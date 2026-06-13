from backend.services.drive_service import list_files

try:
    print(list_files(query="matematicas", mime_type=""))
except Exception as e:
    print("Error:", e)
