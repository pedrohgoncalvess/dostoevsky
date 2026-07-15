<script lang="ts">
	import { onMount } from 'svelte';
	import { downloadModel, getModels, getPreferences, getVoices, updatePreferences } from '$lib/preferences.api';
	import type { AIModel, AIVoice, ModelsGrouped, UserPreferences } from '$lib/preferences.types';

	let prefs = $state<UserPreferences | null>(null);
	let models = $state<ModelsGrouped>({ stt: [], tts: [], text: [] });
	let voices = $state<AIVoice[]>([]);

	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let successMsg = $state<string | null>(null);

	// Poll interval if there are downloading models
	$effect(() => {
		const isDownloading = 
			models.stt.some(m => m.download_status === 'processing') ||
			models.tts.some(m => m.download_status === 'processing') ||
			voices.some(v => v.download_status === 'processing');
			
		if (isDownloading) {
			const interval = setInterval(async () => {
				try {
					models = await getModels();
					if (selectedTtsId) {
						voices = await getVoices(selectedTtsId);
					}
				} catch {
					// Ignore
				}
			}, 3000);
			return () => clearInterval(interval);
		}
	});

	let selectedSttId = $state<number | null>(null);
	let selectedTtsId = $state<number | null>(null);
	let selectedVoice = $state<string | null>(null);

	onMount(async () => {
		try {
			const [prefsData, modelsData] = await Promise.all([
				getPreferences(),
				getModels()
			]);

			prefs = prefsData;
			models = modelsData;

			selectedSttId = prefsData.stt_model?.id ?? null;
			selectedTtsId = prefsData.tts_model?.id ?? null;
			selectedVoice = prefsData.voice ?? null;

			if (selectedTtsId) {
				voices = await getVoices(selectedTtsId);
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load preferences';
		} finally {
			loading = false;
		}
	});

	async function onTtsModelChange(modelId: number | null) {
		selectedTtsId = modelId;
		selectedVoice = null;
		voices = [];
		if (modelId) {
			try {
				voices = await getVoices(modelId);
				const def = voices.find((v) => v.is_default);
				if (def) selectedVoice = def.voice_code;
			} catch {
				// ignore
			}
		}
	}

	async function saveAudioPrefs() {
		saving = true;
		error = null;
		successMsg = null;
		try {
			// Keep existing native language if updating other prefs
			prefs = await updatePreferences({
				stt_model_id: selectedSttId,
				tts_model_id: selectedTtsId,
				voice: selectedVoice,
				native_language: prefs?.native_language || 'portuguese'
			});
			successMsg = 'Preferências salvas.';
			setTimeout(() => (successMsg = null), 3000);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save';
		} finally {
			saving = false;
		}
	}

	async function downloadAudioModel(type: 'stt' | 'tts', voiceCode?: string) {
		try {
			await downloadModel({ type, voice_code: voiceCode });
			// The $effect will pick up the processing status automatically on the next poll
			// But we manually trigger a fetch here so the UI updates instantly
			models = await getModels();
			if (selectedTtsId) {
				voices = await getVoices(selectedTtsId);
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to download model';
		}
	}

	function modelLabel(model: AIModel): string {
		return model.external_id.startsWith('local:')
			? `${model.name} (local)`
			: model.name;
	}

	const ttsVoicesForSelected = $derived(
		selectedTtsId ? voices : []
	);
</script>

{#if loading}
	<div class="loading-state">
		<span class="spinner" aria-hidden="true"></span>
		<p>Carregando preferências…</p>
	</div>
{:else}
	{#if error}
		<div class="error-bar" role="alert">
			<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
				<circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.2"/>
				<path d="M7 4v3.5M7 9.5v.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
			</svg>
			{error}
		</div>
	{/if}

	{#if successMsg}
		<div class="success-bar" role="status">
			<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
				<circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.2"/>
				<path d="M4.5 7l2 2 3-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
			</svg>
			{successMsg}
		</div>
	{/if}

	<section class="section">
		<header class="section-header">
			<p class="section-eyebrow">Preferências</p>
			<h2 class="section-title">Modelos de Áudio</h2>
			<p class="section-desc">
				Define qual modelo será usado para reconhecimento de fala (STT) e síntese de voz (TTS)
				em conversas por áudio.
			</p>
		</header>

		<div class="cards">
			<div class="pref-card">
				<div class="card-header">
					<span class="card-label">Reconhecimento de fala</span>
					<span class="card-sublabel">Speech-to-Text (STT)</span>
				</div>

				<label class="field">
					<span class="field-label">Selecionar modelo STT</span>
					<select
						class="input"
						value={selectedSttId ?? ''}
						onchange={(e) => {
							const v = (e.target as HTMLSelectElement).value;
							selectedSttId = v ? Number(v) : null;
						}}
					>
						<option value="">Nenhum (padrão automático)</option>
						{#each models.stt as model (model.id)}
							<option value={model.id}>{modelLabel(model)}</option>
						{/each}
					</select>
				</label>
				{#if models.stt.find(m => m.id === selectedSttId)?.external_id.startsWith('local:')}
					{@const selectedStt = models.stt.find(m => m.id === selectedSttId)}
					{#if selectedStt?.download_status !== 'downloaded' && selectedStt?.download_status !== 'completed'}
						<div class="download-action">
							<span class="status-badge status-{selectedStt?.download_status}">
								{#if selectedStt?.download_status === 'processing'}
									<span class="spinner spinner--sm spinner--dark" aria-hidden="true"></span>
									Baixando...
								{:else}
									Não baixado
								{/if}
							</span>
							{#if selectedStt?.download_status !== 'processing'}
								<button 
									type="button" 
									class="btn btn--sm" 
									onclick={() => downloadAudioModel('stt')}
								>
									Baixar Modelo
								</button>
							{/if}
						</div>
					{/if}
				{/if}
			</div>

			<div class="pref-card">
				<div class="card-header">
					<span class="card-label">Síntese de voz</span>
					<span class="card-sublabel">Text-to-Speech (TTS)</span>
				</div>

				<label class="field">
					<span class="field-label">Selecionar modelo TTS</span>
					<select
						class="input"
						value={selectedTtsId ?? ''}
						onchange={(e) => {
							const v = (e.target as HTMLSelectElement).value;
							onTtsModelChange(v ? Number(v) : null);
						}}
					>
						<option value="">Nenhum (padrão automático)</option>
						{#each models.tts as model (model.id)}
							<option value={model.id}>{modelLabel(model)}</option>
						{/each}
					</select>
				</label>

				{#if ttsVoicesForSelected.length > 0}
					<label class="field">
						<span class="field-label">Voz</span>
						<div class="voice-grid">
							{#each ttsVoicesForSelected as voice (voice.id)}
								<label
									class="voice-option"
									class:selected={selectedVoice === voice.voice_code}
								>
									<input
										type="radio"
										name="voice"
										value={voice.voice_code}
										checked={selectedVoice === voice.voice_code}
										onchange={() => (selectedVoice = voice.voice_code)}
										class="visually-hidden"
									/>
									<span class="voice-name">{voice.display_name}</span>
									<span class="voice-lang">{voice.language}</span>
									{#if voice.is_default}
										<span class="voice-default">padrão</span>
									{/if}
									{#if voice.download_status === 'downloaded'}
										<!-- no indicator if fully downloaded -->
									{:else if voice.download_status === 'processing'}
										<span class="voice-status processing">
											<span class="spinner spinner--sm spinner--dark" aria-hidden="true"></span>
										</span>
									{:else}
										<button 
											type="button" 
											class="voice-download-btn"
											onclick={(e) => {
												e.preventDefault();
												e.stopPropagation();
												downloadAudioModel('tts', voice.voice_code);
											}}
											title="Baixar voz local"
										>
											↓
										</button>
									{/if}
								</label>
							{/each}
						</div>
					</label>
				{/if}
			</div>
		</div>

		<div class="section-footer">
			<button class="btn" onclick={saveAudioPrefs} disabled={saving}>
				{#if saving}
					<span class="spinner spinner--sm" aria-hidden="true"></span>
				{/if}
				Salvar preferências de áudio
			</button>
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

	.section-footer {
		display: flex;
		justify-content: flex-end;
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

	.voice-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: var(--space-2);
	}

	.voice-option {
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: var(--space-3) var(--space-3);
		background: var(--color-bg-inset);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition:
			border-color var(--duration-fast) var(--ease-standard),
			background var(--duration-fast) var(--ease-standard);
	}

	.voice-option:hover {
		border-color: var(--color-border-strong);
	}

	.voice-option.selected {
		border-color: var(--color-accent);
		background: rgba(200, 155, 60, 0.05);
	}

	.voice-name {
		font: 600 0.875rem var(--font-body);
		color: var(--color-text-primary);
	}

	.voice-lang {
		font: var(--text-caption);
		color: var(--color-text-muted);
		text-transform: capitalize;
	}

	.voice-default {
		font: 500 0.625rem var(--font-mono);
		color: var(--color-accent);
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	.voice-download {
		font: 500 0.75rem var(--font-mono);
		color: var(--color-text-muted);
		opacity: 0.6;
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

	.spinner--sm {
		width: 12px;
		height: 12px;
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

	.download-action {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-top: var(--space-3);
		padding-top: var(--space-3);
		border-top: 1px dashed var(--color-border);
	}

	.status-badge {
		font: var(--text-caption);
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: 2px 8px;
		border-radius: 12px;
		background: var(--color-surface-raised);
		color: var(--color-text-muted);
	}

	.status-badge.status-processing {
		background: rgba(200, 155, 60, 0.1);
		color: var(--color-accent);
	}

	.btn--sm {
		padding: var(--space-1) var(--space-3);
		font-size: 0.75rem;
		background: var(--color-surface-raised);
		color: var(--color-text-primary);
		border: 1px solid var(--color-border-strong);
	}
	.btn--sm:hover {
		background: var(--color-accent);
		border-color: var(--color-accent);
		color: var(--color-text-on-accent);
	}

	.voice-status {
		display: flex;
		align-items: center;
		margin-left: auto;
	}

	.voice-download-btn {
		margin-left: auto;
		background: none;
		border: none;
		padding: var(--space-1) var(--space-2);
		cursor: pointer;
		color: var(--color-text-muted);
		border-radius: var(--radius-sm);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.voice-download-btn:hover {
		background: var(--color-surface-raised);
		color: var(--color-accent);
	}

	.spinner--dark {
		border-color: rgba(0, 0, 0, 0.2);
		border-top-color: currentColor;
	}
</style>
