from app.services.sheets import sheets_service
import asyncio

async def read():
    print("Reading full sheet A1:Z30...")
    try:
        service = sheets_service._service._get_service()
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=sheets_service._service.spreadsheet_id,
            range="Sheet1!A1:Z30"
        ).execute()
        rows = result.get("values", [])
        
        with open("sheet_contents.txt", "w", encoding="utf-8") as f:
            f.write(f"Total rows: {len(rows)}\n")
            for idx, row in enumerate(rows):
                f.write(f"Row {idx}: {repr(row)}\n")
        print("Success! Wrote sheet contents to sheet_contents.txt")
    except Exception as e:
        print("Read failed:", str(e))

if __name__ == "__main__":
    asyncio.run(read())
