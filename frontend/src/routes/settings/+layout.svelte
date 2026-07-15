<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { isAuthenticated } from '$lib/auth';
	import { goto } from '$app/navigation';
	import { listInteractions } from '$lib/api';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import type { Interaction } from '$lib/types';

	let { children } = $props();
	let interactions = $state<Interaction[]>([]);

	onMount(async () => {
		if (!browser) return;
		if (!isAuthenticated()) {
			await goto('/');
			return;
		}
		try {
			interactions = await listInteractions(20);
		} catch (e) {
			// ignore
		}
	});
</script>

<div class="settings-layout">
	<Sidebar 
		{interactions} 
		onOpenNewConversation={() => goto('/dashboard?action=new_conversation')}
	/>
	<main class="settings-main">
		{@render children()}
	</main>
</div>

<style>
	.settings-layout {
		display: flex;
		height: 100vh;
		background: var(--color-bg-base);
	}

	.settings-main {
		flex: 1;
		padding: var(--space-8) var(--space-8);
		max-width: 900px;
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		overflow-y: auto;
	}
</style>
