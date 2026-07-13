import type { TokenResponse } from './types';

const ACCESS_TOKEN_KEY = 'dostoi_evsk_access_token';
const REFRESH_TOKEN_KEY = 'dostoi_evsk_refresh_token';

export function saveTokens(response: TokenResponse): void {
	if (typeof window === 'undefined') return;
	localStorage.setItem(ACCESS_TOKEN_KEY, response.access_token.token);
	localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh_token.token);
}

export function getAccessToken(): string | null {
	if (typeof window === 'undefined') return null;
	return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
	if (typeof window === 'undefined') return null;
	return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function clearTokens(): void {
	if (typeof window === 'undefined') return;
	localStorage.removeItem(ACCESS_TOKEN_KEY);
	localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
	return !!getAccessToken();
}

export function logout(): void {
	clearTokens();
	if (typeof window !== 'undefined') {
		window.location.href = '/';
	}
}
