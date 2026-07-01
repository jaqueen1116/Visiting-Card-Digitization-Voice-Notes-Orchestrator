import os
import wave
import struct
import unittest
import asyncio
from app.services.speech import speech_service

class TestSpeechService(unittest.TestCase):
    def setUp(self):
        self.test_audio_path = "test_temp_silence.wav"
        # Programmatically build a dummy WAV file containing 1 second of silence
        self.create_dummy_wav(self.test_audio_path, duration_sec=1)

    def tearDown(self):
        if os.path.exists(self.test_audio_path):
            os.remove(self.test_audio_path)

    def create_dummy_wav(self, filepath: str, duration_sec: int = 1, sample_rate: int = 16000):
        with wave.open(filepath, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            # Write silence (all zeros)
            num_frames = duration_sec * sample_rate
            for _ in range(num_frames):
                wav_file.writeframesraw(struct.pack('<h', 0))

    def test_transcribe_audio_success(self):
        """
        Verify speech_service transcribes audio correctly (returns string).
        """
        with open(self.test_audio_path, "rb") as f:
            audio_bytes = f.read()

        loop = asyncio.get_event_loop()
        transcript = loop.run_until_complete(
            speech_service.transcribe_audio(audio_bytes, "audio/wav")
        )

        print(f"\n=== Extracted Audio Transcript ===\n'{transcript}'")
        self.assertIsInstance(transcript, str)

    def test_transcribe_empty_payload(self):
        """
        Verify empty audio bytes payload triggers a ValueError.
        """
        loop = asyncio.get_event_loop()
        with self.assertRaises(ValueError) as context:
            loop.run_until_complete(
                speech_service.transcribe_audio(b"", "audio/wav")
            )
        
        self.assertIn("Invalid audio", str(context.exception))

if __name__ == "__main__":
    unittest.main()
