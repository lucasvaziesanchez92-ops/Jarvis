from backend.services.drive_service import list_files

try:
    print("Testing image/")
    print(list_files(mime_type="image/"))
except Exception as e:
    print("Error 1:", e)

try:
    print("Testing image (should use contains)")
    print(list_files(mime_type="image"))
except Exception as e:
    print("Error 2:", e)
