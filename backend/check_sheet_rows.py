from app.services.sheets import sheets_service
import asyncio

async def check():
    print("Fetching all spreadsheet rows...")
    try:
        rows = sheets_service._service._get_all_rows()
        print(f"Total rows retrieved: {len(rows)}")
        
        target_uuids = [
            "970df8c8-44be-4b9d-bb07-c095e68e454c",
            "8beabfb3-d5be-4f85-9492-bf12ff816220"
        ]
        
        print("Checking target UUIDs:")
        for idx, row in enumerate(rows):
            safe_row_str = repr(row)
            if len(row) > 0 and row[0] in target_uuids:
                print(f"FOUND MATCH AT ROW {idx}: {safe_row_str}")
            elif any(uuid in safe_row_str for uuid in target_uuids):
                print(f"FOUND PARTIAL MATCH AT ROW {idx}: {safe_row_str}")
                
    except Exception as e:
        print(f"Error fetching rows: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check())
