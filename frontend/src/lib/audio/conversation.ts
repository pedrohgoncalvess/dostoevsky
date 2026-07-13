import { getConversationWebSocketUrl } from '$lib/api';
import { AudioPlayer } from './player';
import { AudioRecorder } from './recorder';

export type AudioStatus =
	'idle' | 'connecting' | 'connected' | 'recording' | 'processing' | 'playing' | 'error' | 'closed';

type AudioEvent =
	| { type: 'ready' }
	| { type: 'error'; detail: string }
	| { type: 'user_audio_saved' }
	| { type: 'noise_detected' }
	| { type: 'user_transcription'; text: string }
	| { type: 'no_speech_detected' }
	| { type: 'assistant_message'; text: string }
	| { type: 'assistant_audio_end' };

interface AudioConversationCallbacks {
	onStatusChange?: (status: AudioStatus) => void;
	onUserTranscription?: (text: string) => void;
	onAssistantMessage?: (text: string) => void;
	onError?: (message: string) => void;
}

export class AudioConversation {
	private ws: WebSocket | null = null;
	private recorder = new AudioRecorder();
	private player = new AudioPlayer();
	private status: AudioStatus = 'idle';
	private interactionId: string;
	private callbacks: AudioConversationCallbacks;
	private pendingAudio: Uint8Array[] = [];

	constructor(interactionId: string, callbacks: AudioConversationCallbacks = {}) {
		this.interactionId = interactionId;
		this.callbacks = callbacks;
	}

	get currentStatus(): AudioStatus {
		return this.status;
	}

	async connect(): Promise<void> {
		if (this.ws && this.ws.readyState !== WebSocket.CLOSED) return;
		this.setStatus('connecting');

		const url = `${getConversationWebSocketUrl(this.interactionId)}&audio_format=pcm`;
		this.ws = new WebSocket(url);
		this.ws.binaryType = 'arraybuffer';

		this.ws.onopen = () => {
			this.setStatus('connected');
		};

		this.ws.onmessage = async (event) => {
			if (event.data instanceof ArrayBuffer) {
				this.pendingAudio.push(new Uint8Array(event.data));
				return;
			}
			await this.handleMessage(event.data as string);
		};

		this.ws.onerror = () => {
			this.setStatus('error');
			this.callbacks.onError?.('WebSocket connection failed.');
		};

		this.ws.onclose = () => {
			this.setStatus('closed');
			this.ws = null;
		};

		await this.waitForOpen();
	}

	async startRecording(): Promise<void> {
		if (this.recorder.recording) return;
		if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
			await this.connect();
		}

		this.pendingAudio = [];
		await this.recorder.start((chunk) => {
			this.ws?.send(chunk);
		});
		this.setStatus('recording');
	}

	stopRecording(): void {
		if (!this.recorder.recording) return;
		this.recorder.stop();
		this.setStatus('processing');
		this.ws?.send(JSON.stringify({ type: 'commit', audio_format: 'pcm' }));
	}

	toggleRecording(): void {
		if (this.recorder.recording) {
			this.stopRecording();
		} else {
			void this.startRecording();
		}
	}

	private async handleMessage(raw: string): Promise<void> {
		let event: AudioEvent;
		try {
			event = JSON.parse(raw) as AudioEvent;
		} catch {
			return;
		}

		switch (event.type) {
			case 'ready':
				this.setStatus('connected');
				break;
			case 'user_transcription':
				this.callbacks.onUserTranscription?.(event.text);
				break;
			case 'assistant_message':
				this.callbacks.onAssistantMessage?.(event.text);
				this.setStatus('playing');
				break;
			case 'assistant_audio_end':
				await this.playPendingAudio();
				this.setStatus('connected');
				break;
			case 'noise_detected':
			case 'no_speech_detected':
				this.setStatus('connected');
				break;
			case 'error':
				this.setStatus('error');
				this.callbacks.onError?.('detail' in event ? event.detail : 'Unknown error');
				break;
		}
	}

	private async playPendingAudio(): Promise<void> {
		if (this.pendingAudio.length === 0) return;
		const totalLength = this.pendingAudio.reduce((sum, chunk) => sum + chunk.length, 0);
		const combined = new Uint8Array(totalLength);
		let offset = 0;
		for (const chunk of this.pendingAudio) {
			combined.set(chunk, offset);
			offset += chunk.length;
		}
		this.pendingAudio = [];
		await this.player.play(combined.buffer);
	}

	private waitForOpen(): Promise<void> {
		return new Promise((resolve, reject) => {
			if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
				reject(new Error('WebSocket failed to open'));
				return;
			}
			if (this.ws.readyState === WebSocket.OPEN) {
				resolve();
				return;
			}
			const onOpen = () => {
				this.ws?.removeEventListener('open', onOpen);
				resolve();
			};
			this.ws.addEventListener('open', onOpen);
		});
	}

	private setStatus(status: AudioStatus): void {
		this.status = status;
		this.callbacks.onStatusChange?.(status);
	}

	close(): void {
		this.ws?.close();
		this.recorder.stop();
		this.player.close();
		this.ws = null;
	}
}
