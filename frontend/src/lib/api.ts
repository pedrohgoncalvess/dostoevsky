import { getAccessToken } from './auth';
import type { Interaction, Message, Profile, StudyPlan, TokenResponse, User } from './types';

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
	const response = await fetch(`${API_BASE_URL}/users/me`, {
		headers: getHeaders()
	});
	return handleResponse<User>(response);
}

export async function listProfiles(): Promise<Profile[]> {
	const response = await fetch(`${API_BASE_URL}/profiles`, {
		headers: getHeaders()
	});
	const data = await handleResponse<Array<{ public_id: string } & Omit<Profile, 'id'>>>(response);
	return data.map(mapPublicId);
}

export async function listInteractions(limit = 20): Promise<Interaction[]> {
	const response = await fetch(`${API_BASE_URL}/conversation/interactions?limit=${limit}`, {
		headers: getHeaders()
	});
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
	const response = await fetch(`${API_BASE_URL}/conversation/interactions`, {
		method: 'POST',
		headers: getHeaders(),
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

export async function listMessages(interactionId: string): Promise<Message[]> {
	const response = await fetch(
		`${API_BASE_URL}/conversation/interactions/${interactionId}/messages`,
		{
			headers: getHeaders()
		}
	);
	const data = await handleResponse<Array<{ public_id: string } & Omit<Message, 'id'>>>(response);
	return data.map(mapPublicId);
}

export async function sendTextMessage(interactionId: string, text: string): Promise<Message> {
	const response = await fetch(
		`${API_BASE_URL}/conversation/interactions/${interactionId}/messages`,
		{
			method: 'POST',
			headers: getHeaders(),
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
	const response = await fetch(`${API_BASE_URL}/study-plans`, {
		headers: getHeaders()
	});
	const data = await handleResponse<Array<{ public_id: string } & Omit<StudyPlan, 'id'>>>(response);
	return data.map(mapPublicId);
}

export async function createStudyPlan(
	studyLanguage: string,
	selfDeclaredLevel: string,
	goal?: string
): Promise<StudyPlan> {
	const response = await fetch(`${API_BASE_URL}/study-plans`, {
		method: 'POST',
		headers: getHeaders(),
		body: JSON.stringify({
			study_language: studyLanguage,
			self_declared_level: selfDeclaredLevel,
			goal
		})
	});
	const data = await handleResponse<{ public_id: string } & Omit<StudyPlan, 'id'>>(response);
	return mapPublicId(data);
}

export async function updateStudyPlan(
	studyPlanId: string,
	updates: Partial<Pick<StudyPlan, 'study_language' | 'self_declared_level' | 'goal'>>
): Promise<StudyPlan> {
	const response = await fetch(`${API_BASE_URL}/study-plans/${studyPlanId}`, {
		method: 'PATCH',
		headers: getHeaders(),
		body: JSON.stringify(updates)
	});
	const data = await handleResponse<{ public_id: string } & Omit<StudyPlan, 'id'>>(response);
	return mapPublicId(data);
}

export async function deleteStudyPlan(studyPlanId: string): Promise<void> {
	const response = await fetch(`${API_BASE_URL}/study-plans/${studyPlanId}`, {
		method: 'DELETE',
		headers: getHeaders()
	});
	await handleResponse<{ deleted: boolean }>(response);
}
