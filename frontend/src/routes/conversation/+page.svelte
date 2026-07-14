<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { onMount, onDestroy, untrack } from 'svelte';
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
	import VoiceVisualizer from '$lib/components/VoiceVisualizer.svelte';
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
	const currentInteraction = $derived(
		interactions.find((i) => i.id === interactionId) ?? null
	);
	let profiles = $state<Profile[]>([]);
	let studyPlans = $state<StudyPlan[]>([]);
	let messages = $state<Message[]>([]);
	let status = $state<ChatStatus>('idle');
	let inputText = $state('');
	let loading = $state(true);
	let error = $state<string | null>(null);
	let scrollContainer = $state<HTMLDivElement | null>(null);
	let transcriptContainer = $state<HTMLDivElement | null>(null);
	let audioConversation = $state<AudioConversation | null>(null);
	let audioStatus = $state<AudioStatus>('idle');
	let audioEnabled = $state(false);
	let audioVolume = $state(0);
	let modalOpen = $state(false);
	let studyPlanModalOpen = $state(false);
	let creating = $state(false);
	let studyPlanLoading = $state(false);
	let tempMessageCounter = 0;

	function nextTempId(): string {
		return `temp-${++tempMessageCounter}`;
	}

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
		untrack(() => {
			audioConversation?.close();
			audioConversation = null;
			audioStatus = 'idle';
			audioEnabled = false;
			status = 'idle';
			error = null;
		});
	});

	$effect(() => {
		const target = audioEnabled ? transcriptContainer : scrollContainer;
		if (target) {
			target.scrollTop = target.scrollHeight;
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
			id: nextTempId(),
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

	async function handleStartConversation(
		profileId: string,
		studyPlanId: string,
		mediaIds: string[],
		needTip: boolean
	) {
		creating = true;
		error = null;
		try {
			const profile = profiles.find((p) => p.id === profileId);
			const interaction = await createInteraction(
				profileId,
				studyPlanId,
				profile?.name ?? $t('conversation.newConversation'),
				needTip
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
						id: nextTempId(),
						sent_by: 'user',
						content: text,
						tip: null,
						inserted_at: new Date().toISOString()
					});
				},
				onAssistantMessage: (text) => {
					appendMessage({
						id: nextTempId(),
						sent_by: 'assistant',
						content: text,
						tip: null,
						inserted_at: new Date().toISOString()
					});
				},
				onError: (message) => {
					error = message;
				},
				onVolumeChange: (volume) => {
					audioVolume = volume;
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

<div class="conversation" class:voice-active={audioEnabled}>
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
					{currentInteraction?.name || $t('conversation.newConversation')}
				</h1>
			</div>
			<StatusBadge {status} />
		</header>

		{#if audioEnabled}
			{@const audioLabel =
				audioStatus === 'recording'
					? $t('conversation.recording')
					: audioStatus === 'processing'
						? $t('conversation.processingAudio')
						: audioStatus === 'playing'
							? $t('conversation.playing')
							: $t('conversation.voiceChat')}
			<div class="voice-stage">
				<VoiceVisualizer status={audioStatus} volume={audioVolume} label={audioLabel} />

				<div class="voice-controls">
					<button
						class="btn btn--mic btn--voice-main"
						type="button"
						disabled={!interactionId || status === 'processing'}
						onclick={handleMicAction}
						aria-pressed={voiceChatActive()}
					>
						{audioButtonLabel()}
					</button>
					<button
						class="btn btn--voice-end"
						type="button"
						onclick={disconnectAudio}
						aria-label={$t('conversation.voiceChat')}
					>
						{$t('common.cancel')}
					</button>
				</div>
			</div>
		{:else}
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
							{#if currentInteraction?.need_tip && message.sent_by === 'assistant' && message.tip}
								<div class="message-tip">
									<span class="message-tip-label">{$t('conversation.tipLabel')}</span>
									<p class="message-tip-text">{message.tip}</p>
								</div>
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
				<button
					class="btn"
					type="submit"
					disabled={status === 'processing' || !inputText.trim()}
				>
					{status === 'processing' ? $t('conversation.sending') : $t('conversation.send')}
				</button>
			</form>
		{/if}
	</main>

	{#if audioEnabled}
		<aside class="transcript-panel">
			<header class="transcript-header">
				<h2>{$t('conversation.transcript')}</h2>
			</header>
			<div class="transcript-body" bind:this={transcriptContainer}>
				{#if messages.length === 0}
					<p class="transcript-empty">{$t('conversation.transcriptEmpty')}</p>
				{:else}
					{#each messages as message (message.id)}
						<div class="transcript-line {message.sent_by}">
							<span class="transcript-speaker">{speakerName(message.sent_by)}</span>
							{#if message.content}
								<p class="transcript-text">{message.content}</p>
							{/if}
							{#if currentInteraction?.need_tip && message.sent_by === 'assistant' && message.tip}
								<div class="message-tip">
									<span class="message-tip-label">{$t('conversation.tipLabel')}</span>
									<p class="message-tip-text">{message.tip}</p>
								</div>
							{/if}
						</div>
					{/each}
				{/if}
			</div>
		</aside>
	{/if}
</div>

<style>
	.conversation {
		display: grid;
		grid-template-columns: 260px 1fr;
		min-height: 100vh;
		background: var(--color-bg);
	}

	.conversation.voice-active {
		grid-template-columns: 260px 1fr 320px;
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

	.message-tip {
		margin-top: var(--space-2);
		padding: var(--space-3) var(--space-4);
		background: rgba(var(--color-accent-rgb), 0.08);
		border-left: 3px solid var(--color-accent);
		border-radius: var(--radius-md);
	}

	.message-tip-label {
		display: block;
		font: 700 0.6875rem var(--font-body);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--color-accent);
		margin: 0 0 var(--space-1) 0;
	}

	.message-tip-text {
		font: var(--text-body-sm);
		color: var(--color-text-secondary);
		margin: 0;
		line-height: 1.5;
	}

	.voice-stage {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-8);
		padding: var(--space-6);
		background: var(--color-bg);
	}

	.voice-controls {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-4);
	}

	.btn--voice-main {
		min-width: 180px;
		padding: var(--space-4) var(--space-7);
		font: 600 1rem var(--font-body);
	}

	.btn--voice-end {
		background: transparent;
		border-color: var(--color-border-strong);
		color: var(--color-text-secondary);
	}

	.btn--voice-end:hover {
		border-color: var(--color-danger);
		color: var(--color-danger);
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

	.btn--mic:disabled {
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

	.transcript-panel {
		display: flex;
		flex-direction: column;
		height: 100vh;
		background: var(--color-surface);
		border-left: 1px solid var(--color-border);
	}

	.transcript-header {
		padding: var(--space-4) var(--space-5);
		border-bottom: 1px solid var(--color-border);
		background: var(--color-surface-raised);
	}

	.transcript-header h2 {
		font: 700 0.75rem var(--font-body);
		letter-spacing: var(--letter-caption);
		text-transform: uppercase;
		color: var(--color-text-secondary);
		margin: 0;
	}

	.transcript-body {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-5);
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.transcript-empty {
		font: var(--text-body-sm);
		color: var(--color-text-muted);
		text-align: center;
		margin-top: var(--space-6);
	}

	.transcript-line {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		padding: var(--space-3);
		border-radius: var(--radius-md);
		background: var(--color-bg-inset);
		border-left: 3px solid var(--color-border-strong);
	}

	.transcript-line.user {
		border-left-color: var(--color-voice-user);
	}

	.transcript-line.assistant {
		border-left-color: var(--color-voice-ai);
	}

	.transcript-speaker {
		font: 700 0.6875rem var(--font-body);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--color-text-muted);
	}

	.transcript-line.user .transcript-speaker {
		color: var(--color-voice-user-soft);
	}

	.transcript-line.assistant .transcript-speaker {
		color: var(--color-voice-ai-soft);
	}

	.transcript-text {
		font: var(--text-body);
		color: var(--color-text-primary);
		margin: 0;
		line-height: 1.5;
	}
</style>
