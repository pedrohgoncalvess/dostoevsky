<script lang="ts">
	interface Props {
		active?: boolean;
		variant?: 'user' | 'ai';
		bars?: number;
	}

	let { active = false, variant = 'ai', bars = 12 }: Props = $props();

	// Organic height pattern — center bars taller, edges shorter
	const heightPattern = [4, 7, 11, 16, 9, 14, 18, 14, 9, 16, 11, 7];

	function height(index: number): string {
		return `${heightPattern[index % heightPattern.length]}px`;
	}

	// Staggered delays for natural feel
	const delays = [0, 0.12, 0.24, 0.06, 0.32, 0.18, 0.08, 0.28, 0.16, 0.04, 0.22, 0.36];
</script>

<div
	class="wave"
	class:active
	class:user={variant === 'user'}
	class:ai={variant === 'ai'}
	aria-hidden="true"
>
	{#each Array.from({ length: bars }, (_, i) => i) as bar (bar)}
		<span style="height: {height(bar)}; animation-delay: {delays[bar % delays.length]}s"></span>
	{/each}
</div>

<style>
	.wave {
		display: flex;
		align-items: flex-end;
		gap: 2px;
		height: 20px;
		opacity: 0.7;
	}

	.wave span {
		width: 2px;
		background: var(--color-border-strong);
		border-radius: var(--radius-pill);
		transition: height var(--duration-base) var(--ease-standard);
	}

	.wave.user span {
		background: var(--color-voice-user);
	}

	.wave.ai span {
		background: var(--color-voice-ai);
	}

	.wave.active {
		opacity: 1;
	}

	.wave.active span {
		animation: wave-bar var(--duration-waveform) ease-in-out infinite;
	}

	@keyframes wave-bar {
		0%, 100% {
			transform: scaleY(1);
		}
		50% {
			transform: scaleY(0.35);
		}
	}
</style>
