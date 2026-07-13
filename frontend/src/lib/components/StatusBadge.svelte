<script lang="ts">
	import type { ChatStatus } from '$lib/types';

	interface Props {
		status: ChatStatus;
	}

	let { status }: Props = $props();

	const labels: Record<ChatStatus, string> = {
		idle: 'Pronto',
		connecting: 'Conectando',
		listening: 'Escutando',
		recording: 'Gravando',
		processing: 'Processando',
		responding: 'Respondendo',
		error: 'Erro',
		closed: 'Desconectado'
	};

	const statusClass: Record<ChatStatus, string> = {
		idle: 'status--idle',
		connecting: 'status--connecting',
		listening: 'status--listening',
		recording: 'status--recording',
		processing: 'status--processing',
		responding: 'status--responding',
		error: 'status--error',
		closed: 'status--closed'
	};
</script>

<div class="status {statusClass[status]}">
	<span class="dot"></span>
	<span class="label">{labels[status]}</span>
</div>

<style>
	.status {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		font: var(--text-caption);
		color: var(--color-text-secondary);
	}

	.dot {
		width: 8px;
		height: 8px;
		border-radius: var(--radius-pill);
		background: var(--color-text-muted);
	}

	.status--idle .dot {
		background: var(--color-success);
	}

	.status--connecting .dot,
	.status--listening .dot,
	.status--recording .dot {
		background: var(--color-warning);
		animation: blink 1.2s ease-in-out infinite;
	}

	.status--processing .dot,
	.status--responding .dot {
		background: var(--color-voice-ai);
		animation: blink 1.2s ease-in-out infinite;
	}

	.status--error .dot {
		background: var(--color-danger);
	}

	.status--closed .dot {
		background: var(--color-text-muted);
	}

	@keyframes blink {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.4;
		}
	}
</style>
