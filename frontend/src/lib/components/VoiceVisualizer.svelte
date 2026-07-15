<script lang="ts">
	import type { AudioStatus } from '$lib/audio/conversation';

	interface Props {
		status: AudioStatus;
		volume?: number;
		bars?: number;
		label?: string;
	}

	let { status, volume = 0, bars = 40, label }: Props = $props();

	const statusConfig: Record<AudioStatus, { colorVar: string; active: boolean }> = {
		idle: { colorVar: 'var(--color-border-strong)', active: false },
		connecting: { colorVar: 'var(--color-accent)', active: true },
		connected: { colorVar: 'var(--color-border-strong)', active: false },
		recording: { colorVar: 'var(--color-voice-user)', active: true },
		processing: { colorVar: 'var(--color-accent)', active: true },
		playing: { colorVar: 'var(--color-voice-ai)', active: true },
		error: { colorVar: 'var(--color-danger)', active: false },
		closed: { colorVar: 'var(--color-border-strong)', active: false }
	};

	const statusLabel: Record<AudioStatus, string> = {
		idle: 'Em espera',
		connecting: 'Conectando',
		connected: 'Conectado',
		recording: 'Gravando',
		processing: 'Processando',
		playing: 'Respondendo',
		error: 'Erro',
		closed: 'Desconectado'
	};

	let config = $derived(statusConfig[status] ?? statusConfig.idle);
	let displayLabel = $derived(label ?? statusLabel[status]);

	function barHeight(index: number): number {
		const center = bars / 2;
		const distance = Math.abs(index - center) / center;
		const envelope = 1 - distance * distance * 0.7;
		const motion = config.active ? 0.35 + 0.65 * volume : 0.08;
		const noise = Math.sin(index * 1.7 + Date.now() / 180) * 0.12;
		return Math.max(0.04, Math.min(1, envelope * motion + noise));
	}
</script>

<div class="voice-visualizer" style="--voice-color: {config.colorVar}">
	<div class="bars-container" aria-hidden="true">
		{#each Array.from({ length: bars }, (_, i) => i) as bar (bar)}
			{@const height = barHeight(bar)}
			<span class="bar" class:active={config.active} style="--bar-height: {height}"></span>
		{/each}
	</div>

	<div class="meta">
		{#if config.active}
			<span class="pulse-ring" aria-hidden="true"></span>
		{/if}
		<p class="status-label" class:active={config.active}>{displayLabel}</p>
	</div>
</div>

<style>
	.voice-visualizer {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-7);
		padding: var(--space-7) var(--space-6);
	}

	.bars-container {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: clamp(2px, 0.4vw, 5px);
		width: 100%;
		max-width: 640px;
		height: 120px;
	}

	.bar {
		flex: 1;
		max-width: 8px;
		height: calc(var(--bar-height, 0.08) * 100%);
		background: var(--voice-color);
		border-radius: var(--radius-pill);
		opacity: 0.6;
		transition:
			height 60ms var(--ease-standard),
			background var(--duration-base) var(--ease-standard),
			opacity var(--duration-base) var(--ease-standard);
	}

	.bar.active {
		opacity: 0.9;
	}

	.meta {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-3);
		position: relative;
	}

	.pulse-ring {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 48px;
		height: 48px;
		border-radius: var(--radius-pill);
		border: 1px solid var(--voice-color);
		opacity: 0.25;
		animation: pulse-ring 2s ease-out infinite;
	}

	.status-label {
		font: 400 italic 1.0625rem / 1 var(--font-display);
		color: var(--voice-color);
		letter-spacing: 0.01em;
		margin: 0;
		transition: color var(--duration-base) var(--ease-standard);
		opacity: 0.9;
	}

	.status-label.active {
		opacity: 1;
	}

	@keyframes pulse-ring {
		0% {
			transform: translate(-50%, -50%) scale(1);
			opacity: 0.3;
		}
		100% {
			transform: translate(-50%, -50%) scale(2.5);
			opacity: 0;
		}
	}
</style>
