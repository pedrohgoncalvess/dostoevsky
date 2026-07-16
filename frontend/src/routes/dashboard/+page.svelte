<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { onMount } from 'svelte';
	import {
		createInteraction,
		listInteractions,
		listProfiles,
		listStudyPlans,
		listMedias
	} from '$lib/api';
	import { isAuthenticated } from '$lib/auth';
	import { t, formatDate } from '$lib/i18n';
	import { page } from '$app/state';
	import NewConversationModal from '$lib/components/NewConversationModal.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import type { Interaction, Media, Profile, StudyPlan } from '$lib/types';

	let interactions = $state<Interaction[]>([]);
	let profiles = $state<Profile[]>([]);
	let studyPlans = $state<StudyPlan[]>([]);
	let medias = $state<Media[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let modalOpen = $state(false);
	let creating = $state(false);

	onMount(async () => {
		if (!browser) return;
		if (!isAuthenticated()) {
			await goto('/');
			return;
		}
		loadData();
	});

	$effect(() => {
		if (page.url.searchParams.get('action') === 'new_conversation') {
			modalOpen = true;
			goto('/dashboard', { replaceState: true });
		}
	});

	async function loadData() {
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
			error = err instanceof Error ? err.message : $t('dashboard.loadError');
		} finally {
			loading = false;
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
			modalOpen = false;
			await goto(`/conversation?id=${interaction.id}`);
		} catch (err) {
			error = err instanceof Error ? err.message : $t('dashboard.createError');
		} finally {
			creating = false;
		}
	}
</script>

<div class="dashboard">
	<Sidebar
		{interactions}
		onOpenNewConversation={() => (modalOpen = true)}
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

	<main class="main">
		<header class="header">
			<p class="eyebrow">{$t('dashboard.eyebrow')}</p>
			<h1>{$t('dashboard.welcome')}</h1>
			<p class="lede">{$t('dashboard.lede')}</p>
		</header>

		{#if loading}
			<p class="status-text">{$t('common.loading')}</p>
		{:else if error}
			<p class="status-text status-text--error" role="alert">{error}</p>
		{:else}
			<section class="section">
				<h2>{$t('dashboard.recentConversations')}</h2>
				{#if interactions.length === 0}
					<div class="empty">
						<p>{$t('dashboard.empty')}</p>
						<button class="btn" onclick={() => (modalOpen = true)}>
							{$t('dashboard.startFirst')}
						</button>
					</div>
				{:else}
					<ul class="interaction-list">
						{#each interactions.slice(0, 5) as interaction (interaction.id)}
							<li class="interaction-card card">
								<a href="/conversation?id={interaction.id}">
									<span class="interaction-name">
										{interaction.name || `${$t('sidebar.unnamedSession')} ${interaction.id}`}
									</span>
									<span class="interaction-meta">
										{formatDate(interaction.inserted_at)}
									</span>
								</a>
							</li>
						{/each}
					</ul>
				{/if}
			</section>
		{/if}
	</main>
</div>

<style>
	.dashboard {
		display: grid;
		grid-template-columns: 260px 1fr;
		min-height: 100vh;
		background: var(--color-bg);
	}

	.main {
		padding: var(--space-6) var(--space-7);
		overflow-y: auto;
	}

	.header {
		margin-bottom: var(--space-6);
		padding-bottom: var(--space-5);
		border-bottom: 1px solid var(--color-border);
	}

	h1 {
		font: var(--text-display-l);
		margin: var(--space-2) 0;
	}

	.lede {
		font: 400 1.0625rem / 1.6 var(--font-body);
		color: var(--color-text-secondary);
		max-width: 56ch;
	}

	.section {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.section h2 {
		font: var(--text-heading);
		color: var(--color-text-primary);
	}

	.status-text {
		font: var(--text-body);
		color: var(--color-text-muted);
	}

	.status-text--error {
		color: var(--color-danger);
	}

	.empty {
		padding: var(--space-6);
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		text-align: center;
		color: var(--color-text-secondary);
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-4);
	}

	.interaction-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: var(--space-3);
	}

	.interaction-card a {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-4);
		color: inherit;
		transition: background var(--duration-fast) var(--ease-standard);
	}

	.interaction-card a:hover {
		background: var(--color-surface-raised);
	}

	.interaction-name {
		font: 500 1rem var(--font-body);
		color: var(--color-text-primary);
	}

	.interaction-meta {
		font: var(--text-caption);
		color: var(--color-text-muted);
	}
</style>
