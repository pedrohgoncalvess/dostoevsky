<script lang="ts">
	import { t } from '$lib/i18n';
	import { listStudyPlans } from '$lib/api';
	import type { Media, Profile, StudyPlan } from '$lib/types';

	interface Props {
		profiles: Profile[];
		studyPlans: StudyPlan[];
		medias: Media[];
		loading?: boolean;
		onStart: (
			profileId: string,
			studyPlanId: string,
			mediaIds: string[],
			needTip: boolean
		) => void;
		onClose: () => void;
	}

	let { profiles, studyPlans, medias, loading = false, onStart, onClose }: Props = $props();

	const AUDIO_FORMATS = new Set(['pcm', 'wav', 'mp3', 'ogg', 'flac', 'm4a', 'aac', 'opus', 'webm']);
	const contextMedias = $derived(medias.filter(m => !m.format || !AUDIO_FORMATS.has(m.format.toLowerCase())));

	let selectedProfileId = $state('');
	let selectedStudyPlanId = $state('');
	let selectedMediaIds = $state<string[]>([]);
	let needTip = $state(false);

	function toggleMedia(id: string) {
		if (selectedMediaIds.includes(id)) {
			selectedMediaIds = selectedMediaIds.filter((mediaId) => mediaId !== id);
		} else {
			selectedMediaIds = [...selectedMediaIds, id];
		}
	}

	function handleStart() {
		if (!selectedProfileId || !selectedStudyPlanId) return;
		onStart(selectedProfileId, selectedStudyPlanId, selectedMediaIds, needTip);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			onClose();
		}
	}

	let internalStudyPlans = $state<StudyPlan[]>([...studyPlans]);

	$effect(() => {
		internalStudyPlans = studyPlans;
	});

	const selectedPlan = $derived(internalStudyPlans.find((p) => p.id === selectedStudyPlanId));
	const isDownloading = $derived(selectedPlan ? !selectedPlan.setup_completed : false);

	$effect(() => {
		if (isDownloading) {
			const interval = setInterval(async () => {
				try {
					internalStudyPlans = await listStudyPlans();
				} catch (e) {
					// Ignore errors during polling
				}
			}, 3000);
			return () => clearInterval(interval);
		}
	});

	const canStart = $derived(!!selectedProfileId && !!selectedStudyPlanId && !loading && !isDownloading);
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="overlay" onclick={onClose} role="presentation">
	<div
		class="modal"
		onclick={(e) => e.stopPropagation()}
		onkeydown={(e) => e.stopPropagation()}
		role="dialog"
		aria-modal="true"
		aria-labelledby="modal-title"
		tabindex="-1"
	>
		<header class="modal-header">
			<div>
				<p class="eyebrow">{$t('conversation.eyebrow')}</p>
				<h2 id="modal-title">{$t('modal.newConversationTitle')}</h2>
			</div>
			<button class="close-btn" type="button" onclick={onClose} aria-label={$t('common.cancel')}>
				<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
					<path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
				</svg>
			</button>
		</header>

		<div class="modal-body">
			<label class="field">
				<span class="field-label">{$t('modal.profileLabel')}</span>
				<select class="input" bind:value={selectedProfileId}>
					<option value="" disabled selected>{$t('modal.selectProfile')}</option>
					{#each profiles as profile (profile.id)}
						<option value={profile.id}>{profile.name}</option>
					{/each}
				</select>
				{#if profiles.length === 0}
					<span class="field-hint field-hint--warn">{$t('modal.noProfiles')}</span>
				{/if}
			</label>

			<label class="field">
				<span class="field-label">{$t('modal.studyPlanLabel')}</span>
				<select class="input" bind:value={selectedStudyPlanId}>
					<option value="" disabled selected>{$t('modal.selectStudyPlan')}</option>
					{#each internalStudyPlans as plan (plan.id)}
						<option value={plan.id}>
							{plan.study_language} · {plan.self_declared_level.toUpperCase()}
							{#if plan.goal}— {plan.goal}{/if}
						</option>
					{/each}
				</select>
				{#if internalStudyPlans.length === 0}
					<span class="field-hint field-hint--warn">{$t('modal.noStudyPlansModal')}</span>
				{/if}
			</label>

			{#if contextMedias.length > 0}
				<div class="field">
					<span class="field-label">{$t('modal.mediaLabel')}</span>
					<span class="field-hint">{$t('modal.mediaHint')}</span>
					<div class="media-grid">
						{#each contextMedias as media (media.id)}
							<label class="media-card" class:selected={selectedMediaIds.includes(media.id)}>
								<input
									type="checkbox"
									class="media-checkbox"
									value={media.id}
									checked={selectedMediaIds.includes(media.id)}
									onchange={() => toggleMedia(media.id)}
								/>
								<span class="media-name">{media.name}</span>
								<span class="media-desc">{media.description?.written_description || ''}</span>
							</label>
						{/each}
					</div>
				</div>
			{/if}

			<label class="field field--row">
				<input type="checkbox" bind:checked={needTip} />
				<div>
					<span class="field-label">{$t('modal.needTipLabel')}</span>
					<span class="field-hint">{$t('modal.needTipHint')}</span>
				</div>
			</label>
		</div>

		{#if isDownloading}
			<div class="downloading-banner">
				<span class="spinner" aria-hidden="true"></span>
				<p>{$t('modal.modelsDownloading')}</p>
			</div>
		{/if}

		<footer class="modal-footer">
			<button class="btn btn--secondary" type="button" onclick={onClose}>
				{$t('common.cancel')}
			</button>
			<button
				class="btn"
				type="button"
				disabled={!canStart}
				onclick={handleStart}
			>
				{#if loading}
					<span class="spinner" aria-hidden="true"></span>
					{$t('common.loading')}
				{:else}
					{$t('modal.startConversation')}
				{/if}
			</button>
		</footer>
	</div>
</div>

<style>
	.overlay {
		position: fixed;
		inset: 0;
		background: rgba(16, 21, 26, 0.75);
		backdrop-filter: blur(4px);
		-webkit-backdrop-filter: blur(4px);
		display: grid;
		place-items: center;
		padding: var(--space-5);
		z-index: 100;
		animation: fade-in var(--duration-base) var(--ease-out);
	}

	.modal {
		width: 100%;
		max-width: 520px;
		max-height: 88vh;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		background: var(--color-surface);
		border: 1px solid var(--color-border-strong);
		border-radius: var(--radius-lg);
		box-shadow: var(--elevation-2);
		animation: message-enter var(--duration-base) var(--ease-out);
	}

	.modal-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		padding: var(--space-5) var(--space-5) var(--space-4);
		border-bottom: 1px solid var(--color-border);
		gap: var(--space-4);
	}

	.eyebrow {
		font: 500 0.6875rem var(--font-body);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--color-accent);
		margin: 0 0 var(--space-1);
	}

	.modal-header h2 {
		font: var(--text-heading);
		color: var(--color-text-primary);
		margin: 0;
	}

	.close-btn {
		background: transparent;
		border: none;
		color: var(--color-text-muted);
		cursor: pointer;
		padding: var(--space-1);
		border-radius: var(--radius-md);
		display: flex;
		align-items: center;
		transition: color var(--duration-fast) var(--ease-standard);
		flex-shrink: 0;
	}

	.close-btn:hover {
		color: var(--color-text-primary);
	}

	.modal-body {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		padding: var(--space-5);
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.field--row {
		flex-direction: row;
		align-items: flex-start;
		gap: var(--space-3);
		padding: var(--space-3) var(--space-4);
		background: var(--color-bg-inset);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
	}

	.field--row input[type='checkbox'] {
		margin-top: 2px;
		flex-shrink: 0;
	}

	.field-label {
		font: 500 0.6875rem var(--font-body);
		letter-spacing: var(--letter-caption);
		text-transform: uppercase;
		color: var(--color-text-muted);
		display: block;
	}

	.field-hint {
		font: var(--text-caption);
		color: var(--color-text-muted);
	}

	.field-hint--warn {
		color: var(--color-danger);
		opacity: 0.85;
	}

	.input {
		background: var(--color-bg-inset);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		padding: var(--space-3) var(--space-4);
		font: var(--text-body);
		color: var(--color-text-primary);
		transition: border-color var(--duration-fast) var(--ease-standard);
	}

	.input:focus {
		outline: none;
		border-color: var(--color-accent);
	}

	.media-grid {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.media-card {
		display: grid;
		grid-template-columns: auto 1fr;
		grid-template-rows: auto auto;
		column-gap: var(--space-3);
		row-gap: 2px;
		align-items: start;
		padding: var(--space-3) var(--space-4);
		background: var(--color-bg-inset);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition:
			border-color var(--duration-fast) var(--ease-standard),
			background var(--duration-fast) var(--ease-standard);
	}

	.media-card:hover {
		border-color: var(--color-border-strong);
		background: var(--color-surface-raised);
	}

	.media-card.selected {
		border-color: var(--color-accent);
		background: rgba(200, 155, 60, 0.06);
	}

	.media-checkbox {
		margin-top: 2px;
		grid-row: 1 / 3;
		grid-column: 1;
	}

	.media-name {
		font: 500 0.875rem var(--font-body);
		color: var(--color-text-primary);
		grid-column: 2;
		grid-row: 1;
	}

	.media-desc {
		font: var(--text-caption);
		color: var(--color-text-muted);
		grid-column: 2;
		grid-row: 2;
	}

	.modal-footer {
		display: flex;
		justify-content: flex-end;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-5);
		border-top: 1px solid var(--color-border);
	}

	.btn--secondary {
		background: transparent;
		color: var(--color-text-secondary);
		border-color: var(--color-border);
	}

	.btn--secondary:hover {
		background: var(--color-surface-raised);
		border-color: var(--color-border-strong);
		color: var(--color-text-primary);
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.downloading-banner {
		margin: 0 var(--space-5) var(--space-4);
		padding: var(--space-3) var(--space-4);
		background: rgba(200, 155, 60, 0.1);
		border: 1px solid rgba(200, 155, 60, 0.2);
		border-radius: var(--radius-md);
		display: flex;
		align-items: center;
		gap: var(--space-3);
		color: var(--color-accent);
		font: var(--text-body-sm);
	}

	.downloading-banner p {
		margin: 0;
	}

	.downloading-banner .spinner {
		border-color: rgba(200, 155, 60, 0.3);
		border-top-color: var(--color-accent);
	}

	.spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid rgba(16, 21, 26, 0.3);
		border-top-color: var(--color-text-on-accent);
		border-radius: 50%;
		animation: spin 600ms linear infinite;
		flex-shrink: 0;
		box-sizing: border-box;
	}
</style>
