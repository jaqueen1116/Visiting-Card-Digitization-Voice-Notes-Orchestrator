import unittest
import asyncio
from app.services.whatsapp import whatsapp_service
from app.models.contact import ContactCard

class TestWhatsAppService(unittest.TestCase):
    def test_send_notification_mock_fallback(self):
        """
        Verify that notification succeeds and prints mock logs if unconfigured.
        """
        contact = ContactCard(
            name="Alice Smith",
            phone="+1 555 9876",
            email="alice.smith@example.com",
            company="Mock Corp"
        )
        
        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(
            whatsapp_service.send_contact_notification(contact)
        )
        # Should return True (since it falls back to print logging successfully)
        self.assertTrue(success)

    def test_verify_connection_returns_bool(self):
        """
        Verify connection checking completes and returns a boolean value.
        """
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            whatsapp_service.verify_connection()
        )
        self.assertIsInstance(result, bool)

if __name__ == "__main__":
    unittest.main()
