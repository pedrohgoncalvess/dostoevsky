<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { onMount, onDestroy } from 'svelte';
	import {
		createInteraction,
		createStudyPlan,
		deleteStudyPlan,
		listInteractions,
		listMessages,
		listProfiles,
		listStudyPlans,
		sendTextMessage
	} from '$lib/api';
	import { isAuthenticated } from '$lib/auth';
	import { t } from '$lib/i18n';
	import { AudioConversation, type AudioStatus } from '$lib/audio/conversation';
	import NewConversationModal from '$lib/components/NewConversationModal.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import StudyPlanModal from '$lib/components/StudyPlanModal.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import Waveform from '$lib/components/Waveform.svelte';
	import type { ChatStatus, Interaction, Media, Message, Profile, StudyPlan } from '$lib/types';

	const mockMedias: Media[] = [
		{
			id: 'media-1',
			name: 'Business English Phrases',
			description: 'Common phrases for professional meetings and emails.'
		},
		{
			id: 'media-2',
			name: 'Travel Spanish Vocabulary',
			description: 'Essential words and expressions for traveling.'
		},
		{
			id: 'media-3',
			name: 'Job Interview Tips',
			description: 'Questions and answers to practice for interviews.'
		}
	];

	const interactionId = $derived(page.url.searchParams.get('id'));

	let interactions = $state<Interaction[]>([]);
	let profiles = $state<Profile[]>([]);
	let studyPlans = $state<StudyPlan[]>([]);
	let messages = $state<Message[]>([]);
	let status = $state<ChatStatus>('idle');
	let inputText = $state('');
	let loading = $state(true);
	let error = $state<string | null>(null);
	let scrollContainer = $state<HTMLDivElement | null>(null);
	let audioConversation = $state<AudioConversation | null>(null);
	let audioStatus = $state<AudioStatus>('idle');
	let audioEnabled = $state(false);
	let modalOpen = $state(false);
	let studyPlanModalOpen = $state(false);
	let creating = $state(false);
	let studyPlanLoading = $state(false);

	onMount(async () => {
		if (!browser) return;
		if (!isAuthenticated()) {
			await goto('/');
			return;
		}
		await loadSidebarData();
	});

	$effect(() => {
		const id = interactionId;
		if (id) {
			void loadMessages(id);
		}
		audioConversation?.close();
		audioConversation = null;
		audioStatus = 'idle';
		audioEnabled = false;
		status = 'idle';
		error = null;
	});

	$effect(() => {
		if (scrollContainer) {
			scrollContainer.scrollTop = scrollContainer.scrollHeight;
		}
	});

	onDestroy(() => {
		audioConversation?.close();
	});

	async function loadSidebarData() {
		try {
			const [interactionsData, profilesData, studyPlansData] = await Promise.all([
				listInteractions(20),
				listProfiles(),
				listStudyPlans()
			]);
			interactions = interactionsData;
			profiles = profilesData;
			studyPlans = studyPlansData;
		} catch (err) {
			error = err instanceof Error ? err.message : $t('conversation.loadError');
		} finally {
			loading = false;
		}
	}

	async function loadMessages(id: string) {
		try {
			messages = await listMessages(id);
		} catch (err) {
			error = err instanceof Error ? err.message : $t('conversation.loadError');
		}
	}

	function appendMessage(message: Message) {
		messages = [...messages, message];
	}

	async function handleSend(event?: Event) {
		event?.preventDefault();
		if (!inputText.trim() || !interactionId) return;

		const text = inputText.trim();
		inputText = '';
		status = 'processing';
		error = null;

		appendMessage({
			id: 'temp',
			sent_by: 'user',
			content: text,
			tip: null,
			inserted_at: new Date().toISOString()
		});

		try {
			const assistantMessage = await sendTextMessage(interactionId, text);
			appendMessage(assistantMessage);
			status = 'idle';
		} catch (err) {
			status = 'error';
			error = err instanceof Error ? err.message : $t('conversation.messageError');
		}
	}

	async function handleStartConversation(profileId: string, studyPlanId: string) {
		creating = true;
		error = null;
		try {
			const profile = profiles.find((p) => p.id === profileId);
			const interaction = await createInteraction(
				profileId,
				studyPlanId,
				profile?.name ?? $t('conversation.newConversation')
			);
			interactions = [interaction, ...interactions];
			modalOpen = false;
			await goto(`/conversation?id=${interaction.id}`);
		} catch (err) {
			error = err instanceof Error ? err.message : $t('conversation.createError');
		} finally {
			creating = false;
		}
	}

	async function handleCreateStudyPlan(
		studyLanguage: string,
		selfDeclaredLevel: string,
		goal: string
	) {
		studyPlanLoading = true;
		error = null;
		try {
			const plan = await createStudyPlan(studyLanguage, selfDeclaredLevel, goal);
			studyPlans = [plan, ...studyPlans];
		} catch (err) {
			error = err instanceof Error ? err.message : $t('common.error');
		} finally {
			studyPlanLoading = false;
		}
	}

	async function handleDeleteStudyPlan(planId: string) {
		studyPlanLoading = true;
		error = null;
		try {
			await deleteStudyPlan(planId);
			studyPlans = studyPlans.filter((p) => p.id !== planId);
		} catch (err) {
			error = err instanceof Error ? err.message : $t('common.error');
		} finally {
			studyPlanLoading = false;
		}
	}

	function ensureAudioConversation(): AudioConversation {
		if (!interactionId) {
			throw new Error('No interaction selected');
		}
		if (!audioConversation) {
			audioConversation = new AudioConversation(interactionId, {
				onStatusChange: (value) => {
					audioStatus = value;
					if (value === 'processing' || value === 'playing' || value === 'recording') {
						status = 'processing';
					} else if (value === 'error') {
						status = 'error';
					} else {
						status = 'idle';
					}
				},
				onUserTranscription: (text) => {
					appendMessage({
						id: 'temp',
						sent_by: 'user',
						content: text,
						tip: null,
						inserted_at: new Date().toISOString()
					});
				},
				onAssistantMessage: (text) => {
					appendMessage({
						id: 'temp',
						sent_by: 'assistant',
						content: text,
						tip: null,
						inserted_at: new Date().toISOString()
					});
				},
				onError: (message) => {
					error = message;
				}
			});
		}
		return audioConversation;
	}

	async function handleMicAction() {
		if (!interactionId) return;
		error = null;

		try {
			if (!audioEnabled) {
				const conversation = ensureAudioConversation();
				await conversation.connect();
				audioEnabled = true;
				conversation.startRecording();
			} else {
				audioConversation?.toggleRecording();
			}
		} catch (err) {
			error = err instanceof Error ? err.message : $t('conversation.audioError');
			audioEnabled = false;
		}
	}

	function disconnectAudio() {
		audioConversation?.close();
		audioConversation = null;
		audioEnabled = false;
		audioStatus = 'idle';
	}

	function audioButtonLabel(): string {
		if (audioStatus === 'recording') return $t('conversation.recording');
		if (audioStatus === 'processing') return $t('conversation.processingAudio');
		if (audioStatus === 'playing') return $t('conversation.playing');
		return $t('conversation.voiceChat');
	}

	function canDisconnectAudio(): boolean {
		return audioEnabled && (audioStatus === 'idle' || audioStatus === 'connected');
	}

	function voiceChatActive(): boolean {
		return audioEnabled && (audioStatus === 'idle' || audioStatus === 'connected');
	}

	function speakerName(sentBy: string): string {
		return sentBy === 'user' ? $t('conversation.userLabel') : $t('conversation.aiLabel');
	}

	function speakerTag(sentBy: string): string {
		return sentBy === 'user' ? $t('conversation.userTag') : $t('conversation.aiTag');
	}
</script>

<div class="conversation">
	<Sidebar
		{interactions}
		onOpenNewConversation={() => (modalOpen = true)}
		onOpenStudyPlans={() => (studyPlanModalOpen = true)}
	/>

	{#if modalOpen}
		<NewConversationModal
			{profiles}
			{studyPlans}
			medias={mockMedias}
			loading={creating}
			onStart={handleStartConversation}
			onClose={() => (modalOpen = false)}
		/>
	{/if}

	{#if studyPlanModalOpen}
		<StudyPlanModal
			plans={studyPlans}
			loading={studyPlanLoading}
			onCreate={handleCreateStudyPlan}
			onDelete={handleDeleteStudyPlan}
			onClose={() => (studyPlanModalOpen = false)}
		/>
	{/if}

	<main class="main">
		<header class="header">
			<div class="header-title">
				<p class="eyebrow">{$t('conversation.eyebrow')}</p>
				<h1>
					{interactions.find((i) => i.id === interactionId)?.name ||
						$t('conversation.newConversation')}
				</h1>
			</div>
			<StatusBadge {status} />
		</header>

		<div class="ledger" bind:this={scrollContainer}>
			{#if loading && messages.length === 0}
				<p class="status-text">{$t('conversation.loading')}</p>
			{:else if messages.length === 0}
				<div class="empty">
					<p>{$t('conversation.empty')}</p>
				</div>
			{:else}
				{#each messages as message (message.id)}
					<div class="line {message.sent_by}">
						<div class="speaker {message.sent_by}">
							{speakerName(message.sent_by)}
							<span class="tag">{speakerTag(message.sent_by)}</span>
						</div>
						{#if message.content}
							<p class="utterance">{message.content}</p>
						{/if}
						<Waveform
							active={status !== 'idle' && status !== 'error' && status !== 'closed'}
							variant={message.sent_by === 'user' ? 'user' : 'ai'}
						/>
					</div>
				{/each}
			{/if}
		</div>

		{#if error}
			<p class="error-banner" role="alert">{error}</p>
		{/if}

		<form class="composer" onsubmit={handleSend}>
			<input
				class="input composer-input"
				type="text"
				placeholder={$t('conversation.inputPlaceholder')}
				bind:value={inputText}
				disabled={status === 'processing'}
			/>
			<button
				class="btn btn--mic"
				type="button"
				disabled={!interactionId || status === 'processing'}
				onclick={handleMicAction}
				aria-pressed={voiceChatActive()}
			>
				{audioButtonLabel()}
			</button>
			{#if canDisconnectAudio()}
				<button
					class="btn btn--mic-off"
					type="button"
					onclick={disconnectAudio}
					aria-label={$t('conversation.voiceChat')}
				>
					×
				</button>
			{/if}
			<button class="btn" type="submit" disabled={status === 'processing' || !inputText.trim()}>
				{status === 'processing' ? $t('conversation.sending') : $t('conversation.send')}
			</button>
		</form>
	</main>
</div>

<style>
	.conversation {
		display: grid;
		grid-template-columns: 260px 1fr;
		min-height: 100vh;
		background: var(--color-bg);
	}

	.main {
		display: flex;
		flex-direction: column;
		height: 100vh;
	}

	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-4) var(--space-6);
		border-bottom: 1px solid var(--color-border);
		background: var(--color-surface);
	}

	.header h1 {
		font: var(--text-heading);
		color: var(--color-text-primary);
	}

	.ledger {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-6);
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}

	.line {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		max-width: 720px;
	}

	.speaker {
		font: 700 0.75rem var(--font-body);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.speaker.user {
		color: var(--color-voice-user);
	}

	.speaker.assistant {
		color: var(--color-voice-ai);
	}

	.utterance {
		font: 400 1.0625rem / 1.5 var(--font-body);
		color: var(--color-text-primary);
		margin: 0;
		max-width: 52ch;
	}

	.composer {
		display: flex;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-6);
		border-top: 1px solid var(--color-border);
		background: var(--color-surface);
	}

	.composer-input {
		flex: 1;
	}

	.btn--mic {
		background: var(--color-accent);
		color: var(--color-text-on-accent);
		border-color: var(--color-accent);
	}

	.btn--mic:hover {
		background: var(--color-accent-hover);
		border-color: var(--color-accent-hover);
	}

	.btn--mic[aria-pressed='true'] {
		background: var(--color-danger);
		border-color: var(--color-danger);
	}

	.btn--mic-off {
		padding-left: var(--space-3);
		padding-right: var(--space-3);
	}

	.btn--mic:disabled,
	.btn--mic-off:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.status-text {
		font: var(--text-body);
		color: var(--color-text-muted);
		text-align: center;
		margin-top: var(--space-6);
	}

	.empty {
		padding: var(--space-6);
		text-align: center;
		color: var(--color-text-muted);
	}

	.error-banner {
		padding: var(--space-3) var(--space-6);
		background: rgba(140, 59, 59, 0.15);
		border-top: 1px solid var(--color-danger);
		color: var(--raw-oxblood-400);
		font: var(--text-body-sm);
	}
</style>
