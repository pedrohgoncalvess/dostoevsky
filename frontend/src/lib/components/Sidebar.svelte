<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { logout } from '$lib/auth';
	import { t, formatDate, locale, type Locale } from '$lib/i18n';
	import type { Interaction } from '$lib/types';

	interface Props {
		interactions: Interaction[];
		onOpenNewConversation?: () => void;
		onOpenSettings?: (interaction: Interaction) => void;
	}

	let { interactions, onOpenNewConversation, onOpenSettings }: Props = $props();

	let searchQuery = $state('');
	let settingsExpanded = $state(page.url.pathname.startsWith('/settings'));

	const currentId = $derived(page.url.searchParams.get('id'));

	const filteredInteractions = $derived(
		interactions.filter((i) => {
			if (!searchQuery.trim()) return true;
			const q = searchQuery.toLowerCase();
			return (
				(i.name ?? '').toLowerCase().includes(q) ||
				(i.profile_name ?? '').toLowerCase().includes(q)
			);
		})
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
		<div class="nav-primary">
			<button class="btn-new" onclick={() => onOpenNewConversation?.()}>
				<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
					<path d="M7 1v12M1 7h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
				</svg>
				{$t('sidebar.newConversation')}
			</button>

			<button class="nav-item" class:active={page.url.pathname.startsWith('/study-plans')} onclick={() => goto('/study-plans')}>
				<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
					<rect x="1" y="1" width="8" height="10" rx="1" stroke="currentColor" stroke-width="1.2" />
					<path d="M4 4h5M4 6.5h5M4 9h3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
					<path d="M10 7l2.5-2.5M10 7l1 2.5 2.5-2.5-1-2.5" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" />
				</svg>
				{$t('sidebar.studyPlans')}
			</button>

			<button class="nav-item" class:active={page.url.pathname.startsWith('/medias')} onclick={() => goto('/medias')}>
				<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
					<path d="M13 13H1V1h8l4 4v8z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" />
					<path d="M9 1v4h4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" />
				</svg>
				{$t('sidebar.materials')}
			</button>

			<button class="nav-item nav-item--expandable" onclick={() => settingsExpanded = !settingsExpanded}>
				<div class="nav-item__left">
					<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
						<circle cx="7" cy="7" r="2" stroke="currentColor" stroke-width="1.2"/>
						<path d="M7 1.5v1M7 11.5v1M1.5 7h1M11.5 7h1M3.4 3.4l.7.7M9.9 9.9l.7.7M10.6 3.4l-.7.7M4.1 9.9l-.7.7" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
					</svg>
					{$t('sidebar.settings')}
				</div>
				<svg class="chevron" class:expanded={settingsExpanded} width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor">
					<path d="M2.5 3.5l2.5 2.5 2.5-2.5" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			</button>

			{#if settingsExpanded}
				<div class="nav-submenu">
					<button class="nav-submenu-item" class:active={page.url.pathname === '/settings/audio-models'} onclick={() => goto('/settings/audio-models')}>
						{$t('sidebar.audioModels')}
					</button>
					<button class="nav-submenu-item" class:active={page.url.pathname === '/settings/agents'} onclick={() => goto('/settings/agents')}>
						{$t('sidebar.agents')}
					</button>
					<button class="nav-submenu-item" class:active={page.url.pathname === '/settings/account'} onclick={() => goto('/settings/account')}>
						{$t('sidebar.account')}
					</button>
				</div>
			{/if}
		</div>

		<div class="history-section">
			<p class="section-eyebrow">{$t('sidebar.history')}</p>

			<input
				class="search-input"
				type="text"
				placeholder={$t('sidebar.searchPlaceholder')}
				bind:value={searchQuery}
			/>

			{#if filteredInteractions.length === 0}
				<p class="empty-hint">{$t('sidebar.noConversations')}</p>
			{:else}
				<ul class="history-list">
					{#each filteredInteractions as interaction (interaction.id)}
						<li class="history-item-container">
							<button
								class="history-item"
								class:active={interaction.id === currentId}
								onclick={() => openConversation(interaction.id)}
							>
								<span class="history-item__name">
									{interaction.name || `${$t('sidebar.unnamedSession')} ${interaction.id}`}
								</span>
								<span class="history-item__meta">
									{interaction.profile_name
										? `${interaction.profile_name} · `
										: ''}{formatDate(interaction.inserted_at)}
								</span>
							</button>
							<button 
								class="history-item-settings" 
								aria-label="Settings" 
								onclick={() => onOpenSettings?.(interaction)}
							>
								<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-settings">
									<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path>
									<circle cx="12" cy="12" r="3"></circle>
								</svg>
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		</div>

		<div class="config-section">
			<p class="section-eyebrow">{$t('sidebar.configuration')}</p>
			<label class="field">
				<span class="field-label">{$t('sidebar.language')}</span>
				<select
					class="select-input"
					onchange={(e) => setLanguage(e.currentTarget.value as Locale)}
				>
					<option value="en" selected={$locale === 'en'}>{$t('sidebar.english')}</option>
					<option value="pt" selected={$locale === 'pt'}>{$t('sidebar.portuguese')}</option>
				</select>
			</label>
		</div>

		<div class="nav-bottom">
			<button class="nav-item nav-item--danger" onclick={handleLogout}>
				<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
					<path d="M5 2H2a1 1 0 00-1 1v8a1 1 0 001 1h3M9 10l3-3-3-3M12 7H5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" />
				</svg>
				{$t('sidebar.logout')}
			</button>
		</div>
	</nav>
</aside>

<style>
	.sidebar {
		width: 260px;
		height: 100vh;
		background: var(--color-bg-inset);
		border-right: 1px solid var(--color-border);
		padding: var(--space-5) var(--space-4);
		display: flex;
		flex-direction: column;
		gap: 0;
		position: sticky;
		top: 0;
		overflow-y: auto;
	}

	.wordmark {
		display: flex;
		align-items: baseline;
		gap: var(--space-3);
		padding-bottom: var(--space-5);
		border-bottom: 1px solid var(--color-border);
		margin-bottom: var(--space-5);
		flex-shrink: 0;
	}

	.mark {
		font: 700 1.0625rem / 1 var(--font-display);
		color: var(--color-accent);
		letter-spacing: 0.04em;
	}

	.rule {
		flex: 1;
		height: 1px;
		background: var(--color-border);
	}

	.cyr {
		font: 400 italic 0.8125rem var(--font-display);
		color: var(--color-text-muted);
	}

	.nav {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0;
		min-height: 0;
	}

	.nav-primary {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		margin-bottom: var(--space-5);
	}

	.btn-new {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-3) var(--space-3);
		background: var(--color-accent);
		color: var(--color-text-on-accent);
		border: 1px solid var(--color-accent);
		border-radius: var(--radius-md);
		font: 500 0.9375rem var(--font-body);
		text-align: left;
		cursor: pointer;
		transition:
			background var(--duration-fast) var(--ease-standard),
			border-color var(--duration-fast) var(--ease-standard);
	}

	.btn-new:hover {
		background: var(--color-accent-hover);
		border-color: var(--color-accent-hover);
	}

	.btn-new:focus-visible {
		outline: 2px solid var(--color-focus-ring);
		outline-offset: 2px;
	}

	.nav-item {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-2) var(--space-3);
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
		outline: 2px solid var(--color-focus-ring);
		outline-offset: 2px;
	}

	.nav-item--expandable {
		justify-content: space-between;
	}

	.nav-item__left {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.chevron {
		color: var(--color-text-muted);
		transition: transform var(--duration-fast) var(--ease-standard);
	}

	.chevron.expanded {
		transform: rotate(180deg);
	}

	.nav-submenu {
		display: flex;
		flex-direction: column;
		gap: 1px;
		margin-left: 28px;
		margin-top: -var(--space-1);
		margin-bottom: var(--space-2);
	}

	.nav-submenu-item {
		width: 100%;
		text-align: left;
		padding: var(--space-2) var(--space-2);
		background: transparent;
		border: none;
		border-radius: var(--radius-sm);
		color: var(--color-text-secondary);
		font: 400 0.8125rem var(--font-body);
		cursor: pointer;
		transition: all var(--duration-fast) var(--ease-standard);
	}

	.nav-submenu-item:hover {
		color: var(--color-text-primary);
		background: var(--color-surface);
	}

	.nav-submenu-item.active {
		color: var(--color-accent);
		background: rgba(200, 155, 60, 0.06);
		font-weight: 500;
	}

	.history-section {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		min-height: 0;
		margin-bottom: var(--space-5);
	}

	.section-eyebrow {
		font: 500 0.6875rem var(--font-body);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--color-text-muted);
		margin: 0 0 var(--space-1);
		padding: 0 var(--space-1);
	}

	.search-input {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		font: 400 0.8125rem var(--font-body);
		color: var(--color-text-primary);
		transition: border-color var(--duration-fast) var(--ease-standard);
	}

	.search-input::placeholder {
		color: var(--color-text-muted);
	}

	.search-input:focus {
		outline: none;
		border-color: var(--color-accent);
	}

	.empty-hint {
		font: var(--text-caption);
		color: var(--color-text-muted);
		padding: var(--space-2) var(--space-1);
		margin: 0;
	}

	.history-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 1px;
		overflow-y: auto;
		flex: 1;
	}

	.history-item-container {
		display: flex;
		align-items: stretch;
		width: 100%;
		border-left: 2px solid transparent;
		border-radius: var(--radius-sm);
		transition: border-left-color var(--duration-fast) var(--ease-standard),
		            background var(--duration-fast) var(--ease-standard);
	}
	
	.history-item-container:has(.history-item.active) {
		border-left-color: var(--color-accent);
		background: rgba(200, 155, 60, 0.06);
	}
	
	.history-item-container:hover {
		background: var(--color-surface);
	}

	.history-item {
		flex: 1;
		min-width: 0;
		padding: var(--space-2) var(--space-2) var(--space-2) var(--space-3);
		background: transparent;
		border: none;
		color: var(--color-text-muted);
		cursor: pointer;
		text-align: left;
		transition: color var(--duration-fast) var(--ease-standard);
	}

	.history-item-container:hover .history-item {
		color: var(--color-text-primary);
	}

	.history-item.active {
		color: var(--color-text-primary);
	}
	
	.history-item-settings {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		background: transparent;
		border: none;
		color: var(--color-text-muted);
		cursor: pointer;
		opacity: 0.6;
		transition: opacity var(--duration-fast) var(--ease-standard), color var(--duration-fast) var(--ease-standard);
	}
	
	.history-item-settings:hover {
		opacity: 1;
		color: var(--color-text-primary);
	}

	.history-item__name {
		display: block;
		font: 500 0.8125rem var(--font-body);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.history-item__meta {
		display: block;
		font: 400 0.6875rem var(--font-mono);
		color: var(--color-text-muted);
		margin-top: 1px;
	}

	.config-section {
		padding-top: var(--space-4);
		border-top: 1px solid var(--color-border);
		margin-bottom: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.field-label {
		font: var(--text-caption);
		letter-spacing: var(--letter-caption);
		text-transform: uppercase;
		color: var(--color-text-muted);
	}

	.select-input {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		font: 400 0.8125rem var(--font-body);
		color: var(--color-text-primary);
		cursor: pointer;
	}

	.select-input:focus {
		outline: none;
		border-color: var(--color-accent);
	}

	.nav-bottom {
		padding-top: var(--space-4);
		border-top: 1px solid var(--color-border);
		flex-shrink: 0;
	}

	.nav-item--danger {
		color: var(--color-danger);
	}

	.nav-item--danger:hover {
		background: rgba(140, 59, 59, 0.1);
		color: var(--color-danger);
	}
</style>
