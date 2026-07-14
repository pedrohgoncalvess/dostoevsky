export interface RecorderCallbacks {
	onChunk?: (chunk: ArrayBuffer) => void;
	onVolumeChange?: (volume: number) => void;
	onSilence?: () => void;
}

export interface RecorderOptions {
	/** Callbacks for audio events. */
	callbacks?: RecorderCallbacks;
	/** Sample rate used for recording. */
	sampleRate?: number;
	/** Buffer size for the ScriptProcessorNode. */
	bufferSize?: number;
	/** RMS level below which audio is considered silent (0-32767). */
	silenceThreshold?: number;
	/** Milliseconds of continuous silence before auto-stop. */
	silenceTimeoutMs?: number;
	/** Minimum recording duration in milliseconds before auto-stop is allowed. */
	minDurationMs?: number;
}

export class AudioRecorder {
	private stream: MediaStream | null = null;
	private audioContext: AudioContext | null = null;
	private source: MediaStreamAudioSourceNode | null = null;
	private processor: ScriptProcessorNode | null = null;
	private analyser: AnalyserNode | null = null;
	private chunks: Int16Array[] = [];
	private isRecording = false;
	private options: RecorderOptions;
	private silenceSamples = 0;
	private sampleRate: number;
	private bufferSize: number;
	private silenceThreshold: number;
	private silenceTimeoutMs: number;
	private minDurationMs: number;
	private startTime = 0;
	private animationFrameId: number | null = null;

	constructor(options: RecorderOptions = {}) {
		this.options = options;
		this.sampleRate = options.sampleRate ?? 24_000;
		this.bufferSize = options.bufferSize ?? 4096;
		this.silenceThreshold = options.silenceThreshold ?? 350;
		this.silenceTimeoutMs = options.silenceTimeoutMs ?? 1_800;
		this.minDurationMs = options.minDurationMs ?? 800;
	}

	async start(): Promise<void> {
		if (this.isRecording) return;

		this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
		this.audioContext = new AudioContext({ sampleRate: this.sampleRate });
		this.source = this.audioContext.createMediaStreamSource(this.stream);
		this.processor = this.audioContext.createScriptProcessor(this.bufferSize, 1, 1);
		this.analyser = this.audioContext.createAnalyser();
		this.analyser.fftSize = 256;

		this.processor.onaudioprocess = (event) => {
			const input = event.inputBuffer.getChannelData(0);
			const int16 = float32ToInt16(input);
			this.chunks.push(int16);
			this.options.callbacks?.onChunk?.(
				int16.buffer.slice(int16.byteOffset, int16.byteOffset + int16.byteLength) as ArrayBuffer
			);
			this.updateSilence(int16);
		};

		this.source.connect(this.analyser);
		this.analyser.connect(this.processor);
		this.processor.connect(this.audioContext.destination);

		this.startTime = performance.now();
		this.silenceSamples = 0;
		this.isRecording = true;
		this.startVolumeLoop();
	}

	stop(): ArrayBuffer {
		this.stopVolumeLoop();
		this.processor?.disconnect();
		this.source?.disconnect();
		this.analyser?.disconnect();
		this.audioContext?.close();
		this.stream?.getTracks().forEach((track) => track.stop());

		this.processor = null;
		this.source = null;
		this.analyser = null;
		this.audioContext = null;
		this.stream = null;
		this.isRecording = false;
		this.silenceSamples = 0;

		const totalLength = this.chunks.reduce((sum, chunk) => sum + chunk.length, 0);
		const result = new Int16Array(totalLength);
		let offset = 0;
		for (const chunk of this.chunks) {
			result.set(chunk, offset);
			offset += chunk.length;
		}
		this.chunks = [];
		return result.buffer.slice(
			result.byteOffset,
			result.byteOffset + result.byteLength
		) as ArrayBuffer;
	}

	get recording(): boolean {
		return this.isRecording;
	}

	private updateSilence(int16: Int16Array): void {
		const rms = calculateRms(int16);
		const isSilent = rms < this.silenceThreshold;

		if (!isSilent) {
			this.silenceSamples = 0;
			return;
		}

		this.silenceSamples += int16.length;
		const silenceMs = (this.silenceSamples / this.sampleRate) * 1000;
		const durationMs = performance.now() - this.startTime;

		if (silenceMs >= this.silenceTimeoutMs && durationMs >= this.minDurationMs) {
			this.options.callbacks?.onSilence?.();
		}
	}

	private startVolumeLoop(): void {
		const loop = () => {
			if (!this.isRecording || !this.analyser) return;
			const data = new Uint8Array(this.analyser.frequencyBinCount);
			this.analyser.getByteFrequencyData(data);
			const volume = data.reduce((sum, v) => sum + v, 0) / data.length / 255;
			this.options.callbacks?.onVolumeChange?.(volume);
			this.animationFrameId = requestAnimationFrame(loop);
		};
		this.animationFrameId = requestAnimationFrame(loop);
	}

	private stopVolumeLoop(): void {
		if (this.animationFrameId !== null) {
			cancelAnimationFrame(this.animationFrameId);
			this.animationFrameId = null;
		}
	}
}

function float32ToInt16(input: Float32Array): Int16Array {
	const output = new Int16Array(input.length);
	for (let i = 0; i < input.length; i++) {
		const sample = Math.max(-1, Math.min(1, input[i]));
		output[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
	}
	return output;
}

function calculateRms(int16: Int16Array): number {
	if (int16.length === 0) return 0;
	let sum = 0;
	for (let i = 0; i < int16.length; i++) {
		sum += int16[i] * int16[i];
	}
	return Math.sqrt(sum / int16.length);
}
