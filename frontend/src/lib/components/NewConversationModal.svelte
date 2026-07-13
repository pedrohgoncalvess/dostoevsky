<script lang="ts">
	import { t } from '$lib/i18n';
	import type { Media, Profile, StudyPlan } from '$lib/types';

	interface Props {
		profiles: Profile[];
		studyPlans: StudyPlan[];
		medias: Media[];
		loading?: boolean;
		onStart: (profileId: string, studyPlanId: string, mediaIds: string[]) => void;
		onClose: () => void;
	}

	let { profiles, studyPlans, medias, loading = false, onStart, onClose }: Props = $props();

	let selectedProfileId = $state('');
	let selectedStudyPlanId = $state('');
	let selectedMediaIds = $state<string[]>([]);

	function toggleMedia(id: string) {
		if (selectedMediaIds.includes(id)) {
			selectedMediaIds = selectedMediaIds.filter((mediaId) => mediaId !== id);
		} else {
			selectedMediaIds = [...selectedMediaIds, id];
		}
	}

	function handleStart() {
		if (!selectedProfileId || !selectedStudyPlanId) return;
		onStart(selectedProfileId, selectedStudyPlanId, selectedMediaIds);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="overlay" onclick={onClose} role="presentation">
	<div
		class="modal card"
		onclick={(e) => e.stopPropagation()}
		onkeydown={(e) => e.stopPropagation()}
		role="dialog"
		aria-modal="true"
		tabindex="-1"
	>
		<header class="header">
			<h2>{$t('modal.newConversationTitle')}</h2>
			<button class="close" type="button" onclick={onClose} aria-label={$t('common.cancel')}>
				×
			</button>
		</header>

		<div class="body">
			<label class="field">
				<span class="field-label">{$t('modal.profileLabel')}</span>
				<select class="input" bind:value={selectedProfileId}>
					<option value="" disabled selected>{$t('modal.selectProfile')}</option>
					{#each profiles as profile (profile.id)}
						<option value={profile.id}>{profile.name}</option>
					{/each}
				</select>
			</label>

			{#if profiles.length === 0}
				<p class="hint hint--warning">{$t('modal.noProfiles')}</p>
			{/if}

			<label class="field">
				<span class="field-label">{$t('modal.studyPlanLabel')}</span>
				<select class="input" bind:value={selectedStudyPlanId}>
					<option value="" disabled selected>{$t('modal.selectStudyPlan')}</option>
					{#each studyPlans as plan (plan.id)}
						<option value={plan.id}>
							{plan.study_language} · {plan.self_declared_level.toUpperCase()}
							{#if plan.goal}- {plan.goal}{/if}
						</option>
					{/each}
				</select>
			</label>

			{#if studyPlans.length === 0}
				<p class="hint hint--warning">{$t('modal.noStudyPlansModal')}</p>
			{/if}

			<div class="field">
				<span class="field-label">{$t('modal.mediaLabel')}</span>
				<span class="hint">{$t('modal.mediaHint')}</span>
				<div class="media-list">
					{#each medias as media (media.id)}
						<label class="media-item">
							<input
								type="checkbox"
								value={media.id}
								checked={selectedMediaIds.includes(media.id)}
								onchange={() => toggleMedia(media.id)}
							/>
							<span class="media-name">{media.name}</span>
							<span class="media-desc">{media.description}</span>
						</label>
					{/each}
				</div>
			</div>
		</div>

		<footer class="footer">
			<button class="btn btn--secondary" type="button" onclick={onClose}>
				{$t('common.cancel')}
			</button>
			<button
				class="btn btn--primary"
				type="button"
				disabled={!selectedProfileId || !selectedStudyPlanId || loading}
				onclick={handleStart}
			>
				{loading ? $t('common.loading') : $t('modal.startConversation')}
			</button>
		</footer>
	</div>
</div>

<style>
	.overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: grid;
		place-items: center;
		padding: var(--space-5);
		z-index: 100;
	}

	.modal {
		width: 100%;
		max-width: 480px;
		max-height: 90vh;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}

	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding-bottom: var(--space-4);
		border-bottom: 1px solid var(--color-border);
	}

	.header h2 {
		font: var(--text-heading);
		color: var(--color-text-primary);
		margin: 0;
	}

	.close {
		background: transparent;
		border: none;
		color: var(--color-text-muted);
		font-size: 1.5rem;
		cursor: pointer;
		padding: 0 var(--space-2);
	}

	.close:hover {
		color: var(--color-text-primary);
	}

	.body {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.field-label {
		font: var(--text-caption);
		letter-spacing: var(--letter-caption);
		text-transform: uppercase;
		color: var(--color-text-muted);
	}

	.hint {
		font: var(--text-caption);
		color: var(--color-text-muted);
	}

	.hint--warning {
		color: var(--color-danger);
	}

	.media-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		max-height: 200px;
		overflow-y: auto;
		padding: var(--space-2);
		background: var(--color-bg-inset);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
	}

	.media-item {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--space-2) var(--space-3);
		align-items: start;
		padding: var(--space-2);
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: background var(--duration-fast) var(--ease-standard);
	}

	.media-item:hover {
		background: var(--color-surface);
	}

	.media-item input {
		margin-top: 3px;
	}

	.media-name {
		font: 500 0.875rem var(--font-body);
		color: var(--color-text-primary);
	}

	.media-desc {
		font: var(--text-caption);
		color: var(--color-text-muted);
		grid-column: 2;
	}

	.footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		padding-top: var(--space-4);
		border-top: 1px solid var(--color-border);
	}

	.btn--secondary {
		background: transparent;
		color: var(--color-text-secondary);
		border-color: var(--color-border);
	}

	.btn--secondary:hover {
		background: var(--color-surface);
	}

	.btn--primary {
		background: var(--color-accent);
		color: var(--color-text-on-accent);
		border-color: var(--color-accent);
	}

	.btn--primary:hover {
		background: var(--color-accent-hover);
		border-color: var(--color-accent-hover);
	}

	.btn--primary:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
</style>
