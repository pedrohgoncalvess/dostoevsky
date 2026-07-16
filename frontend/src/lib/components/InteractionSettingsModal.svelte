<script lang="ts">
	import { t } from '$lib/i18n';
	import type { Media, Interaction } from '$lib/types';
	import { updateInteraction, deleteInteraction } from '$lib/api';

	interface Props {
		interaction: Interaction;
		medias: Media[];
		onSave: (updatedInteraction: Interaction) => void;
		onDelete: (id: string) => void;
		onClose: () => void;
	}

	let { interaction, medias, onSave, onDelete, onClose }: Props = $props();

	// Derived to filter audio files from medias, similar to NewConversationModal
	const AUDIO_FORMATS = new Set(['pcm', 'wav', 'mp3', 'ogg', 'flac', 'm4a', 'aac', 'opus', 'webm']);
	const contextMedias = $derived(medias.filter(m => !m.format || !AUDIO_FORMATS.has(m.format.toLowerCase())));

	let name = $state(interaction.name || '');
	let needTip = $state(interaction.need_tip || false);
	let selectedMediaIds = $state<string[]>(interaction.media_ids || []);
	
	let saving = $state(false);
	let error = $state<string | null>(null);

	function toggleMedia(id: string) {
		if (selectedMediaIds.includes(id)) {
			selectedMediaIds = selectedMediaIds.filter((mediaId) => mediaId !== id);
		} else {
			selectedMediaIds = [...selectedMediaIds, id];
		}
	}

	async function handleSave() {
		error = null;
		saving = true;
		try {
			await updateInteraction(interaction.id, {
				name,
				need_tip: needTip,
				media_ids: selectedMediaIds
			});
			onSave({
				...interaction,
				name,
				need_tip: needTip,
				media_ids: selectedMediaIds
			});
		} catch (err) {
			error = err instanceof Error ? err.message : 'Error updating settings';
		} finally {
			saving = false;
		}
	}

	async function handleDelete() {
		if (!confirm('Tem certeza que deseja excluir esta interação? Esta ação não pode ser desfeita.')) {
			return;
		}
		
		error = null;
		saving = true;
		try {
			await deleteInteraction(interaction.id);
			onDelete(interaction.id);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Error deleting interaction';
			saving = false;
		}
	}
</script>

<div class="overlay" role="presentation" onclick={onClose}>
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div class="modal" role="dialog" aria-modal="true" onclick={(e) => e.stopPropagation()}>
		<header class="modal-header">
			<h2 class="modal-title">Configurações da Interação</h2>
			<button class="btn-close" type="button" aria-label="Close" onclick={onClose}>
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
					<path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
				</svg>
			</button>
		</header>

		<div class="modal-body">
			{#if error}
				<div class="error-bar" role="alert">{error}</div>
			{/if}

			<label class="field">
				<span class="field-label">Nome da Interação</span>
				<input
					type="text"
					class="input"
					placeholder="Ex: Praticando no aeroporto..."
					bind:value={name}
					disabled={saving}
				/>
			</label>

			<label class="field checkbox-field">
				<input
					type="checkbox"
					class="checkbox"
					bind:checked={needTip}
					disabled={saving}
				/>
				<div class="checkbox-text">
					<span class="field-label">{$t('modal.needTipLabel')}</span>
					<span class="field-hint">{$t('modal.needTipHint')}</span>
				</div>
			</label>

			{#if contextMedias.length > 0}
				<div class="field">
					<span class="field-label">{$t('modal.mediaLabel')}</span>
					<span class="field-hint">Adicionar ou remover documentos de contexto</span>
					<div class="media-grid">
						{#each contextMedias as media (media.id)}
							<label class="media-card" class:selected={selectedMediaIds.includes(media.id)}>
								<input
									type="checkbox"
									class="media-checkbox"
									value={media.id}
									checked={selectedMediaIds.includes(media.id)}
									onchange={() => toggleMedia(media.id)}
									disabled={saving}
								/>
								<span class="media-name">{media.name}</span>
								<span class="media-desc">{media.description?.written_description || ''}</span>
							</label>
						{/each}
					</div>
				</div>
			{/if}
			
			<div class="field delete-section">
				<span class="field-label">Zona de Perigo</span>
				<button class="btn btn--danger" type="button" onclick={handleDelete} disabled={saving}>
					Excluir Interação
				</button>
			</div>
		</div>

		<footer class="modal-footer">
			<button class="btn btn--secondary" type="button" onclick={onClose} disabled={saving}>
				{$t('common.cancel')}
			</button>
			<button class="btn btn--primary" type="button" onclick={handleSave} disabled={saving}>
				{#if saving}
					<span class="spinner" aria-hidden="true"></span>
				{:else}
					Salvar
				{/if}
			</button>
		</footer>
	</div>
</div>

<style>
	.overlay {
		position: fixed;
		inset: 0;
		background: rgba(10, 12, 16, 0.7);
		backdrop-filter: blur(8px);
		z-index: 100;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-4);
	}

	.modal {
		width: 100%;
		max-width: 520px;
		background: var(--color-bg);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		box-shadow: 0 24px 48px -12px rgba(0, 0, 0, 0.4);
		display: flex;
		flex-direction: column;
		max-height: 90vh;
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-5);
		border-bottom: 1px solid var(--color-border);
	}

	.modal-title {
		font: 500 1.25rem var(--font-display);
		color: var(--color-text-primary);
		margin: 0;
	}

	.btn-close {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		background: transparent;
		border: none;
		color: var(--color-text-muted);
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition:
			background var(--duration-fast) var(--ease-standard),
			color var(--duration-fast) var(--ease-standard);
	}

	.btn-close:hover {
		background: var(--color-surface-raised);
		color: var(--color-text-primary);
	}

	.modal-body {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-5);
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.error-bar {
		padding: var(--space-3) var(--space-4);
		background: rgba(140, 59, 59, 0.1);
		border-left: 2px solid var(--color-voice-user);
		color: var(--color-voice-user-soft);
		font: var(--text-body-sm);
		border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.field-label {
		font: 500 0.875rem var(--font-body);
		color: var(--color-text-primary);
	}

	.field-hint {
		font: var(--text-caption);
		color: var(--color-text-muted);
	}

	.checkbox-field {
		flex-direction: row;
		align-items: flex-start;
		gap: var(--space-3);
		padding: var(--space-4);
		background: var(--color-bg-inset);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		cursor: pointer;
	}

	.checkbox {
		margin-top: 3px;
	}

	.checkbox-text {
		display: flex;
		flex-direction: column;
		gap: 2px;
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
	
	.delete-section {
		margin-top: var(--space-2);
		padding-top: var(--space-5);
		border-top: 1px dashed var(--color-border-strong);
	}

	.modal-footer {
		display: flex;
		justify-content: flex-end;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-5);
		border-top: 1px solid var(--color-border);
	}

	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		padding: 0 var(--space-5);
		height: 38px;
		font: 500 0.875rem var(--font-body);
		border-radius: var(--radius-md);
		border: 1px solid transparent;
		cursor: pointer;
		transition: all var(--duration-fast) var(--ease-standard);
	}

	.btn--primary {
		background: var(--color-accent);
		color: var(--color-text-on-accent);
	}

	.btn--primary:hover {
		background: var(--color-accent-hover);
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
	
	.btn--danger {
		background: rgba(140, 59, 59, 0.1);
		color: var(--raw-oxblood-400);
		border-color: rgba(140, 59, 59, 0.2);
	}
	
	.btn--danger:hover:not(:disabled) {
		background: rgba(140, 59, 59, 0.2);
		color: var(--raw-oxblood-300);
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
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
	
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
