<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from '$lib/i18n';
	import { getMe } from '$lib/api';
	import type { KnowledgeLevel, Language, StudyPlan, User } from '$lib/types';

	interface Props {
		plans: StudyPlan[];
		loading?: boolean;
		onCreate: (studyLanguage: Language, selfDeclaredLevel: KnowledgeLevel, goal: string) => void;
		onDelete: (planId: string) => void;
		onClose: () => void;
	}

	let { plans, loading = false, onCreate, onDelete, onClose }: Props = $props();

	const languages: Language[] = [
		'portuguese',
		'english',
		'french',
		'spanish',
		'russian',
		'mandarim'
	];
	const levels: KnowledgeLevel[] = ['a1', 'a2', 'b1', 'b2', 'c1', 'c2'];

	let studyLanguage = $state<Language>('english');
	let selfDeclaredLevel = $state<KnowledgeLevel>('a1');
	let goal = $state('');
	let activeTab = $state<'list' | 'create'>('list');
	let user = $state<User | null>(null);

	let availableLanguages = $derived(languages.filter((lang) => lang !== user?.native_language));

	$effect(() => {
		if (!availableLanguages.includes(studyLanguage)) {
			studyLanguage = availableLanguages[0] ?? 'english';
		}
	});

	onMount(async () => {
		try {
			user = await getMe();
		} catch {
			// ignore
		}

		if (plans.length === 0) {
			activeTab = 'create';
		}
	});

	function formatLanguage(language: string): string {
		return language.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
	}

	function handleCreate(event: Event) {
		event.preventDefault();
		onCreate(studyLanguage, selfDeclaredLevel, goal.trim());
		goal = '';
		activeTab = 'list';
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
			<h2>{$t('sidebar.studyPlans')}</h2>
			<button class="close" type="button" onclick={onClose} aria-label={$t('common.cancel')}>
				×
			</button>
		</header>

		<div class="tabs">
			<button
				class="tab"
				class:active={activeTab === 'list'}
				onclick={() => (activeTab = 'list')}
				type="button"
			>
				{$t('sidebar.studyPlans')}
			</button>
			<button
				class="tab"
				class:active={activeTab === 'create'}
				onclick={() => (activeTab = 'create')}
				type="button"
			>
				{$t('sidebar.newStudyPlan')}
			</button>
		</div>

		<div class="body">
			{#if activeTab === 'list'}
				{#if plans.length === 0}
					<div class="empty">
						<p>{$t('sidebar.noStudyPlans')}</p>
						<button class="btn btn--primary" type="button" onclick={() => (activeTab = 'create')}>
							{$t('sidebar.newStudyPlan')}
						</button>
					</div>
				{:else}
					<ul class="plan-list">
						{#each plans as plan (plan.id)}
							<li class="plan-item">
								<div class="plan-main">
									<div class="plan-header">
										<span class="plan-language">{formatLanguage(plan.study_language)}</span>
										<span class="plan-level">{plan.self_declared_level.toUpperCase()}</span>
									</div>
									{#if plan.goal}
										<p class="plan-goal">{plan.goal}</p>
									{/if}
								</div>
								<button
									class="btn btn--danger btn--small"
									type="button"
									disabled={loading}
									onclick={() => onDelete(plan.id)}
								>
									{$t('sidebar.deleteStudyPlan')}
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
						<select class="input" bind:value={selfDeclaredLevel}>
							{#each levels as level (level)}
								<option value={level}>{level.toUpperCase()}</option>
							{/each}
						</select>
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

					<div class="footer">
						<button class="btn btn--secondary" type="button" onclick={() => (activeTab = 'list')}>
							{$t('common.cancel')}
						</button>
						<button class="btn btn--primary" type="submit" disabled={loading}>
							{loading ? $t('common.loading') : $t('modal.studyPlanCreate')}
						</button>
					</div>
				</form>
			{/if}
		</div>
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
		max-width: 560px;
		max-height: 90vh;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		padding: var(--space-5);
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

	.tabs {
		display: flex;
		gap: var(--space-2);
		border-bottom: 1px solid var(--color-border);
	}

	.tab {
		flex: 1;
		padding: var(--space-3);
		background: transparent;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--color-text-secondary);
		font: 500 0.9375rem var(--font-body);
		cursor: pointer;
		transition:
			color var(--duration-fast) var(--ease-standard),
			border-color var(--duration-fast) var(--ease-standard);
	}

	.tab:hover {
		color: var(--color-text-primary);
	}

	.tab.active {
		color: var(--color-accent);
		border-bottom-color: var(--color-accent);
	}

	.body {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		min-height: 0;
	}

	.empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-4);
		text-align: center;
		color: var(--color-text-muted);
		padding: var(--space-6) var(--space-4);
	}

	.plan-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		max-height: 360px;
		overflow-y: auto;
		padding-right: var(--space-2);
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
		transition: background var(--duration-fast) var(--ease-standard);
	}

	.plan-item:hover {
		background: var(--color-surface);
	}

	.plan-main {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		min-width: 0;
		flex: 1;
	}

	.plan-header {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		flex-wrap: wrap;
	}

	.plan-language {
		font: 600 1rem var(--font-body);
		color: var(--color-text-primary);
		text-transform: capitalize;
	}

	.plan-level {
		font: 700 0.75rem var(--font-mono);
		color: var(--color-accent);
		background: rgba(200, 155, 60, 0.12);
		padding: 2px 8px;
		border-radius: var(--radius-sm);
		letter-spacing: 0.08em;
	}

	.plan-goal {
		font: var(--text-body-sm);
		color: var(--color-text-secondary);
		margin: 0;
		word-break: break-word;
	}

	.form {
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

	.btn--danger {
		background: transparent;
		color: var(--color-danger);
		border-color: var(--color-danger);
	}

	.btn--danger:hover {
		background: rgba(140, 59, 59, 0.12);
	}

	.btn--small {
		padding: var(--space-2) var(--space-3);
		font: 500 0.8125rem var(--font-body);
		flex-shrink: 0;
	}
</style>
