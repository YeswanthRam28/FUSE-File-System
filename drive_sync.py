"""
drive_sync.py
Sync daemon (OAuth version): uploads new/modified files under MOUNT_DIR/notes
to DRIVE_FOLDER_ID on Google Drive using user OAuth login.

Behavior:
 - Mirrors subfolders
 - Uploads new files
 - Updates existing files
 - Tracks processed files per session
"""
import os
import time
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# ---------------- CONFIG ----------------
CLIENT_SECRET_FILE = "client_secret.json"  # <-- download from Google Cloud OAuth credentials
TOKEN_FILE = "token.json"            # saved after first login
DRIVE_FOLDER_ID = "18hufMLDrwAxgDhNk4z4CZi6yVWOEx6gI"
MOUNT_DIR = "/tmp/myfs_mount"
SYNC_INTERVAL = 5
# ----------------------------------------

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def build_drive_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def find_child_folder(service, parent_id, folder_name):
    q = (
        f"'{parent_id}' in parents and name = '{folder_name}' "
        "and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    res = service.files().list(q=q, fields="files(id,name)").execute()
    files = res.get("files", [])
    return files[0]["id"] if files else None


def create_folder(service, parent_id, folder_name):
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def ensure_drive_path(service, rel_dir):
    if rel_dir in ("", "."):
        return DRIVE_FOLDER_ID

    parts = rel_dir.strip("/").split("/")
    parent = DRIVE_FOLDER_ID

    for p in parts:
        found = find_child_folder(service, parent, p)
        parent = found if found else create_folder(service, parent, p)

    return parent


def find_drive_file(service, drive_parent_id, filename):
    q = f"'{drive_parent_id}' in parents and name = '{filename}' and trashed = false"
    res = service.files().list(
        q=q, fields="files(id,name,modifiedTime,size)"
    ).execute()
    files = res.get("files", [])
    return files[0] if files else None


def upload_or_update(service, local, parent, name):
    try:
        media = MediaFileUpload(local, resumable=True)
        existing = find_drive_file(service, parent, name)

        if existing:
            service.files().update(fileId=existing["id"], media_body=media).execute()
            print(f"[UPDATE] {name}")
        else:
            meta = {"name": name, "parents": [parent]}
            new = service.files().create(body=meta, media_body=media, fields="id").execute()
            print(f"[UPLOAD] {name}")

    except HttpError as e:
        print(f"[ERROR] {local}: {e}")


def scan_and_sync(service, uploaded_set):
    notes_dir = os.path.join(MOUNT_DIR, "notes")
    if not os.path.exists(notes_dir):
        return

    for root, _, files in os.walk(notes_dir):
        for fname in files:
            local_path = os.path.join(root, fname)
            rel_path = os.path.relpath(local_path, MOUNT_DIR)

            if rel_path in uploaded_set:
                continue

            rel_dir = os.path.dirname(rel_path)
            drive_parent = ensure_drive_path(service, rel_dir)

            upload_or_update(service, local_path, drive_parent, fname)
            uploaded_set.add(rel_path)


def main():
    print("Drive sync (OAuth) starting...")
    service = build_drive_service()
    uploaded = set()

    try:
        while True:
            scan_and_sync(service, uploaded)
            time.sleep(SYNC_INTERVAL)
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
