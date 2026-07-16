<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n';
	import { 
		listInteractions, 
		listMedias, 
		uploadMedia,
		updateMedia,
		deleteMedia
	} from '$lib/api';
	import { isAuthenticated } from '$lib/auth';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import type { Interaction, Media } from '$lib/types';

	let interactions = $state<Interaction[]>([]);
	let medias = $state<Media[]>([]);

	let activeTab = $state<'list' | 'upload'>('list');
	let loading = $state(true);
	let processing = $state(false);
	let error = $state<string | null>(null);

	// Upload form
	let uploadFile = $state<FileList | null>(null);
	let uploadName = $state('');

	// Edit modal
	let editingMedia = $state<Media | null>(null);
	let editName = $state('');
	let editDescription = $state('');
	let editProcessing = $state(false);

	onMount(async () => {
		if (!browser) return;
		if (!isAuthenticated()) {
			await goto('/');
			return;
		}

		try {
			const [interactionsData, mediasData] = await Promise.all([
				listInteractions(20),
				listMedias()
			]);
			interactions = interactionsData;
			medias = mediasData;
		} catch (err) {
			error = err instanceof Error ? err.message : $t('dashboard.loadError');
		} finally {
			loading = false;
		}
	});

	async function handleUpload(event: Event) {
		event.preventDefault();
		if (!uploadFile || uploadFile.length === 0) return;

		processing = true;
		error = null;

		try {
			const file = uploadFile[0];
			const media = await uploadMedia(file, uploadName.trim() || undefined);
			medias = [media, ...medias];
			uploadFile = null;
			uploadName = '';
			activeTab = 'list';
		} catch (err) {
			error = err instanceof Error ? err.message : $t('common.error');
		} finally {
			processing = false;
		}
	}

	async function handleDelete(mediaId: string) {
		if (!confirm($t('materials.deleteConfirm'))) return;

		processing = true;
		error = null;
		
		try {
			await deleteMedia(mediaId);
			medias = medias.filter((m) => m.id !== mediaId);
		} catch (err) {
			error = err instanceof Error ? err.message : $t('common.error');
		} finally {
			processing = false;
		}
	}

	function openEdit(media: Media) {
		editingMedia = media;
		editName = media.name;
		editDescription = media.description?.written_description || '';
	}

	function closeEdit() {
		editingMedia = null;
		editName = '';
		editDescription = '';
	}

	async function handleEditSubmit(event: Event) {
		event.preventDefault();
		if (!editingMedia) return;

		editProcessing = true;
		error = null;

		try {
			const updated = await updateMedia(
				editingMedia.id, 
				editName.trim() || undefined,
				editDescription.trim() || undefined
			);
			medias = medias.map(m => m.id === updated.id ? updated : m);
			closeEdit();
		} catch (err) {
			error = err instanceof Error ? err.message : $t('common.error');
		} finally {
			editProcessing = false;
		}
	}
</script>

<div class="page-layout">
	<Sidebar 
		{interactions} 
		onOpenNewConversation={() => goto('/dashboard?action=new_conversation')}
	/>
	<main class="page-main">
		<header class="page-header">
			<div>
				<p class="eyebrow">Dostoevsky</p>
				<h2>{$t('materials.title')}</h2>
				<p class="lede">{$t('materials.lede')}</p>
			</div>
		</header>

		{#if error}
			<div class="error-banner">
				{error}
			</div>
		{/if}

		<div class="tabs" role="tablist">
			<button
				class="tab"
				class:active={activeTab === 'list'}
				onclick={() => (activeTab = 'list')}
				type="button"
				role="tab"
				aria-selected={activeTab === 'list'}
			>
				{$t('materials.title')}
				{#if medias.length > 0}
					<span class="tab-count">{medias.length}</span>
				{/if}
			</button>
			<button
				class="tab"
				class:active={activeTab === 'upload'}
				onclick={() => (activeTab = 'upload')}
				type="button"
				role="tab"
				aria-selected={activeTab === 'upload'}
			>
				{$t('materials.uploadNew')}
			</button>
		</div>

		<div class="page-body">
			{#if loading}
				<div class="empty-state">
					<span class="spinner" aria-hidden="true"></span>
					<p class="empty-text">{$t('common.loading')}</p>
				</div>
			{:else if activeTab === 'list'}
				{#if medias.length === 0}
					<div class="empty-state">
						<p class="empty-text">{$t('materials.empty')}</p>
						<button class="btn" type="button" onclick={() => (activeTab = 'upload')}>
							{$t('materials.uploadNew')}
						</button>
					</div>
				{:else}
					<ul class="media-list">
						{#each medias as media (media.id)}
							<li class="media-item">
								<div class="media-info">
									<h3 class="media-name">{media.name}</h3>
									{#if media.format}
										<span class="media-format">{media.format.toUpperCase()}</span>
									{/if}
									{#if media.description?.written_description}
										<p class="media-desc">{media.description.written_description}</p>
									{/if}
								</div>
								<div class="media-actions">
									<button
										class="action-btn"
										type="button"
										onclick={() => openEdit(media)}
									>
										<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
											<path d="M10.5 1.5l2 2-8 8H2.5v-2l8-8z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" />
										</svg>
									</button>
									<button
										class="action-btn action-btn--danger"
										type="button"
										disabled={processing}
										onclick={() => handleDelete(media.id)}
									>
										<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
											<path d="M2 4h10M5 4V2.5a.5.5 0 01.5-.5h3a.5.5 0 01.5.5V4M6 6.5v4M8 6.5v4M3.5 4l.5 7.5a.5.5 0 00.5.5h5a.5.5 0 00.5-.5L10.5 4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" />
										</svg>
									</button>
								</div>
							</li>
						{/each}
					</ul>
				{/if}
			{:else}
				<form class="form" onsubmit={handleUpload}>
					<label class="field">
						<span class="field-label">File</span>
						<input
							type="file"
							class="input"
							bind:files={uploadFile}
							required
						/>
					</label>

					<label class="field">
						<span class="field-label">{$t('materials.name')} (Optional)</span>
						<input
							class="input"
							type="text"
							bind:value={uploadName}
						/>
					</label>

					<div class="form-footer">
						<button class="btn btn--secondary" type="button" onclick={() => (activeTab = 'list')}>
							{$t('common.cancel')}
						</button>
						<button class="btn" type="submit" disabled={processing || !uploadFile?.length}>
							{#if processing}
								<span class="spinner" aria-hidden="true"></span>
								{$t('common.loading')}
							{:else}
								{$t('materials.uploadNew')}
							{/if}
						</button>
					</div>
				</form>
			{/if}
		</div>
	</main>
</div>

{#if editingMedia}
	<div class="modal-backdrop" onclick={closeEdit}>
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div class="modal" onclick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
			<header class="modal-header">
				<h3>{$t('materials.editTitle')}</h3>
				<button class="close-btn" onclick={closeEdit}>
					<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
						<path d="M1 1l12 12M13 1L1 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
					</svg>
				</button>
			</header>

			<form class="form" onsubmit={handleEditSubmit}>
				<label class="field">
					<span class="field-label">{$t('materials.name')}</span>
					<input
						class="input"
						type="text"
						bind:value={editName}
						required
					/>
				</label>
				<label class="field">
					<span class="field-label">{$t('materials.description')}</span>
					<textarea
						class="input"
						bind:value={editDescription}
						rows="4"
					></textarea>
				</label>
				<div class="form-footer">
					<button class="btn btn--secondary" type="button" onclick={closeEdit}>
						{$t('common.cancel')}
					</button>
					<button class="btn" type="submit" disabled={editProcessing}>
						{#if editProcessing}
							<span class="spinner" aria-hidden="true"></span>
							{$t('common.loading')}
						{:else}
							{$t('common.save')}
						{/if}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<style>
	.page-layout {
		display: flex;
		height: 100vh;
		background: var(--color-bg-base);
	}

	.page-main {
		flex: 1;
		padding: var(--space-8) var(--space-8);
		max-width: 900px;
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		overflow-y: auto;
	}

	.page-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		padding-bottom: var(--space-4);
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

	.page-header h2 {
		font: var(--text-heading);
		color: var(--color-text-primary);
		margin: 0 0 var(--space-2);
	}

	.lede {
		font: 400 1.0625rem / 1.6 var(--font-body);
		color: var(--color-text-secondary);
		max-width: 56ch;
		margin: 0;
	}

	.error-banner {
		padding: var(--space-3);
		background: rgba(239, 68, 68, 0.1);
		color: var(--color-danger);
		border: 1px solid rgba(239, 68, 68, 0.2);
		border-radius: var(--radius-md);
		font: 500 0.875rem var(--font-body);
	}

	.tabs {
		display: flex;
		border-bottom: 1px solid var(--color-border);
		padding: 0;
	}

	.tab {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) 0;
		margin-right: var(--space-5);
		background: transparent;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--color-text-muted);
		font: 500 0.875rem var(--font-body);
		cursor: pointer;
		transition:
			color var(--duration-fast) var(--ease-standard),
			border-color var(--duration-fast) var(--ease-standard);
	}

	.tab:hover {
		color: var(--color-text-secondary);
	}

	.tab.active {
		color: var(--color-accent);
		border-bottom-color: var(--color-accent);
	}

	.tab-count {
		font: 500 0.6875rem var(--font-mono);
		background: var(--color-surface-raised);
		color: var(--color-text-muted);
		padding: 1px 5px;
		border-radius: var(--radius-pill);
	}

	.page-body {
		padding: var(--space-2) 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-4);
		padding: var(--space-8) var(--space-4);
		text-align: center;
	}

	.empty-text {
		font: 400 italic 1rem var(--font-display);
		color: var(--color-text-muted);
		margin: 0;
	}

	.media-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.media-item {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-4);
		padding: var(--space-4);
		background: var(--color-bg-inset);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		transition: border-color var(--duration-fast) var(--ease-standard);
	}

	.media-item:hover {
		border-color: var(--color-border-strong);
	}

	.media-info {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		min-width: 0;
		flex: 1;
	}
	
	.media-name {
		font: 600 0.9375rem var(--font-body);
		color: var(--color-text-primary);
		margin: 0;
	}

	.media-format {
		display: inline-block;
		font: 600 0.625rem var(--font-mono);
		color: var(--color-accent);
		background: rgba(200, 155, 60, 0.1);
		border: 1px solid rgba(200, 155, 60, 0.2);
		padding: 2px 6px;
		border-radius: var(--radius-pill);
		letter-spacing: 0.08em;
		width: fit-content;
	}

	.media-desc {
		font: var(--text-body-sm);
		color: var(--color-text-secondary);
		margin: 0;
		word-break: break-word;
	}

	.media-actions {
		display: flex;
		gap: var(--space-2);
	}

	.action-btn {
		background: transparent;
		border: 1px solid transparent;
		border-radius: var(--radius-md);
		color: var(--color-text-muted);
		cursor: pointer;
		padding: var(--space-2);
		display: flex;
		align-items: center;
		transition: all var(--duration-fast) var(--ease-standard);
	}

	.action-btn:hover {
		color: var(--color-text-primary);
		background: var(--color-surface);
	}

	.action-btn--danger:hover {
		color: var(--color-danger);
		border-color: rgba(140, 59, 59, 0.3);
		background: rgba(140, 59, 59, 0.08);
	}
	
	.action-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		max-width: 560px;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.field-label {
		font: 500 0.6875rem var(--font-body);
		letter-spacing: var(--letter-caption);
		text-transform: uppercase;
		color: var(--color-text-muted);
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

	.form-footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-3);
		padding-top: var(--space-4);
		border-top: 1px solid var(--color-border);
		margin-top: var(--space-2);
	}

	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-4);
		background: var(--color-accent);
		color: var(--color-text-on-accent);
		border: 1px solid var(--color-accent);
		border-radius: var(--radius-md);
		font: 500 0.9375rem var(--font-body);
		cursor: pointer;
		transition: all var(--duration-fast) var(--ease-standard);
	}

	.btn:hover:not(:disabled) {
		background: var(--color-accent-hover);
		border-color: var(--color-accent-hover);
	}

	.btn--secondary {
		background: transparent;
		color: var(--color-text-secondary);
		border-color: var(--color-border);
	}

	.btn--secondary:hover:not(:disabled) {
		background: var(--color-surface-raised);
		border-color: var(--color-border-strong);
		color: var(--color-text-primary);
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.spinner {
		display: inline-block;
		width: 12px;
		height: 12px;
		border: 2px solid rgba(16, 21, 26, 0.3);
		border-top-color: var(--color-text-on-accent);
		border-radius: 50%;
		animation: spin 600ms linear infinite;
	}
	
	.modal-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.4);
		backdrop-filter: blur(2px);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
	}

	.modal {
		background: var(--color-bg);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		width: 100%;
		max-width: 480px;
		padding: var(--space-6);
		box-shadow: var(--shadow-lg);
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--space-5);
	}

	.modal-header h3 {
		font: var(--text-heading);
		margin: 0;
	}

	.close-btn {
		background: transparent;
		border: none;
		color: var(--color-text-muted);
		cursor: pointer;
		padding: var(--space-1);
		transition: color var(--duration-fast) var(--ease-standard);
	}

	.close-btn:hover {
		color: var(--color-text-primary);
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
