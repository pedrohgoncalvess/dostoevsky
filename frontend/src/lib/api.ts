import { getAccessToken, getRefreshToken, saveTokens, logout } from './auth';
import type { Interaction, Message, Profile, StudyPlan, TokenResponse, User, Media } from './types';

const API_BASE_URL = '/api';
const PUBLIC_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

function getHeaders(): Record<string, string> {
	const token = getAccessToken();
	const headers: Record<string, string> = {
		'Content-Type': 'application/json'
	};
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}
	return headers;
}

async function handleResponse<T>(response: Response): Promise<T> {
	if (!response.ok) {
		let detail = `Request failed with status ${response.status}`;
		try {
			const body = await response.json();
			detail = body.detail || detail;
		} catch {
			// ignore
		}
		throw new Error(detail);
	}
	return response.json() as Promise<T>;
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshTokenApi(): Promise<boolean> {
	const refresh_token = getRefreshToken();
	if (!refresh_token) return false;

	try {
		const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ refresh_token })
		});

		if (response.ok) {
			const tokens = await response.json() as TokenResponse;
			saveTokens(tokens);
			return true;
		}
	} catch (err) {
		// ignore
	}
	
	return false;
}

export async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
	let response = await fetch(url, {
		...options,
		headers: { ...getHeaders(), ...options.headers }
	});

	if (response.status === 401) {
		if (!refreshPromise) {
			refreshPromise = refreshTokenApi().finally(() => {
				refreshPromise = null;
			});
		}

		const success = await refreshPromise;
		
		if (success) {
			response = await fetch(url, {
				...options,
				headers: { ...getHeaders(), ...options.headers }
			});
		} else {
			logout();
		}
	}

	return response;
}

function mapPublicId<T extends { public_id: string }>(
	item: T
): Omit<T, 'public_id'> & { id: string } {
	const { public_id, ...rest } = item;
	return { ...rest, id: public_id };
}

export async function login(email: string, password: string): Promise<TokenResponse> {
	const response = await fetch(`${API_BASE_URL}/auth`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email, password })
	});
	return handleResponse<TokenResponse>(response);
}

export async function getMe(): Promise<User> {
	const response = await apiFetch(`${API_BASE_URL}/users/me`);
	return handleResponse<User>(response);
}

export async function listProfiles(): Promise<Profile[]> {
	const response = await apiFetch(`${API_BASE_URL}/profiles`);
	const data = await handleResponse<Array<{ public_id: string } & Omit<Profile, 'id'>>>(response);
	return data.map(mapPublicId);
}

export async function listInteractions(limit = 20): Promise<Interaction[]> {
	const response = await apiFetch(`${API_BASE_URL}/conversation/interactions?limit=${limit}`);
	const data =
		await handleResponse<Array<{ public_id: string } & Omit<Interaction, 'id'>>>(response);
	return data.map(mapPublicId);
}

export async function createInteraction(
	profileId: string,
	studyPlanId: string,
	name?: string,
	needTip?: boolean
): Promise<Interaction> {
	const response = await apiFetch(`${API_BASE_URL}/conversation/interactions`, {
		method: 'POST',
		body: JSON.stringify({
			profile_public_id: profileId,
			study_plan_public_id: studyPlanId,
			name,
			need_tip: needTip
		})
	});
	const data = await handleResponse<{ public_id: string } & Omit<Interaction, 'id'>>(response);
	return mapPublicId(data);
}

export async function updateInteraction(
	interactionId: string,
	updates: { name?: string; need_tip?: boolean; media_ids?: string[] }
): Promise<void> {
	const response = await apiFetch(`${API_BASE_URL}/conversation/interactions/${interactionId}`, {
		method: 'PATCH',
		body: JSON.stringify(updates)
	});
	await handleResponse(response);
}

export async function deleteInteraction(interactionId: string): Promise<void> {
	const response = await apiFetch(`${API_BASE_URL}/conversation/interactions/${interactionId}`, {
		method: 'DELETE'
	});
	await handleResponse(response);
}

export async function listMessages(interactionId: string): Promise<Message[]> {
	const response = await apiFetch(
		`${API_BASE_URL}/conversation/interactions/${interactionId}/messages`
	);
	const data = await handleResponse<Array<{ public_id: string } & Omit<Message, 'id'>>>(response);
	return data.map(mapPublicId);
}

export async function sendTextMessage(interactionId: string, text: string): Promise<Message> {
	const response = await apiFetch(
		`${API_BASE_URL}/conversation/interactions/${interactionId}/messages`,
		{
			method: 'POST',
			body: JSON.stringify({ text })
		}
	);
	const data = await handleResponse<{ public_id: string } & Omit<Message, 'id'>>(response);
	return mapPublicId(data);
}

export function getConversationWebSocketUrl(interactionId: string): string {
	const token = getAccessToken();
	const wsProtocol = PUBLIC_API_BASE_URL.startsWith('https') ? 'wss' : 'ws';
	const base = PUBLIC_API_BASE_URL.replace(/^https?:\/\//, '');
	return `${wsProtocol}://${base}/conversation/ws?token=${token}&interaction_public_id=${interactionId}`;
}

export async function listStudyPlans(): Promise<StudyPlan[]> {
	const response = await apiFetch(`${API_BASE_URL}/study-plans`);
	const data = await handleResponse<Array<{ public_id: string } & Omit<StudyPlan, 'id'>>>(response);
	return data.map(mapPublicId);
}

export async function createStudyPlan(
	studyLanguage: string,
	selfDeclaredLevel: string,
	goal?: string
): Promise<{ plan: StudyPlan; feedback: string | null }> {
	const response = await apiFetch(`${API_BASE_URL}/study-plans`, {
		method: 'POST',
		body: JSON.stringify({
			study_language: studyLanguage,
			self_declared_level: selfDeclaredLevel,
			goal
		})
	});
	const data = await handleResponse<{
		plan: { public_id: string } & Omit<StudyPlan, 'id'>;
		feedback: string | null;
	}>(response);
	return { plan: mapPublicId(data.plan), feedback: data.feedback };
}

export async function updateStudyPlan(
	studyPlanId: string,
	updates: Partial<Pick<StudyPlan, 'study_language' | 'self_declared_level' | 'goal'>>
): Promise<StudyPlan> {
	const response = await apiFetch(`${API_BASE_URL}/study-plans/${studyPlanId}`, {
		method: 'PATCH',
		body: JSON.stringify(updates)
	});
	const data = await handleResponse<{ public_id: string } & Omit<StudyPlan, 'id'>>(response);
	return mapPublicId(data);
}

export async function deleteStudyPlan(studyPlanId: string): Promise<void> {
	const response = await apiFetch(`${API_BASE_URL}/study-plans/${studyPlanId}`, {
		method: 'DELETE'
	});
	await handleResponse<{ deleted: boolean }>(response);
}

export async function listMedias(): Promise<Media[]> {
	const response = await apiFetch(`${API_BASE_URL}/media/medias`);
	const data = await handleResponse<Array<{ public_id: string } & Omit<Media, 'id'>>>(response);
	return data.map(mapPublicId);
}

export async function uploadMedia(file: File, name?: string): Promise<Media> {
	const formData = new FormData();
	formData.append('file', file);
	if (name) {
		formData.append('name', name);
	}

	const token = getAccessToken();
	const headers: Record<string, string> = {};
	if (token) headers['Authorization'] = `Bearer ${token}`;

	const response = await fetch(`${API_BASE_URL}/media`, {
		method: 'POST',
		headers,
		body: formData
	});
	const data = await handleResponse<{ public_id: string } & Omit<Media, 'id'>>(response);
	return mapPublicId(data);
}

export async function updateMedia(id: string, name?: string, description?: string): Promise<Media> {
	const payload: Record<string, string> = {};
	if (name !== undefined) payload.name = name;
	if (description !== undefined) payload.description = description;

	const response = await apiFetch(`${API_BASE_URL}/media/${id}`, {
		method: 'PATCH',
		body: JSON.stringify(payload)
	});
	const data = await handleResponse<{ public_id: string } & Omit<Media, 'id'>>(response);
	return mapPublicId(data);
}

export async function deleteMedia(id: string): Promise<void> {
	await apiFetch(`${API_BASE_URL}/media/${id}`, {
		method: 'DELETE'
	});
}
