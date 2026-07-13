<script lang="ts">
	import { goto } from '$app/navigation';
	import { login } from '$lib/api';
	import { saveTokens } from '$lib/auth';
	import { t } from '$lib/i18n';

	let email = $state('');
	let password = $state('');
	let loading = $state(false);
	let error = $state<string | null>(null);

	async function handleSubmit(event: Event) {
		event.preventDefault();
		loading = true;
		error = null;

		try {
			const tokens = await login(email, password);
			saveTokens(tokens);
			await goto('/dashboard');
		} catch (err) {
			error = err instanceof Error ? err.message : $t('login.failure');
		} finally {
			loading = false;
		}
	}
</script>

<main class="login">
	<div class="card login-card">
		<div class="wordmark">
			<span class="mark">{$t('common.appName')}</span>
			<span class="rule"></span>
			<span class="cyr">{$t('common.appNameCyrillic')}</span>
		</div>

		<form class="form" onsubmit={handleSubmit}>
			<label class="field">
				<span class="field-label">{$t('login.email')}</span>
				<input
					class="input"
					type="email"
					autocomplete="email"
					placeholder={$t('login.emailPlaceholder')}
					bind:value={email}
					required
				/>
			</label>

			<label class="field">
				<span class="field-label">{$t('login.password')}</span>
				<input
					class="input"
					type="password"
					autocomplete="current-password"
					placeholder={$t('login.passwordPlaceholder')}
					bind:value={password}
					required
				/>
			</label>

			{#if error}
				<p class="error" role="alert">{error}</p>
			{/if}

			<button class="btn btn--submit" type="submit" disabled={loading}>
				{loading ? $t('login.submitting') : $t('login.submit')}
			</button>
		</form>
	</div>
</main>

<style>
	.login {
		min-height: 100vh;
		display: grid;
		place-items: center;
		padding: var(--space-5);
		background: var(--color-bg);
	}

	.login-card {
		width: 100%;
		max-width: 440px;
		padding: var(--space-6) var(--space-5);
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}

	.wordmark {
		display: flex;
		align-items: baseline;
		gap: var(--space-3);
		margin-bottom: var(--space-2);
	}

	.mark {
		font: 700 1.25rem var(--font-display);
		color: var(--color-accent);
		letter-spacing: 0.02em;
	}

	.rule {
		flex: 1;
		height: 1px;
		background: var(--color-border);
	}

	.cyr {
		font: 400 italic 1rem var(--font-display);
		color: var(--color-text-muted);
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

	.btn--submit {
		width: 100%;
		margin-top: var(--space-2);
	}

	.btn--submit:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.error {
		padding: var(--space-3);
		background: rgba(140, 59, 59, 0.15);
		border: 1px solid var(--color-danger);
		border-radius: var(--radius-md);
		color: var(--raw-oxblood-400);
		font: var(--text-body-sm);
	}
</style>
