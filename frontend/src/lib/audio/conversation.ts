import { getConversationWebSocketUrl } from '$lib/api';
import { AudioPlayer } from './player';
import { AudioRecorder } from './recorder';

export type AudioStatus =
	| 'idle'
	| 'connecting'
	| 'connected'
	| 'recording'
	| 'processing'
	| 'playing'
	| 'error'
	| 'closed';

type AudioEvent =
	| { type: 'ready' }
	| { type: 'error'; detail: string }
	| { type: 'user_audio_saved' }
	| { type: 'noise_detected' }
	| { type: 'user_transcription'; text: string }
	| { type: 'no_speech_detected' }
	| { type: 'assistant_message'; text: string; tip?: string; correction?: string }
	| { type: 'assistant_audio_end' }
	| { type: 'processing_cancelled' };

interface AudioConversationCallbacks {
	onStatusChange?: (status: AudioStatus) => void;
	onUserTranscription?: (text: string) => void;
	onAssistantMessage?: (text: string, tip: string | null, correction: string | null) => void;
	onError?: (message: string) => void;
	onVolumeChange?: (volume: number) => void;
}

export class AudioConversation {
	private ws: WebSocket | null = null;
	private recorder: AudioRecorder;
	private player = new AudioPlayer();
	private status: AudioStatus = 'idle';
	private interactionId: string;
	private callbacks: AudioConversationCallbacks;
	private pendingAudio: Uint8Array[] = [];
	private closing = false;
	private manuallyPaused = false;
	private isSpeaking = false;

	constructor(interactionId: string, callbacks: AudioConversationCallbacks = {}) {
		this.interactionId = interactionId;
		this.callbacks = callbacks;
		this.recorder = new AudioRecorder({
			sampleRate: 24_000,
			bufferSize: 4096,
			silenceThreshold: 350,
			silenceTimeoutMs: 1_800,
			minDurationMs: 800,
			callbacks: {
				onChunk: (chunk) => {
					if (this.status === 'recording' || (this.status === 'processing' && this.isSpeaking)) {
						this.ws?.send(chunk);
					}
				},
				onVolumeChange: (volume) => this.callbacks.onVolumeChange?.(volume),
				onSilence: () => {
					this.isSpeaking = false;
					this.stopRecording();
				},
				onSpeechStart: () => {
					this.isSpeaking = true;
				}
			}
		});
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
			if (this.closing) return;
			this.setStatus('error');
			this.callbacks.onError?.('WebSocket connection failed.');
		};

		this.ws.onclose = () => {
			if (this.closing) return;
			this.setStatus('closed');
			this.ws = null;
		};

		await this.waitForOpen();
	}

	startRecording(manual = false): void {
		if (manual) {
			this.manuallyPaused = false;
		}
		if (this.recorder.recording) {
			this.setStatus('recording');
			return;
		}
		void this._startRecording();
	}

	private async _startRecording(): Promise<void> {
		if (this.recorder.recording) return;
		if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
			await this.connect();
		}

		this.pendingAudio = [];
		this.isSpeaking = false;
		await this.recorder.start();
		this.setStatus('recording');
	}

	stopRecording(manual = false): void {
		if (!this.recorder.recording) return;
		if (manual) {
			this.manuallyPaused = true;
			this.recorder.stop();
			if (this.status === 'processing' || this.status === 'playing') {
				this.setStatus('connected');
				return;
			}
		}
		this.setStatus('processing');
		this.ws?.send(JSON.stringify({ type: 'commit', audio_format: 'pcm' }));
	}

	/** Mute: stop capturing the mic without closing the WS or committing audio. */
	muteMic(): void {
		if (!this.recorder.recording) return;
		this.manuallyPaused = true;
		this.recorder.stop();
		// Only change status if we're still in recording state (not processing/playing)
		if (this.status === 'recording') {
			this.setStatus('connected');
		}
	}

	/** Unmute: restart capturing the mic (WS must already be open). */
	unmuteMic(): void {
		this.manuallyPaused = false;
		if (this.recorder.recording) {
			this.setStatus('recording');
			return;
		}
		void this._startRecording();
	}

	get muted(): boolean {
		return this.manuallyPaused;
	}

	toggleRecording(): void {
		if (this.recorder.recording) {
			this.stopRecording(true);
		} else {
			this.startRecording(true);
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
            case 'processing_cancelled':
                this.setStatus('recording');
                break;
			case 'user_transcription':
				this.callbacks.onUserTranscription?.(event.text);
				break;
			case 'assistant_message':
				this.callbacks.onAssistantMessage?.(event.text, event.tip ?? null, event.correction ?? null);
				this.setStatus('playing');
				break;
			case 'assistant_audio_end':
				await this.playPendingAudio();
				if (!this.manuallyPaused) {
					this.setStatus('recording');
				} else {
					this.setStatus('connected');
				}
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
			const onError = () => {
				this.ws?.removeEventListener('open', onOpen);
				this.ws?.removeEventListener('error', onError);
				reject(new Error('WebSocket failed to open'));
			};
			this.ws.addEventListener('open', onOpen);
			this.ws.addEventListener('error', onError);
		});
	}

	private setStatus(status: AudioStatus): void {
		this.status = status;
		this.callbacks.onStatusChange?.(status);
	}

	close(): void {
		this.closing = true;
		this.ws?.close();
		this.recorder.stop();
		this.player.close();
		this.ws = null;
	}
}
