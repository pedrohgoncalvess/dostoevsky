import { browser } from '$app/environment';
import { writable, derived, get } from 'svelte/store';
import { translations, type Locale } from './translations';

export type { Locale };

const STORAGE_KEY = 'dostoi_evsk_locale';

function detectLocale(): Locale {
	if (browser) {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (stored === 'en' || stored === 'pt') {
			return stored;
		}

		const navigatorLang = navigator.language.toLowerCase();
		if (navigatorLang.startsWith('pt')) {
			return 'pt';
		}
	}
	return 'en';
}

function createLocaleStore() {
	const store = writable<Locale>(detectLocale());

	return {
		subscribe: store.subscribe,
		set(locale: Locale) {
			if (browser) {
				localStorage.setItem(STORAGE_KEY, locale);
			}
			store.set(locale);
		},
		init() {
			store.set(detectLocale());
		}
	};
}

export const locale = createLocaleStore();

export const t = derived(locale, ($locale) => {
	return function (
		key: keyof typeof translations.en | `${keyof typeof translations.en}.${string}`
	): string {
		const parts = key.split('.');
		let value: unknown = translations[$locale];

		for (const part of parts) {
			if (value && typeof value === 'object' && part in value) {
				value = (value as Record<string, unknown>)[part];
			} else {
				value = undefined;
				break;
			}
		}

		if (typeof value === 'string') {
			return value;
		}

		// Fallback to English
		value = translations.en;
		for (const part of parts) {
			if (value && typeof value === 'object' && part in value) {
				value = (value as Record<string, unknown>)[part];
			} else {
				return key;
			}
		}

		return typeof value === 'string' ? value : key;
	};
});

export function formatDate(date: string | Date, options?: Intl.DateTimeFormatOptions): string {
	const d = typeof date === 'string' ? new Date(date) : date;
	const currentLocale = get(locale);
	return d.toLocaleDateString(currentLocale === 'pt' ? 'pt-BR' : 'en-US', {
		day: '2-digit',
		month: 'short',
		year: 'numeric',
		...options
	});
}
