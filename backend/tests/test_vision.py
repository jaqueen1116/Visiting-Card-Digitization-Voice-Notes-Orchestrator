import os
import unittest
import asyncio
from app.services.vision import vision_service
from app.models.contact import ContactCard

class TestVisionService(unittest.TestCase):
    def setUp(self):
        # Path to the generated sample business card in artifacts
        self.sample_card_path = r"C:\Users\jaque\OneDrive\Documents\Desktop\6th sem\krid\backend\sample-card.jpg"
        # Fallback to absolute path in agent memory if not found in local workspace
        if not os.path.exists(self.sample_card_path):
            self.sample_card_path = r"C:\Users\jaque\.gemini\antigravity\brain\f3a60f2c-6ed9-4922-9589-dbf75df327e3\sample_business_card_1782851745329.jpg"
        
    def test_extract_contact_card_success(self):
        """
        Verify extracting data from a valid business card image.
        """
        if not os.path.exists(self.sample_card_path):
            self.skipTest(f"Sample card image not found at {self.sample_card_path}")

        with open(self.sample_card_path, "rb") as f:
            image_bytes = f.read()

        # Run async method in synchronous test context
        loop = asyncio.get_event_loop()
        contact = loop.run_until_complete(vision_service.extract_contact_card(image_bytes, "image/jpeg"))

        print("\n=== Extracted Contact Card ===")
        print(f"UUID: {contact.uuid}")
        print(f"Name: {contact.name}")
        print(f"Phone: {contact.phone}")
        print(f"Email: {contact.email}")
        print(f"Company: {contact.company}")

        self.assertIsInstance(contact, ContactCard)
        self.assertIsNotNone(contact.uuid)
        self.assertIsNotNone(contact.name)
        self.assertIn("John", contact.name)
        self.assertIn("acme", contact.company.lower())

    def test_extract_invalid_image_payload(self):
        """
        Verify empty image bytes payload triggers a ValueError.
        """
        loop = asyncio.get_event_loop()
        with self.assertRaises(ValueError) as context:
            loop.run_until_complete(vision_service.extract_contact_card(b"", "image/jpeg"))
        
        self.assertIn("Invalid image", str(context.exception))

    def test_extract_malformed_image_bytes(self):
        """
        Verify corrupt / malformed image bytes triggers a handled error.
        """
        loop = asyncio.get_event_loop()
        with self.assertRaises(ValueError) as context:
            # Pass random non-image bytes
            loop.run_until_complete(vision_service.extract_contact_card(b"not_an_image_data", "image/jpeg"))
            
        self.assertTrue(
            "unreadable" in str(context.exception).lower() or 
            "failure" in str(context.exception).lower() or 
            "api" in str(context.exception).lower() or
            "card" in str(context.exception).lower() or
            "business" in str(context.exception).lower()
        )

if __name__ == "__main__":
    unittest.main()
