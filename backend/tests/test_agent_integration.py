import os
import unittest
import wave
import struct
from fastapi.testclient import TestClient
from app.main import app

class TestAgentIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Location of the generated test card in artifacts
        cls.sample_card_path = r"C:\Users\jaque\OneDrive\Documents\Desktop\6th sem\krid\backend\sample-card.jpg"
        if not os.path.exists(cls.sample_card_path):
            cls.sample_card_path = r"C:\Users\jaque\.gemini\antigravity\brain\f3a60f2c-6ed9-4922-9589-dbf75df327e3\sample_business_card_1782851745329.jpg"

    def test_full_agent_workflow(self):
        """
        Tests session creation, text messaging, image upload, audio notes,
        retrieving message histories, and deleting the session.
        """
        with TestClient(app) as client:
            # 1. Create a new chat session
            response = client.post("/api/sessions")
            self.assertEqual(response.status_code, 201)
            session_data = response.json()
            session_id = session_data["session_id"]
            self.assertIsNotNone(session_id)
            
            # 2. Send a text chat message
            chat_payload = {"session_id": session_id, "text": "Hello, what features do you support?"}
            response = client.post("/api/chat/message", json=chat_payload)
            self.assertEqual(response.status_code, 200)
            msg_data = response.json()
            self.assertEqual(msg_data["sender"], "assistant")
            self.assertIsNotNone(msg_data["text"])
            
            # 3. Upload a visiting card image if present
            if os.path.exists(self.sample_card_path):
                with open(self.sample_card_path, "rb") as f:
                    image_bytes = f.read()
                
                response = client.post(
                    "/api/chat/upload",
                    data={"session_id": session_id},
                    files={"file": ("card.jpg", image_bytes, "image/jpeg")}
                )
                self.assertEqual(response.status_code, 200)
                upload_data = response.json()
                self.assertEqual(upload_data["sender"], "assistant")
                self.assertTrue("Digitized" in upload_data["text"] or "Duplicate" in upload_data["text"])

            # 4. Upload a voice note WAV audio file
            temp_audio_path = "integration_test_silence.wav"
            with wave.open(temp_audio_path, "wb") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)
                # Write 1 second of silent frames
                num_frames = 16000
                for _ in range(num_frames):
                    wav_file.writeframesraw(struct.pack("<h", 0))
                    
            try:
                with open(temp_audio_path, "rb") as f:
                    audio_bytes = f.read()
                    
                response = client.post(
                    "/api/chat/upload",
                    data={"session_id": session_id},
                    files={"file": ("note.wav", audio_bytes, "audio/wav")}
                )
                self.assertEqual(response.status_code, 200)
                audio_data = response.json()
                self.assertEqual(audio_data["sender"], "assistant")
                self.assertIsNotNone(audio_data["text"])
            finally:
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
                    
            # 5. Fetch message logs history
            response = client.get(f"/api/sessions/{session_id}/messages")
            self.assertEqual(response.status_code, 200)
            messages_list = response.json()
            # Should contain at least the text chat, user query metadata, and replies
            self.assertGreaterEqual(len(messages_list), 2)
            
            # 6. Delete chat session
            response = client.delete(f"/api/sessions/{session_id}")
            self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
