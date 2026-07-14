<script lang="ts">
	import type { AudioStatus } from '$lib/audio/conversation';

	interface Props {
		status: AudioStatus;
		volume?: number;
		bars?: number;
		label?: string;
	}

	let { status, volume = 0, bars = 32, label }: Props = $props();

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

	let config = $derived(statusConfig[status] ?? statusConfig.idle);

	function barHeight(index: number): number {
		const center = bars / 2;
		const distance = Math.abs(index - center) / center;
		const base = 0.25 + 0.75 * (1 - distance * distance);
		const motion = config.active ? 0.4 + 0.6 * volume : 0.1;
		const noise = Math.sin(index * 1.3 + Date.now() / 200) * 0.15;
		return Math.max(0.08, Math.min(1, base * motion + noise));
	}
</script>

<div class="voice-visualizer" style="--voice-color: {config.colorVar}">
	<div class="rings" aria-hidden="true">
		{#each Array.from({ length: bars }, (_, i) => i) as bar (bar)}
			{@const height = barHeight(bar)}
			<span class="bar" style="--bar-height: {height}"></span>
		{/each}
	</div>
	{#if label}
		<p class="status-label">{label}</p>
	{/if}
</div>

<style>
	.voice-visualizer {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-5);
		min-height: 280px;
		padding: var(--space-6);
		border-radius: var(--radius-lg);
		background: var(--color-surface);
		box-shadow: var(--elevation-2);
	}

	.rings {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: clamp(2px, 0.6vw, 8px);
		width: 100%;
		max-width: 720px;
		height: 180px;
	}

	.bar {
		flex: 1;
		max-width: 14px;
		height: calc(var(--bar-height, 0.2) * 100%);
		background: var(--voice-color);
		border-radius: var(--radius-pill);
		opacity: 0.85;
		transition:
			height 80ms var(--ease-standard),
			background 200ms var(--ease-standard),
			opacity 200ms var(--ease-standard);
	}

	.status-label {
		font: var(--text-heading);
		color: var(--voice-color);
		letter-spacing: var(--letter-caption);
		text-transform: uppercase;
		margin: 0;
	}
</style>
