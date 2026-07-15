<script lang="ts">
	import type { ChatStatus } from '$lib/types';

	interface Props {
		status: ChatStatus;
	}

	let { status }: Props = $props();

	const config: Record<ChatStatus, { label: string; cls: string }> = {
		idle: { label: 'Pronto', cls: 'idle' },
		connecting: { label: 'Conectando', cls: 'active' },
		listening: { label: 'Escutando', cls: 'active' },
		recording: { label: 'Gravando', cls: 'recording' },
		processing: { label: 'Processando', cls: 'processing' },
		responding: { label: 'Respondendo', cls: 'processing' },
		error: { label: 'Erro', cls: 'error' },
		closed: { label: 'Desconectado', cls: 'muted' }
	};

	const current = $derived(config[status] ?? config.idle);
</script>

<div class="status status--{current.cls}" role="status" aria-live="polite">
	<span class="dot" aria-hidden="true"></span>
	<span class="label">{current.label}</span>
</div>

<style>
	.status {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		font: 500 0.6875rem var(--font-body);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--color-text-muted);
		transition: color var(--duration-base) var(--ease-standard);
	}

	.dot {
		width: 6px;
		height: 6px;
		border-radius: var(--radius-pill);
		background: var(--color-border-strong);
		flex-shrink: 0;
		transition: background var(--duration-base) var(--ease-standard);
	}

	/* idle — verdigris dim */
	.status--idle .dot {
		background: var(--color-success);
		opacity: 0.7;
	}
	.status--idle {
		color: var(--color-text-muted);
	}

	/* active (connecting, listening) — gilt pulse */
	.status--active .dot {
		background: var(--color-warning);
		animation: pulse-dot 1.4s ease-in-out infinite;
	}
	.status--active {
		color: var(--color-warning);
	}

	/* recording — oxblood pulse */
	.status--recording .dot {
		background: var(--color-voice-user);
		animation: pulse-dot 0.9s ease-in-out infinite;
	}
	.status--recording {
		color: var(--color-voice-user-soft);
	}

	/* processing / responding — verdigris pulse */
	.status--processing .dot {
		background: var(--color-voice-ai);
		animation: pulse-dot 1.1s ease-in-out infinite;
	}
	.status--processing {
		color: var(--color-voice-ai-soft);
	}

	/* error */
	.status--error .dot {
		background: var(--color-danger);
	}
	.status--error {
		color: var(--raw-oxblood-400);
	}

	/* muted / closed */
	.status--muted .dot {
		background: var(--color-border-strong);
		opacity: 0.5;
	}

	@keyframes pulse-dot {
		0%, 100% { opacity: 1; transform: scale(1); }
		50% { opacity: 0.4; transform: scale(0.85); }
	}
</style>
