export class AudioPlayer {
	private audioContext: AudioContext | null = null;

	async play(pcmBuffer: ArrayBuffer): Promise<void> {
		if (!this.audioContext) {
			this.audioContext = new AudioContext({ sampleRate: 24_000 });
		}

		const int16 = new Int16Array(pcmBuffer);
		const float32 = new Float32Array(int16.length);
		for (let i = 0; i < int16.length; i++) {
			const sample = int16[i];
			float32[i] = sample < 0 ? sample / 0x8000 : sample / 0x7fff;
		}

		const audioBuffer = this.audioContext.createBuffer(1, float32.length, 24_000);
		audioBuffer.copyToChannel(float32, 0);

		const source = this.audioContext.createBufferSource();
		source.buffer = audioBuffer;
		source.connect(this.audioContext.destination);

		return new Promise((resolve) => {
			source.onended = () => resolve();
			source.start();
		});
	}

	close(): void {
		this.audioContext?.close();
		this.audioContext = null;
	}
}
