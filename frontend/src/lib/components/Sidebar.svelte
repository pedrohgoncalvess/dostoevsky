<script lang="ts">
	import { goto } from '$app/navigation';
	import { logout } from '$lib/auth';
	import { t, formatDate, locale, type Locale } from '$lib/i18n';
	import type { Interaction } from '$lib/types';

	interface Props {
		interactions: Interaction[];
		onOpenNewConversation?: () => void;
		onOpenStudyPlans?: () => void;
	}

	let { interactions, onOpenNewConversation, onOpenStudyPlans }: Props = $props();

	let historyOpen = $state(false);
	let configOpen = $state(false);
	let searchQuery = $state('');

	const recentInteractions = $derived(
		interactions
			.filter((i) => {
				if (!searchQuery.trim()) return true;
				const q = searchQuery.toLowerCase();
				return (
					(i.name ?? '').toLowerCase().includes(q) ||
					(i.profile_name ?? '').toLowerCase().includes(q)
				);
			})
			.slice(0, 5)
	);

	async function openConversation(id: string) {
		await goto(`/conversation?id=${id}`);
	}

	function handleLogout() {
		logout();
	}

	function setLanguage(value: Locale) {
		locale.set(value);
	}
</script>

<aside class="sidebar">
	<div class="wordmark">
		<span class="mark">{$t('common.appName')}</span>
		<span class="rule"></span>
		<span class="cyr">{$t('common.appNameCyrillic')}</span>
	</div>

	<nav class="nav">
		<div class="nav-section">
			<button class="nav-item nav-item--primary" onclick={() => onOpenNewConversation?.()}>
				<span class="icon">+</span>
				{$t('sidebar.newConversation')}
			</button>
		</div>

		<div class="nav-section">
			<button class="nav-item" onclick={() => onOpenStudyPlans?.()}>
				<span class="icon">✎</span>
				{$t('sidebar.studyPlans')}
			</button>
		</div>

		<div class="nav-section">
			<button
				class="nav-item"
				onclick={() => (historyOpen = !historyOpen)}
				aria-expanded={historyOpen}
			>
				<span class="icon">⌘</span>
				{$t('sidebar.history')}
				<span class="chevron" class:open={historyOpen}>›</span>
			</button>

			{#if historyOpen}
				<div class="dropdown">
					<input
						class="input search-input"
						type="text"
						placeholder={$t('sidebar.searchPlaceholder')}
						bind:value={searchQuery}
					/>

					{#if recentInteractions.length === 0}
						<p class="empty">{$t('sidebar.noConversations')}</p>
					{:else}
						<ul class="history-list">
							{#each recentInteractions as interaction (interaction.id)}
								<li>
									<button class="history-item" onclick={() => openConversation(interaction.id)}>
										<span class="history-item__name">
											{interaction.name || `${$t('sidebar.unnamedSession')} ${interaction.id}`}
										</span>
										<span class="history-item__meta">
											{formatDate(interaction.inserted_at)}
										</span>
									</button>
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			{/if}
		</div>

		<div class="nav-section">
			<button
				class="nav-item"
				onclick={() => (configOpen = !configOpen)}
				aria-expanded={configOpen}
			>
				<span class="icon">⚙</span>
				{$t('sidebar.configuration')}
				<span class="chevron" class:open={configOpen}>›</span>
			</button>

			{#if configOpen}
				<div class="dropdown">
					<label class="field">
						<span class="field-label">{$t('sidebar.language')}</span>
						<select
							class="input language-select"
							onchange={(e) => setLanguage(e.currentTarget.value as Locale)}
						>
							<option value="en" selected={$locale === 'en'}>{$t('sidebar.english')}</option>
							<option value="pt" selected={$locale === 'pt'}>{$t('sidebar.portuguese')}</option>
						</select>
					</label>
				</div>
			{/if}
		</div>

		<div class="nav-section nav-section--bottom">
			<button class="nav-item nav-item--danger" onclick={handleLogout}>
				<span class="icon">→</span>
				{$t('sidebar.logout')}
			</button>
		</div>
	</nav>
</aside>

<style>
	.sidebar {
		width: 260px;
		min-height: 100%;
		background: var(--color-bg-inset);
		border-right: 1px solid var(--color-border);
		padding: var(--space-5) var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.wordmark {
		display: flex;
		align-items: baseline;
		gap: var(--space-3);
		padding-bottom: var(--space-4);
		border-bottom: 1px solid var(--color-border);
	}

	.mark {
		font: 700 1.1rem var(--font-display);
		color: var(--color-accent);
		letter-spacing: 0.02em;
	}

	.rule {
		flex: 1;
		height: 1px;
		background: var(--color-border);
	}

	.cyr {
		font: 400 italic 0.875rem var(--font-display);
		color: var(--color-text-muted);
	}

	.nav {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		flex: 1;
	}

	.nav-section {
		display: flex;
		flex-direction: column;
	}

	.nav-item {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		width: 100%;
		padding: var(--space-3) var(--space-3);
		background: transparent;
		border: 1px solid transparent;
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		font: 500 0.9375rem var(--font-body);
		text-align: left;
		cursor: pointer;
		transition:
			background var(--duration-fast) var(--ease-standard),
			color var(--duration-fast) var(--ease-standard);
	}

	.nav-item:hover {
		background: var(--color-surface);
		color: var(--color-text-primary);
	}

	.nav-item:focus-visible {
		outline: var(--border-width-active) solid var(--color-focus-ring);
		outline-offset: 2px;
	}

	.nav-item:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.nav-item--primary {
		background: var(--color-accent);
		color: var(--color-text-on-accent);
		border-color: var(--color-accent);
	}

	.nav-item--primary:hover:not(:disabled) {
		background: var(--color-accent-hover);
		border-color: var(--color-accent-hover);
	}

	.icon {
		font: 500 1rem var(--font-mono);
	}

	.chevron {
		margin-left: auto;
		font: 500 1rem var(--font-mono);
		transition: transform var(--duration-fast) var(--ease-standard);
	}

	.chevron.open {
		transform: rotate(90deg);
	}

	.dropdown {
		margin-top: var(--space-2);
		padding: var(--space-3);
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.search-input {
		background: var(--color-bg-inset);
		font: var(--text-body-sm);
		padding: var(--space-2) var(--space-3);
	}

	.empty {
		font: var(--text-caption);
		color: var(--color-text-muted);
		padding: var(--space-2);
	}

	.history-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.history-item {
		width: 100%;
		padding: var(--space-2);
		background: transparent;
		border: 1px solid transparent;
		border-radius: var(--radius-sm);
		color: var(--color-text-secondary);
		cursor: pointer;
		text-align: left;
		transition:
			background var(--duration-fast) var(--ease-standard),
			color var(--duration-fast) var(--ease-standard);
	}

	.history-item:hover {
		background: var(--color-bg-inset);
		color: var(--color-text-primary);
	}

	.history-item__name {
		display: block;
		font: 500 0.875rem var(--font-body);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.history-item__meta {
		display: block;
		font: var(--text-caption);
		color: var(--color-text-muted);
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

	.language-select {
		background: var(--color-bg-inset);
		font: var(--text-body-sm);
		padding: var(--space-2) var(--space-3);
		cursor: pointer;
	}

	.nav-section--bottom {
		margin-top: auto;
		padding-top: var(--space-4);
		border-top: 1px solid var(--color-border);
	}

	.nav-item--danger {
		color: var(--color-danger);
	}

	.nav-item--danger:hover {
		background: rgba(140, 59, 59, 0.12);
		color: var(--color-danger);
	}
</style>
