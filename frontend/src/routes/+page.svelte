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
	<div class="login-inner">
		<div class="wordmark">
			<span class="mark">{$t('common.appName')}</span>
			<span class="rule"></span>
			<span class="cyr">{$t('common.appNameCyrillic')}</span>
		</div>

		<p class="lede">{$t('login.lede')}</p>

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
				{#if loading}
					<span class="spinner" aria-hidden="true"></span>
					{$t('login.submitting')}
				{:else}
					{$t('login.submit')}
				{/if}
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
		background-image:
			radial-gradient(ellipse at 20% 50%, rgba(200, 155, 60, 0.04) 0%, transparent 60%),
			radial-gradient(ellipse at 80% 20%, rgba(79, 122, 108, 0.03) 0%, transparent 50%);
	}

	.login-inner {
		width: 100%;
		max-width: 400px;
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.wordmark {
		display: flex;
		align-items: baseline;
		gap: var(--space-3);
	}

	.mark {
		font: 700 1.5rem / 1 var(--font-display);
		color: var(--color-accent);
		letter-spacing: 0.04em;
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

	.lede {
		font: 400 italic 1rem / 1.6 var(--font-display);
		color: var(--color-text-muted);
		margin: calc(-1 * var(--space-3)) 0 0;
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

	.btn--submit {
		width: 100%;
		margin-top: var(--space-2);
		padding: var(--space-3) var(--space-4);
		font: 500 1rem var(--font-body);
	}

	.btn--submit:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid rgba(16, 21, 26, 0.3);
		border-top-color: var(--color-text-on-accent);
		border-radius: 50%;
		animation: spin 600ms linear infinite;
	}

	.error {
		padding: var(--space-3) var(--space-4);
		background: rgba(140, 59, 59, 0.12);
		border-left: 2px solid var(--color-danger);
		border-radius: var(--radius-md);
		color: var(--raw-oxblood-400);
		font: var(--text-body-sm);
	}
</style>
