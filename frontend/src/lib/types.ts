export interface TokenResponse {
	access_token: { token: string; expires: string };
	refresh_token: { token: string; expires: string };
	token_type: string;
}

export interface User {
	name: string;
	email: string;
	native_language: Language;
}

export interface Profile {
	id: string;
	name: string;
	description: string;
}

export interface Interaction {
	id: string;
	name: string | null;
	profile_id: string;
	profile_name?: string;
	need_tip: boolean;
	inserted_at: string;
}

export interface Message {
	id: string;
	sent_by: 'user' | 'assistant';
	content: string;
	tip?: string;
	correction?: string;
	inserted_at: string;
}

export interface MediaDescription {
	written_description?: string;
	extracted_text?: string;
	[key: string]: any;
}

export interface Media {
	id: string; // This corresponds to public_id in backend
	name: string;
	description: MediaDescription | null;
	format?: string;
	inserted_at?: string;
}

export type Language = 'portuguese' | 'english' | 'french' | 'spanish' | 'russian' | 'mandarim';

export type KnowledgeLevel = 'a1' | 'a2' | 'b1' | 'b2' | 'c1' | 'c2';

export interface StudyPlan {
	id: string;
	study_language: Language;
	self_declared_level: KnowledgeLevel;
	goal: string | null;
	setup_completed: boolean;
	inserted_at: string;
	deleted_at: string | null;
}

export type ChatStatus =
	| 'idle'
	| 'connecting'
	| 'listening'
	| 'recording'
	| 'processing'
	| 'responding'
	| 'error'
	| 'closed';
