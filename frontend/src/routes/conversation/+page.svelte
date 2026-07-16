<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { onMount, onDestroy, untrack } from 'svelte';
	import {
		createInteraction,
		listInteractions,
		listMessages,
		listProfiles,
		listStudyPlans,
		listMedias,
		sendTextMessage
	} from '$lib/api';
	import { isAuthenticated } from '$lib/auth';
	import { t } from '$lib/i18n';
	import { AudioConversation, type AudioStatus } from '$lib/audio/conversation';
	import NewConversationModal from '$lib/components/NewConversationModal.svelte';
	import InteractionSettingsModal from '$lib/components/InteractionSettingsModal.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import VoiceVisualizer from '$lib/components/VoiceVisualizer.svelte';
	import Waveform from '$lib/components/Waveform.svelte';
	import type { ChatStatus, Interaction, Media, Message, Profile, StudyPlan } from '$lib/types';

	const interactionId = $derived(page.url.searchParams.get('id'));

	let interactions = $state<Interaction[]>([]);
	const currentInteraction = $derived(
		interactions.find((i) => i.id === interactionId) ?? null
	);
	let profiles = $state<Profile[]>([]);
	let studyPlans = $state<StudyPlan[]>([]);
	let medias = $state<Media[]>([]);
	let messages = $state<Message[]>([]);
	let status = $state<ChatStatus>('idle');
	let inputText = $state('');
	let loading = $state(true);
	let error = $state<string | null>(null);
	let scrollContainer = $state<HTMLDivElement | null>(null);
	let transcriptContainer = $state<HTMLDivElement | null>(null);
	let audioConversation = $state<AudioConversation | null>(null);
	let audioStatus = $state<AudioStatus>('idle');
	let creating = $state(false);

	let modalOpen = $state(false);
	let settingsModalOpen = $state(false);
	let selectedInteractionForSettings = $state<Interaction | null>(null);

	// Voice Chat State
	let audioEnabled = $state(false);
	let audioVolume = $state(0);
	let tempMessageCounter = 0;
	let currentTurnTempId = $state<string | null>(null);

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
			const [interactionsData, profilesData, studyPlansData, mediasData] = await Promise.all([
				listInteractions(20),
				listProfiles(),
				listStudyPlans(),
				listMedias()
			]);
			interactions = interactionsData;
			profiles = profilesData;
			studyPlans = studyPlansData;
			medias = mediasData;
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
					if (!currentTurnTempId) currentTurnTempId = nextTempId();
					
					const existingIdx = messages.findIndex(m => m.id === currentTurnTempId);
					if (existingIdx >= 0) {
						messages[existingIdx] = { ...messages[existingIdx], content: text };
					} else {
						appendMessage({
							id: currentTurnTempId,
							sent_by: 'user',
							content: text,
							tip: null,
							inserted_at: new Date().toISOString()
						});
					}
				},
				onAssistantMessage: (text, tip, correction) => {
					appendMessage({
						id: nextTempId(),
						sent_by: 'assistant',
						content: text,
						tip: tip || undefined,
						correction: correction || undefined,
						inserted_at: new Date().toISOString()
					});
					currentTurnTempId = null;
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

	function handleMicToggle() {
		if (!audioConversation) return;
		if (audioStatus === 'recording') {
			audioConversation.muteMic();
		} else if (audioStatus === 'connected') {
			audioConversation.unmuteMic();
		}
	}

	function playAudio(mediaId: string | undefined) {
		if (!mediaId) return;
		
		// If using SSR_API_BASE_URL vs VITE_API_BASE_URL, the front talks to the same domain using auth cookie.
		// Wait, the API base url is import.meta.env.VITE_API_BASE_URL for client side fetches.
		const url = `${import.meta.env.VITE_API_BASE_URL}/media/${mediaId}/file`;
		
		const audio = new window.Audio(url);
		audio.play().catch(console.error);
	}

	function audioButtonLabel(): string {
		if (audioEnabled) {
			// Check if currently muted (not recording)
			const isMuted = audioConversation?.muted ?? false;
			if (isMuted || (!audioConversation?.muted && audioStatus !== 'recording')) {
				return 'Unmute mic';
			}
			return 'Mute mic';
		}
		return $t('conversation.voiceChat');
	}

	function voiceChatActive(): boolean {
		return audioEnabled && audioStatus !== 'connected' && audioStatus !== 'idle';
	}

	function speakerName(sentBy: string): string {
		return sentBy === 'user' ? $t('conversation.userLabel') : $t('conversation.aiLabel');
	}

	function speakerTag(sentBy: string): string {
		return sentBy === 'user' ? $t('conversation.userTag') : $t('conversation.aiTag');
	}

	function formatTimestamp(iso: string): string {
		try {
			return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
		} catch {
			return '';
		}
	}
	
	function handleSettingsSave(updatedInteraction: Interaction) {
		interactions = interactions.map(i => i.id === updatedInteraction.id ? updatedInteraction : i);
		settingsModalOpen = false;
	}
	
	function handleSettingsDelete(id: string) {
		interactions = interactions.filter(i => i.id !== id);
		settingsModalOpen = false;
		if (interactionId === id) {
			goto('/conversation', { replaceState: true });
		}
	}
</script>

<div class="conversation" class:voice-active={audioEnabled}>
	<Sidebar
		{interactions}
		onOpenNewConversation={() => (modalOpen = true)}
		onOpenSettings={(interaction) => {
			selectedInteractionForSettings = interaction;
			settingsModalOpen = true;
		}}
	/>

	{#if modalOpen}
		<NewConversationModal
			{profiles}
			{studyPlans}
			{medias}
			loading={creating}
			onStart={handleStartConversation}
			onClose={() => (modalOpen = false)}
		/>
	{/if}
	
	{#if settingsModalOpen && selectedInteractionForSettings}
		<InteractionSettingsModal
			interaction={selectedInteractionForSettings}
			{medias}
			onSave={handleSettingsSave}
			onDelete={handleSettingsDelete}
			onClose={() => (settingsModalOpen = false)}
		/>
	{/if}

	<main class="main">
		<header class="header">
			<div class="header-left">
				<p class="eyebrow">{$t('conversation.eyebrow')}</p>
				<h1 class="header-title">
					{currentInteraction?.name || $t('conversation.newConversation')}
				</h1>
			</div>
			<div class="header-right">
				<StatusBadge {status} />
				{#if audioEnabled}
					<button class="btn-end-voice" type="button" onclick={disconnectAudio}>
						<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
							<path d="M3 3l8 8M11 3L3 11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
						</svg>
						{$t('common.cancel')}
					</button>
				{/if}
			</div>
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
				<div class="voice-transcript" bind:this={transcriptContainer}>
					{#if messages.length === 0}
						<p class="transcript-empty">{$t('conversation.transcriptEmpty')}</p>
					{:else}
						{#each messages as message (message.id)}
							<div class="transcript-line {message.sent_by}" class:blurred={message.sent_by === 'assistant' && !currentInteraction?.need_tip}>
								<span class="transcript-speaker">
									{speakerName(message.sent_by)}
									{#if message.media_id}
										<button class="btn-play-audio" type="button" aria-label="Play audio" onclick={() => playAudio(message.media_id)}>
											<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
										</button>
									{/if}
								</span>
								{#if message.content}
									<p class="transcript-text">{message.content}</p>
								{/if}
								{#if message.sent_by === 'assistant' && message.correction}
									<div class="correction-block tip-block--sm">
										<span class="correction-label">{$t('conversation.correctionLabel')}</span>
										<p class="correction-text">{message.correction}</p>
									</div>
								{/if}
								{#if currentInteraction?.need_tip && message.sent_by === 'assistant' && message.tip}
									<div class="tip-block tip-block--sm">
										<span class="tip-label">{$t('conversation.tipLabel')}</span>
										<p class="tip-text">{message.tip}</p>
									</div>
								{/if}
							</div>
						{/each}
					{/if}
				</div>

				<div class="voice-right">
					<div class="visualizer-wrapper">
						<VoiceVisualizer status={audioStatus} volume={audioVolume} label={audioLabel} />
						{#if audioStatus === 'processing' || audioStatus === 'playing'}
							<p class="processing-hint">{$t('conversation.stillListening')}</p>
						{/if}
					</div>

					<div class="voice-controls">
						<button
							class="btn-mic"
							class:recording={audioStatus === 'recording'}
							type="button"
							disabled={!interactionId}
							onclick={handleMicToggle}
							aria-pressed={audioStatus === 'recording'}
						>
							{#if audioStatus === 'recording'}
								<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
									<rect x="4" y="4" width="8" height="8" rx="1" fill="currentColor" />
								</svg>
								Mute mic
							{:else}
								<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
									<rect x="5.5" y="2" width="5" height="8" rx="2.5" stroke="currentColor" stroke-width="1.4" />
									<path d="M2.5 8a5.5 5.5 0 0011 0M8 13.5v2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
								</svg>
								Unmute mic
							{/if}
						</button>
					</div>
				</div>
			</div>
		{:else}
			<div class="ledger" bind:this={scrollContainer}>
				{#if loading && messages.length === 0}
					<div class="ledger-state">
						<p class="state-text">{$t('conversation.loading')}</p>
					</div>
				{:else if !interactionId}
					<div class="ledger-state ledger-state--empty">
						<p class="state-display">{$t('conversation.selectOrCreate')}</p>
						<p class="state-text">{$t('conversation.empty')}</p>
					</div>
				{:else if messages.length === 0}
					<div class="ledger-state ledger-state--empty">
						<p class="state-display">{$t('conversation.emptyTitle')}</p>
						<p class="state-text">{$t('conversation.empty')}</p>
					</div>
				{:else}
					{#each messages as message (message.id)}
						<div class="line {message.sent_by}" style="animation: message-enter 220ms var(--ease-out) both">
							<div class="line-speaker">
								<span class="speaker-dot" aria-hidden="true"></span>
								<span class="speaker-name">{speakerName(message.sent_by)}</span>
								<span class="speaker-time">{formatTimestamp(message.inserted_at)}</span>
								{#if message.media_id}
									<button class="btn-play-audio" type="button" aria-label="Play audio" onclick={() => playAudio(message.media_id)}>
										<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
									</button>
								{/if}
							</div>

							{#if message.content}
								<p class="utterance">{message.content}</p>
							{/if}

							{#if message.sent_by === 'assistant' && message.correction}
								<div class="correction-block">
									<span class="correction-label">{$t('conversation.correctionLabel')}</span>
									<p class="correction-text">{message.correction}</p>
								</div>
							{/if}

							{#if currentInteraction?.need_tip && message.sent_by === 'assistant' && message.tip}
								<div class="tip-block">
									<span class="tip-label">{$t('conversation.tipLabel')}</span>
									<p class="tip-text">{message.tip}</p>
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
				<div class="error-bar" role="alert">
					<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
						<circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.2" />
						<path d="M7 4v3.5M7 9.5v.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
					</svg>
					{error}
				</div>
			{/if}

			<form class="composer" onsubmit={handleSend}>
				<input
					class="composer-input"
					type="text"
					placeholder={$t('conversation.inputPlaceholder')}
					bind:value={inputText}
					disabled={status === 'processing'}
				/>
				<button
					class="composer-btn composer-btn--mic"
					class:active={voiceChatActive()}
					type="button"
					disabled={!interactionId || (status === 'processing' && !audioEnabled)}
					onclick={handleMicAction}
					aria-pressed={voiceChatActive()}
					aria-label={audioButtonLabel()}
					title={audioButtonLabel()}
				>
					<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
						<rect x="5.5" y="2" width="5" height="8" rx="2.5" stroke="currentColor" stroke-width="1.4" />
						<path d="M2.5 8a5.5 5.5 0 0011 0M8 13.5v2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
					</svg>
				</button>
				<button
					class="composer-btn composer-btn--send"
					type="submit"
					disabled={status === 'processing' || !inputText.trim()}
					aria-label={status === 'processing' ? $t('conversation.sending') : $t('conversation.send')}
				>
					{#if status === 'processing'}
						<span class="spinner" aria-hidden="true"></span>
					{:else}
						<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
							<path d="M14 2L7 9M14 2L9.5 14 7 9 2 6.5 14 2z" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
						</svg>
					{/if}
				</button>
			</form>
		{/if}
	</main>
</div>

<style>

	.conversation {
		display: grid;
		grid-template-columns: 260px 1fr;
		min-height: 100vh;
		background: var(--color-bg);
	}

	.conversation.voice-active {
		grid-template-columns: 260px 1fr;
	}

	.main {
		display: flex;
		flex-direction: column;
		height: 100vh;
		overflow: hidden;
	}


	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-4) var(--space-6);
		border-bottom: 1px solid var(--color-border);
		background: var(--color-bg-inset);
		gap: var(--space-4);
		flex-shrink: 0;
	}

	.header-left {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}

	.eyebrow {
		font: 500 0.6875rem var(--font-body);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--color-accent);
		margin: 0;
	}

	.header-title {
		font: 600 1rem / 1.3 var(--font-body);
		color: var(--color-text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.header-right {
		display: flex;
		align-items: center;
		gap: var(--space-4);
		flex-shrink: 0;
	}

	.btn-end-voice {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: transparent;
		border: 1px solid var(--color-border-strong);
		border-radius: var(--radius-md);
		color: var(--color-text-muted);
		font: 500 0.8125rem var(--font-body);
		cursor: pointer;
		transition:
			border-color var(--duration-fast) var(--ease-standard),
			color var(--duration-fast) var(--ease-standard);
	}

	.btn-end-voice:hover {
		border-color: var(--color-danger);
		color: var(--color-danger);
	}


	.ledger {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-6) var(--space-7);
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.ledger-state {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-4);
		padding: var(--space-8);
		text-align: center;
	}

	.state-display {
		font: 400 italic 1.5rem / 1.3 var(--font-display);
		color: var(--color-text-muted);
		margin: 0;
	}

	.state-text {
		font: var(--text-body-sm);
		color: var(--color-text-muted);
		margin: 0;
		max-width: 36ch;
	}

	.line {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		max-width: 640px;
	}

	.line-speaker {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.speaker-dot {
		width: 5px;
		height: 5px;
		border-radius: var(--radius-pill);
		background: var(--color-border-strong);
		flex-shrink: 0;
	}

	.line.user .speaker-dot {
		background: var(--color-voice-user);
	}

	.line.assistant .speaker-dot {
		background: var(--color-voice-ai);
	}

	.speaker-name {
		font: 700 0.6875rem var(--font-body);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--color-text-muted);
	}

	.line.user .speaker-name {
		color: var(--color-voice-user);
	}

	.line.assistant .speaker-name {
		color: var(--color-voice-ai);
	}

	.btn-play-audio {
		background: none;
		border: none;
		padding: 4px;
		margin-left: 4px;
		color: var(--color-text-secondary);
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		transition: background-color 0.2s, color 0.2s;
	}

	.btn-play-audio:hover {
		background-color: var(--color-bg-inset);
		color: var(--color-accent);
	}

	.speaker-time {
		font: 400 0.6875rem var(--font-mono);
		color: var(--color-text-muted);
		background: var(--color-bg-inset);
		padding: 1px 5px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--color-border);
		color: var(--color-text-muted);
		opacity: 0.6;
		margin-left: auto;
	}

	.utterance {
		font: 400 1.0625rem / 1.6 var(--font-body);
		color: var(--color-text-primary);
		margin: 0;
		max-width: 56ch;
	}

	.tip-block {
		margin-top: var(--space-2);
		padding: var(--space-3) var(--space-4);
		background: rgba(200, 155, 60, 0.05);
		border-left: 2px solid var(--color-accent);
		border-radius: 0 var(--radius-md) var(--radius-md) 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.tip-label {
		display: block;
		font: 700 0.6125rem var(--font-body);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--color-accent);
	}

	.tip-text {
		font: var(--text-body-sm);
		color: var(--color-text-secondary);
		margin: 0;
		line-height: 1.55;
	}

	.tip-block--sm {
		padding: var(--space-2) var(--space-3);
	}

	.correction-block {
		margin-top: var(--space-2);
		padding: var(--space-3) var(--space-4);
		background: rgba(180, 80, 80, 0.05);
		border-left: 2px solid var(--raw-oxblood-500);
		border-radius: 0 var(--radius-md) var(--radius-md) 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.correction-label {
		display: block;
		font: 700 0.6125rem var(--font-body);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--raw-oxblood-500);
	}

	.correction-text {
		font: var(--text-body-sm);
		color: var(--color-text-secondary);
		margin: 0;
		line-height: 1.55;
	}


	.voice-stage {
		flex: 1;
		display: flex;
		flex-direction: row;
		align-items: stretch;
		gap: 0;
		overflow: hidden;
		background: var(--color-bg);
		background-image: radial-gradient(
			ellipse at 50% 50%,
			rgba(79, 122, 108, 0.04) 0%,
			transparent 70%
		);
	}

	.voice-transcript {
		width: 440px;
		flex-shrink: 0;
		border-right: 1px solid var(--color-border);
		background: var(--color-bg-inset);
		overflow-y: auto;
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.voice-right {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-7);
		padding: var(--space-7) var(--space-6);
	}

	.visualizer-wrapper {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-2);
		text-align: center;
	}
	
	.processing-hint {
		font: var(--text-caption);
		color: var(--color-text-muted);
		margin: 0;
		animation: pulse-opacity 2s infinite ease-in-out;
	}

	@keyframes pulse-opacity {
		0%, 100% { opacity: 0.6; }
		50% { opacity: 1; }
	}

	.voice-controls {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-3);
	}

	.btn-mic {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-7);
		background: var(--color-surface);
		border: 1px solid var(--color-border-strong);
		border-radius: var(--radius-md);
		color: var(--color-text-primary);
		font: 500 1rem var(--font-body);
		cursor: pointer;
		transition:
			background var(--duration-fast) var(--ease-standard),
			border-color var(--duration-fast) var(--ease-standard),
			color var(--duration-fast) var(--ease-standard);
	}

	.btn-mic:hover:not(:disabled) {
		border-color: var(--color-accent);
		color: var(--color-accent);
	}

	.btn-mic.recording {
		background: rgba(140, 59, 59, 0.12);
		border-color: var(--color-voice-user);
		color: var(--color-voice-user-soft);
	}

	.btn-mic:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* ================================================================
	   ERROR BAR
	   ================================================================ */
	.error-bar {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-6);
		background: rgba(140, 59, 59, 0.1);
		border-top: 1px solid rgba(140, 59, 59, 0.25);
		color: var(--raw-oxblood-400);
		font: var(--text-body-sm);
		flex-shrink: 0;
	}


	.composer {
		display: flex;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-5);
		border-top: 1px solid var(--color-border);
		background: var(--color-bg-inset);
		align-items: center;
		flex-shrink: 0;
	}

	.composer-input {
		flex: 1;
		padding: var(--space-3) var(--space-4);
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		font: var(--text-body);
		color: var(--color-text-primary);
		transition: border-color var(--duration-fast) var(--ease-standard);
	}

	.composer-input::placeholder {
		color: var(--color-text-muted);
	}

	.composer-input:focus {
		outline: none;
		border-color: var(--color-accent);
	}

	.composer-input:disabled {
		opacity: 0.6;
	}

	.composer-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 38px;
		height: 38px;
		background: transparent;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		color: var(--color-text-muted);
		cursor: pointer;
		flex-shrink: 0;
		transition:
			background var(--duration-fast) var(--ease-standard),
			border-color var(--duration-fast) var(--ease-standard),
			color var(--duration-fast) var(--ease-standard);
	}

	.composer-btn:hover:not(:disabled) {
		border-color: var(--color-border-strong);
		color: var(--color-text-primary);
	}

	.composer-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.composer-btn--mic.active {
		background: rgba(140, 59, 59, 0.12);
		border-color: var(--color-voice-user);
		color: var(--color-voice-user-soft);
	}

	.composer-btn--send {
		background: var(--color-accent);
		border-color: var(--color-accent);
		color: var(--color-text-on-accent);
	}

	.composer-btn--send:hover:not(:disabled) {
		background: var(--color-accent-hover);
		border-color: var(--color-accent-hover);
		color: var(--color-text-on-accent);
	}

	.spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid rgba(16, 21, 26, 0.3);
		border-top-color: var(--color-text-on-accent);
		border-radius: 50%;
		animation: spin 600ms linear infinite;
	}



	.transcript-empty {
		font: 400 italic 0.875rem var(--font-display);
		color: var(--color-text-muted);
		text-align: center;
		margin: var(--space-6) 0 0;
	}

	.transcript-line {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		padding: var(--space-3);
		border-radius: var(--radius-md);
		background: var(--color-surface);
		border-left: 2px solid var(--color-border-strong);
		transition: filter 0.3s ease;
	}

	.transcript-line.blurred {
		filter: blur(4px);
		user-select: none;
		pointer-events: none;
	}

	.transcript-line.user {
		border-left-color: var(--color-voice-user);
	}

	.transcript-line.assistant {
		border-left-color: var(--color-voice-ai);
	}

	.transcript-speaker {
		font: 700 0.6125rem var(--font-body);
		letter-spacing: 0.1em;
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
		font: 400 0.8125rem / 1.5 var(--font-body);
		color: var(--color-text-primary);
		margin: 0;
	}
</style>
