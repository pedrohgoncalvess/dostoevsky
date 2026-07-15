export interface AIModel {
	id: number;
	public_id: string;
	name: string;
	type: string;
	external_id: string;
	for_stt: boolean;
	for_tts: boolean;
	for_text: boolean;
	for_planning: boolean;
	for_embedding: boolean;
	download_status?: 'pending' | 'processing' | 'downloaded' | 'not_downloaded' | 'completed';
}

export interface AIVoice {
	id: number;
	public_id: string;
	model_id: number;
	language: string;
	voice_code: string;
	display_name: string;
	is_default: boolean;
	downloaded: boolean;
	download_status?: 'pending' | 'processing' | 'downloaded' | 'not_downloaded' | 'completed';
}

export interface AIAgent {
	id: number;
	public_id: string;
	name: string;
	description: string | null;
	model: Pick<AIModel, 'id' | 'name' | 'type' | 'external_id'> | null;
}

export interface UserPreferences {
	native_language: string;
	stt_model: AIModel | null;
	tts_model: AIModel | null;
	voice: string | null;
}

export interface ModelsGrouped {
	stt: AIModel[];
	tts: AIModel[];
	text: AIModel[];
}
