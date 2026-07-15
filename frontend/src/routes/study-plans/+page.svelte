<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n';
	import { 
		createStudyPlan, 
		deleteStudyPlan, 
		listInteractions, 
		listStudyPlans, 
		getMe 
	} from '$lib/api';
	import { isAuthenticated } from '$lib/auth';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import type { Interaction, KnowledgeLevel, Language, StudyPlan, User } from '$lib/types';

	const languages: Language[] = [
		'portuguese',
		'english',
		'french',
		'spanish',
		'russian',
		'mandarim'
	];
	const levels: KnowledgeLevel[] = ['a1', 'a2', 'b1', 'b2', 'c1', 'c2'];

	let interactions = $state<Interaction[]>([]);
	let studyPlans = $state<StudyPlan[]>([]);
	let user = $state<User | null>(null);

	let studyLanguage = $state<Language>('english');
	let selfDeclaredLevel = $state<KnowledgeLevel>('a1');
	let goal = $state('');
	
	let activeTab = $state<'list' | 'create'>('list');
	let loading = $state(true);
	let processing = $state(false);
	let error = $state<string | null>(null);
	let feedback = $state<string | null>(null);

	let availableLanguages = $derived(languages.filter((lang) => lang !== user?.native_language));

	$effect(() => {
		if (!availableLanguages.includes(studyLanguage)) {
			studyLanguage = availableLanguages[0] ?? 'english';
		}
	});

	onMount(async () => {
		if (!browser) return;
		if (!isAuthenticated()) {
			await goto('/');
			return;
		}

		try {
			const [interactionsData, studyPlansData, userData] = await Promise.all([
				listInteractions(20),
				listStudyPlans(),
				getMe().catch(() => null)
			]);
			interactions = interactionsData;
			studyPlans = studyPlansData;
			user = userData;

			if (studyPlans.length === 0) {
				activeTab = 'create';
			}
		} catch (err) {
			error = err instanceof Error ? err.message : $t('dashboard.loadError');
		} finally {
			loading = false;
		}
	});

	function formatLanguage(language: string): string {
		return language.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
	}

	async function handleCreate(event: Event) {
		event.preventDefault();
		processing = true;
		error = null;
		feedback = null;

		try {
			const { plan, feedback: planFeedback } = await createStudyPlan(
				studyLanguage,
				selfDeclaredLevel,
				goal.trim()
			);
			studyPlans = [plan, ...studyPlans];
			feedback = planFeedback;
			goal = '';
			activeTab = 'list';
		} catch (err) {
			error = err instanceof Error ? err.message : $t('common.error');
		} finally {
			processing = false;
		}
	}

	async function handleDelete(planId: string) {
		processing = true;
		error = null;
		
		try {
			await deleteStudyPlan(planId);
			studyPlans = studyPlans.filter((p) => p.id !== planId);
		} catch (err) {
			error = err instanceof Error ? err.message : $t('common.error');
		} finally {
			processing = false;
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
				<h2>{$t('sidebar.studyPlans')}</h2>
			</div>
		</header>

		{#if error}
			<div class="error-banner">
				{error}
			</div>
		{/if}

		{#if feedback}
			<div class="feedback-banner">
				{feedback}
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
				{$t('sidebar.studyPlans')}
				{#if studyPlans.length > 0}
					<span class="tab-count">{studyPlans.length}</span>
				{/if}
			</button>
			<button
				class="tab"
				class:active={activeTab === 'create'}
				onclick={() => (activeTab = 'create')}
				type="button"
				role="tab"
				aria-selected={activeTab === 'create'}
			>
				{$t('sidebar.newStudyPlan')}
			</button>
		</div>

		<div class="page-body">
			{#if loading}
				<div class="empty-state">
					<span class="spinner" aria-hidden="true"></span>
					<p class="empty-text">{$t('common.loading')}</p>
				</div>
			{:else if activeTab === 'list'}
				{#if studyPlans.length === 0}
					<div class="empty-state">
						<p class="empty-text">{$t('sidebar.noStudyPlans')}</p>
						<button class="btn" type="button" onclick={() => (activeTab = 'create')}>
							{$t('sidebar.newStudyPlan')}
						</button>
					</div>
				{:else}
					<ul class="plan-list">
						{#each studyPlans as plan (plan.id)}
							<li class="plan-item">
								<div class="plan-info">
									<div class="plan-meta">
										<span class="plan-language">{formatLanguage(plan.study_language)}</span>
										<span class="plan-level">{plan.self_declared_level.toUpperCase()}</span>
									</div>
									{#if plan.goal}
										<p class="plan-goal">{plan.goal}</p>
									{/if}
								</div>
								<button
									class="delete-btn"
									type="button"
									disabled={processing}
									onclick={() => handleDelete(plan.id)}
									aria-label="{$t('sidebar.deleteStudyPlan')} {formatLanguage(plan.study_language)}"
								>
									<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
										<path d="M2 4h10M5 4V2.5a.5.5 0 01.5-.5h3a.5.5 0 01.5.5V4M6 6.5v4M8 6.5v4M3.5 4l.5 7.5a.5.5 0 00.5.5h5a.5.5 0 00.5-.5L10.5 4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" />
									</svg>
								</button>
							</li>
						{/each}
					</ul>
				{/if}
			{:else}
				<form class="form" onsubmit={handleCreate}>
					<label class="field">
						<span class="field-label">{$t('modal.studyPlanLanguageLabel')}</span>
						<select class="input" bind:value={studyLanguage}>
							{#each availableLanguages as lang (lang)}
								<option value={lang}>{formatLanguage(lang)}</option>
							{/each}
						</select>
					</label>

					<label class="field">
						<span class="field-label">{$t('modal.studyPlanLevelLabel')}</span>
						<div class="level-grid">
							{#each levels as level (level)}
								<label class="level-option" class:selected={selfDeclaredLevel === level}>
									<input
										type="radio"
										name="level"
										value={level}
										bind:group={selfDeclaredLevel}
										class="visually-hidden"
									/>
									{level.toUpperCase()}
								</label>
							{/each}
						</div>
					</label>

					<label class="field">
						<span class="field-label">{$t('modal.studyPlanGoalLabel')}</span>
						<input
							class="input"
							type="text"
							placeholder={$t('modal.studyPlanGoalPlaceholder')}
							bind:value={goal}
						/>
					</label>

					<div class="form-footer">
						<button class="btn btn--secondary" type="button" onclick={() => (activeTab = 'list')}>
							{$t('common.cancel')}
						</button>
						<button class="btn" type="submit" disabled={processing}>
							{#if processing}
								<span class="spinner" aria-hidden="true"></span>
								{$t('common.loading')}
							{:else}
								{$t('modal.studyPlanCreate')}
							{/if}
						</button>
					</div>
				</form>
			{/if}
		</div>
	</main>
</div>

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

	.feedback-banner {
		padding: var(--space-3);
		background: rgba(var(--color-accent-rgb), 0.1);
		color: var(--color-text-secondary);
		border: 1px solid var(--color-accent);
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

	.plan-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.plan-item {
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

	.plan-item:hover {
		border-color: var(--color-border-strong);
	}

	.plan-info {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		min-width: 0;
		flex: 1;
	}

	.plan-meta {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		flex-wrap: wrap;
	}

	.plan-language {
		font: 600 0.9375rem var(--font-body);
		color: var(--color-text-primary);
		text-transform: capitalize;
	}

	.plan-level {
		font: 600 0.6875rem var(--font-mono);
		color: var(--color-accent);
		background: rgba(200, 155, 60, 0.1);
		border: 1px solid rgba(200, 155, 60, 0.2);
		padding: 2px 7px;
		border-radius: var(--radius-pill);
		letter-spacing: 0.08em;
	}

	.plan-goal {
		font: var(--text-body-sm);
		color: var(--color-text-secondary);
		margin: 0;
		word-break: break-word;
	}

	.delete-btn {
		background: transparent;
		border: 1px solid transparent;
		border-radius: var(--radius-md);
		color: var(--color-text-muted);
		cursor: pointer;
		padding: var(--space-2);
		display: flex;
		align-items: center;
		transition:
			color var(--duration-fast) var(--ease-standard),
			border-color var(--duration-fast) var(--ease-standard),
			background var(--duration-fast) var(--ease-standard);
		flex-shrink: 0;
	}

	.delete-btn:hover {
		color: var(--color-danger);
		border-color: rgba(140, 59, 59, 0.3);
		background: rgba(140, 59, 59, 0.08);
	}

	.delete-btn:disabled {
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

	.level-grid {
		display: flex;
		gap: var(--space-2);
		flex-wrap: wrap;
	}

	.level-option {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-2) var(--space-4);
		background: var(--color-bg-inset);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		font: 600 0.75rem var(--font-mono);
		color: var(--color-text-muted);
		cursor: pointer;
		letter-spacing: 0.08em;
		transition:
			border-color var(--duration-fast) var(--ease-standard),
			color var(--duration-fast) var(--ease-standard),
			background var(--duration-fast) var(--ease-standard);
	}

	.level-option:hover {
		border-color: var(--color-border-strong);
		color: var(--color-text-primary);
	}

	.level-option.selected {
		border-color: var(--color-accent);
		color: var(--color-accent);
		background: rgba(200, 155, 60, 0.08);
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
		transition:
			background var(--duration-fast) var(--ease-standard),
			border-color var(--duration-fast) var(--ease-standard);
	}

	.btn:hover {
		background: var(--color-accent-hover);
		border-color: var(--color-accent-hover);
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

	.spinner {
		display: inline-block;
		width: 12px;
		height: 12px;
		border: 2px solid rgba(16, 21, 26, 0.3);
		border-top-color: var(--color-text-on-accent);
		border-radius: 50%;
		animation: spin 600ms linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
