export class AudioRecorder {
	private stream: MediaStream | null = null;
	private audioContext: AudioContext | null = null;
	private source: MediaStreamAudioSourceNode | null = null;
	private processor: ScriptProcessorNode | null = null;
	private chunks: Int16Array[] = [];
	private isRecording = false;

	async start(onChunk?: (chunk: ArrayBuffer) => void): Promise<void> {
		if (this.isRecording) return;

		this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
		this.audioContext = new AudioContext({ sampleRate: 24_000 });
		this.source = this.audioContext.createMediaStreamSource(this.stream);
		this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

		this.processor.onaudioprocess = (event) => {
			const input = event.inputBuffer.getChannelData(0);
			const int16 = float32ToInt16(input);
			this.chunks.push(int16);
			onChunk?.(
				int16.buffer.slice(int16.byteOffset, int16.byteOffset + int16.byteLength) as ArrayBuffer
			);
		};

		this.source.connect(this.processor);
		this.processor.connect(this.audioContext.destination);
		this.isRecording = true;
	}

	stop(): ArrayBuffer {
		this.processor?.disconnect();
		this.source?.disconnect();
		this.audioContext?.close();
		this.stream?.getTracks().forEach((track) => track.stop());

		this.processor = null;
		this.source = null;
		this.audioContext = null;
		this.stream = null;
		this.isRecording = false;

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
}

function float32ToInt16(input: Float32Array): Int16Array {
	const output = new Int16Array(input.length);
	for (let i = 0; i < input.length; i++) {
		const sample = Math.max(-1, Math.min(1, input[i]));
		output[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
	}
	return output;
}
