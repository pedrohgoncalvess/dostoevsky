<script lang="ts">
	interface Props {
		active?: boolean;
		variant?: 'user' | 'ai';
		bars?: number;
	}

	let { active = false, variant = 'ai', bars = 8 }: Props = $props();

	function heights(index: number): string {
		const base = [6, 14, 9, 18, 7, 12, 5, 16];
		return `${base[index % base.length]}px`;
	}
</script>

<div class="wave" class:active class:user={variant === 'user'} class:ai={variant === 'ai'}>
	{#each Array.from({ length: bars }, (_, i) => i) as bar (bar)}
		<span style="height: {heights(bar)}"></span>
	{/each}
</div>

<style>
	.wave {
		display: flex;
		align-items: flex-end;
		gap: 2px;
		height: 20px;
	}

	.wave span {
		width: 2px;
		background: var(--color-border-strong);
		border-radius: 1px;
		transition: height var(--duration-fast) var(--ease-standard);
	}

	.wave.user span {
		background: var(--color-voice-user);
	}

	.wave.ai span {
		background: var(--color-voice-ai);
	}

	.wave.active span {
		animation: pulse var(--duration-waveform) ease-in-out infinite;
	}

	.wave.active span:nth-child(2) {
		animation-delay: 0.1s;
	}
	.wave.active span:nth-child(3) {
		animation-delay: 0.2s;
	}
	.wave.active span:nth-child(4) {
		animation-delay: 0.3s;
	}
	.wave.active span:nth-child(5) {
		animation-delay: 0.15s;
	}
	.wave.active span:nth-child(6) {
		animation-delay: 0.25s;
	}
	.wave.active span:nth-child(7) {
		animation-delay: 0.05s;
	}
	.wave.active span:nth-child(8) {
		animation-delay: 0.35s;
	}

	@keyframes pulse {
		0%,
		100% {
			transform: scaleY(1);
		}
		50% {
			transform: scaleY(0.4);
		}
	}
</style>
