from app.services.sheets import sheets_service
from app.models.contact import ContactCard
import asyncio
import uuid

async def test():
    print("Testing Google Sheets append...")
    contact = ContactCard(
        uuid=str(uuid.uuid4()),
        name="Test Append Contact",
        phone="+1234567890",
        email="test@append.com",
        company="Test Company",
        voice_notes="This is a test notes."
    )
    try:
        # Resolve SheetsService insert
        res = await sheets_service.insert_contact(contact)
        print("Insert contact response:", res)
    except Exception as e:
        print("Append failed:", str(e))

if __name__ == "__main__":
    asyncio.run(test())
