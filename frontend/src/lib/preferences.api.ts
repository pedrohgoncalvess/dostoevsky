import { apiFetch } from './api';
import type { AIAgent, AIModel, AIVoice, ModelsGrouped, UserPreferences } from './preferences.types';

const API_BASE_URL = '/api';

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

export async function getPreferences(): Promise<UserPreferences> {
	const response = await apiFetch(`${API_BASE_URL}/preferences`);
	return handleResponse<UserPreferences>(response);
}

export async function updatePreferences(
	patch: Partial<{
		stt_model_id: number | null;
		tts_model_id: number | null;
		voice: string | null;
		native_language: string;
	}>
): Promise<UserPreferences> {
	const response = await apiFetch(`${API_BASE_URL}/preferences`, {
		method: 'PATCH',
		body: JSON.stringify(patch)
	});
	return handleResponse<UserPreferences>(response);
}

export async function getModels(): Promise<ModelsGrouped> {
	const response = await apiFetch(`${API_BASE_URL}/preferences/models`);
	return handleResponse<ModelsGrouped>(response);
}

export async function getVoices(modelId?: number): Promise<AIVoice[]> {
	const url = modelId
		? `${API_BASE_URL}/preferences/voices?model_id=${modelId}`
		: `${API_BASE_URL}/preferences/voices`;
	const response = await apiFetch(url);
	return handleResponse<AIVoice[]>(response);
}

export async function getAgents(): Promise<AIAgent[]> {
	const response = await apiFetch(`${API_BASE_URL}/preferences/agents`);
	return handleResponse<AIAgent[]>(response);
}

export async function updateAgentModel(agentName: string, modelId: number): Promise<AIAgent> {
	const response = await apiFetch(`${API_BASE_URL}/preferences/agents/${agentName}`, {
		method: 'PATCH',
		body: JSON.stringify({ model_id: modelId })
	});
	return handleResponse<AIAgent>(response);
}

export async function downloadModel(payload: { type: 'stt' | 'tts'; voice_code?: string }): Promise<{ status: string }> {
	const response = await apiFetch(`${API_BASE_URL}/preferences/audio-models/download`, {
		method: 'POST',
		body: JSON.stringify(payload)
	});
	return handleResponse<{ status: string }>(response);
}
