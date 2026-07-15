<script lang="ts">
	import { onMount } from 'svelte';
	import { getPreferences, updatePreferences } from '$lib/preferences.api';
	import type { UserPreferences } from '$lib/preferences.types';

	let prefs = $state<UserPreferences | null>(null);

	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let successMsg = $state<string | null>(null);

	let selectedNativeLanguage = $state('portuguese');

	const LANGUAGES = [
		{ value: 'portuguese', label: 'Português' },
		{ value: 'english', label: 'English' },
		{ value: 'french', label: 'Français' },
		{ value: 'spanish', label: 'Español' },
		{ value: 'russian', label: 'Русский' },
		{ value: 'mandarim', label: '普通话' }
	];

	onMount(async () => {
		try {
			prefs = await getPreferences();
			selectedNativeLanguage = prefs.native_language ?? 'portuguese';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load account preferences';
		} finally {
			loading = false;
		}
	});

	async function saveAccountPrefs() {
		saving = true;
		error = null;
		successMsg = null;
		try {
			prefs = await updatePreferences({
				native_language: selectedNativeLanguage
			});
			successMsg = 'Conta atualizada.';
			setTimeout(() => (successMsg = null), 3000);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save';
		} finally {
			saving = false;
		}
	}
</script>

{#if loading}
	<div class="loading-state">
		<span class="spinner" aria-hidden="true"></span>
		<p>Carregando conta…</p>
	</div>
{:else}
	{#if error}
		<div class="error-bar" role="alert">
			{error}
		</div>
	{/if}

	{#if successMsg}
		<div class="success-bar" role="status">
			{successMsg}
		</div>
	{/if}

	<section class="section">
		<header class="section-header">
			<p class="section-eyebrow">Conta</p>
			<h2 class="section-title">Idioma nativo</h2>
			<p class="section-desc">
				O idioma nativo é usado pelo agente para personalizar as instruções e correções.
			</p>
		</header>

		<div class="cards">
			<div class="pref-card">
				<label class="field">
					<span class="field-label">Seu idioma nativo</span>
					<div class="lang-grid">
						{#each LANGUAGES as lang}
							<label
								class="lang-option"
								class:selected={selectedNativeLanguage === lang.value}
							>
								<input
									type="radio"
									name="native_language"
									value={lang.value}
									checked={selectedNativeLanguage === lang.value}
									onchange={() => (selectedNativeLanguage = lang.value)}
									class="visually-hidden"
								/>
								{lang.label}
							</label>
						{/each}
					</div>
				</label>

				<div class="card-footer">
					<button class="btn" onclick={saveAccountPrefs} disabled={saving}>
						{saving ? 'Salvando…' : 'Salvar'}
					</button>
				</div>
			</div>
		</div>
	</section>
{/if}

<style>
	.loading-state {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		color: var(--color-text-muted);
		font: var(--text-body-sm);
		padding: var(--space-8);
	}

	.error-bar {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-4);
		background: rgba(140, 59, 59, 0.1);
		border: 1px solid rgba(140, 59, 59, 0.25);
		border-radius: var(--radius-md);
		color: var(--color-danger);
		font: var(--text-body-sm);
	}

	.success-bar {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-4);
		background: rgba(79, 122, 108, 0.1);
		border: 1px solid rgba(79, 122, 108, 0.25);
		border-radius: var(--radius-md);
		color: var(--color-success);
		font: var(--text-body-sm);
		animation: message-enter 200ms var(--ease-out);
	}

	.section {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.section-header {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		padding-bottom: var(--space-5);
		border-bottom: 1px solid var(--color-border);
	}

	.section-eyebrow {
		font: 500 0.6875rem var(--font-body);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--color-accent);
		margin: 0;
	}

	.section-title {
		font: 600 1.25rem / 1.3 var(--font-display);
		color: var(--color-text-primary);
		margin: 0;
	}

	.section-desc {
		font: var(--text-body-sm);
		color: var(--color-text-muted);
		margin: 0;
		max-width: 52ch;
		line-height: 1.6;
	}

	.cards {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.pref-card {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		padding: var(--space-5);
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.card-footer {
		display: flex;
		justify-content: flex-end;
		padding-top: var(--space-3);
		border-top: 1px solid var(--color-border);
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

	.lang-grid {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}

	.lang-option {
		padding: var(--space-2) var(--space-4);
		background: var(--color-bg-inset);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		font: 500 0.875rem var(--font-body);
		color: var(--color-text-muted);
		cursor: pointer;
		transition:
			border-color var(--duration-fast) var(--ease-standard),
			color var(--duration-fast) var(--ease-standard),
			background var(--duration-fast) var(--ease-standard);
	}

	.lang-option:hover {
		border-color: var(--color-border-strong);
		color: var(--color-text-primary);
	}

	.lang-option.selected {
		border-color: var(--color-accent);
		color: var(--color-accent);
		background: rgba(200, 155, 60, 0.08);
	}

	.btn {
		padding: var(--space-2) var(--space-4);
		font-size: 0.8125rem;
	}

	.spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid rgba(16, 21, 26, 0.25);
		border-top-color: var(--color-text-on-accent);
		border-radius: 50%;
		animation: spin 600ms linear infinite;
	}

	.visually-hidden {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}
</style>
