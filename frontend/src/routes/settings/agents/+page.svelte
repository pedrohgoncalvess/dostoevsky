<script lang="ts">
	import { onMount } from 'svelte';
	import { getAgents, getModels, updateAgentModel } from '$lib/preferences.api';
	import type { AIAgent, ModelsGrouped } from '$lib/preferences.types';

	let models = $state<ModelsGrouped>({ stt: [], tts: [], text: [] });
	let agents = $state<AIAgent[]>([]);

	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let successMsg = $state<string | null>(null);

	let agentModelOverrides = $state<Record<string, number>>({});

	onMount(async () => {
		try {
			const [modelsData, agentsData] = await Promise.all([
				getModels(),
				getAgents()
			]);

			models = modelsData;
			agents = agentsData;

			const overrides: Record<string, number> = {};
			for (const agent of agentsData) {
				if (agent.model) overrides[agent.name] = agent.model.id;
			}
			agentModelOverrides = overrides;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load agents';
		} finally {
			loading = false;
		}
	});

	async function saveAgentModel(agentName: string) {
		const modelId = agentModelOverrides[agentName];
		if (!modelId) return;
		saving = true;
		error = null;
		successMsg = null;
		try {
			const updated = await updateAgentModel(agentName, modelId);
			agents = agents.map((a) => (a.name === agentName ? updated : a));
			successMsg = `Agente "${agentName}" atualizado.`;
			setTimeout(() => (successMsg = null), 3000);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save';
		} finally {
			saving = false;
		}
	}

	function isLocal(id: string): boolean {
		return id.startsWith('local:');
	}
</script>

{#if loading}
	<div class="loading-state">
		<span class="spinner" aria-hidden="true"></span>
		<p>Carregando agentes…</p>
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
			<p class="section-eyebrow">Configuração</p>
			<h2 class="section-title">Agentes</h2>
			<p class="section-desc">
				Escolha qual modelo de linguagem cada agente deve usar. O agente <em>teacher</em>
				é o responsável pela conversa principal.
			</p>
		</header>

		<div class="cards">
			{#each agents as agent (agent.id)}
				<div class="pref-card">
					<div class="card-header">
						<span class="card-label">{agent.name}</span>
						{#if agent.description}
							<span class="card-sublabel">{agent.description}</span>
						{/if}
					</div>

					{#if agent.model}
						<div class="current-badge">
							<span class="badge-dot" class:local={isLocal(agent.model.external_id)}></span>
							<span class="badge-text">{agent.model.name}</span>
							<code class="model-id-code">{agent.model.external_id}</code>
						</div>
					{/if}

					<label class="field">
						<span class="field-label">Modelo LLM</span>
						<select
							class="input"
							value={agentModelOverrides[agent.name] ?? ''}
							onchange={(e) => {
								const v = (e.target as HTMLSelectElement).value;
								if (v) agentModelOverrides[agent.name] = Number(v);
							}}
						>
							<option value="" disabled>Selecionar modelo</option>
							{#each models.text as model (model.id)}
								<option value={model.id}>{model.name}</option>
							{/each}
						</select>
					</label>

					<div class="card-footer">
						<button
							class="btn btn--sm"
							onclick={() => saveAgentModel(agent.name)}
							disabled={saving || !agentModelOverrides[agent.name]}
						>
							{saving ? 'Salvando…' : 'Aplicar'}
						</button>
					</div>
				</div>
			{/each}

			{#if agents.length === 0}
				<div class="empty-state">
					<p class="empty-text">Nenhum agente configurado.</p>
				</div>
			{/if}
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

	.card-header {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.card-label {
		font: 600 0.9375rem var(--font-body);
		color: var(--color-text-primary);
	}

	.card-sublabel {
		font: var(--text-caption);
		color: var(--color-text-muted);
	}

	.card-footer {
		display: flex;
		justify-content: flex-end;
		padding-top: var(--space-3);
		border-top: 1px solid var(--color-border);
	}

	.current-badge {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: var(--color-bg-inset);
		border-radius: var(--radius-md);
		border: 1px solid var(--color-border);
	}

	.badge-dot {
		width: 6px;
		height: 6px;
		border-radius: var(--radius-pill);
		background: var(--color-border-strong);
		flex-shrink: 0;
	}

	.badge-dot.local {
		background: var(--color-success);
	}

	.badge-text {
		font: 500 0.8125rem var(--font-body);
		color: var(--color-text-primary);
		flex: 1;
		min-width: 0;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.model-id-code {
		font: 400 0.75rem var(--font-mono);
		color: var(--color-text-muted);
		background: var(--color-bg-inset);
		padding: 1px 5px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--color-border);
		max-width: 220px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
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

	.btn--sm {
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

	.empty-state {
		padding: var(--space-8);
		text-align: center;
	}

	.empty-text {
		font: 400 italic 1rem var(--font-display);
		color: var(--color-text-muted);
		margin: 0;
	}
</style>
