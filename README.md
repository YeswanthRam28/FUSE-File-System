# FUSEfs

FUSEfs is a lightweight user-space filesystem that allows local directories to synchronize seamlessly with Google Drive. It supports nested folder structures, automatic uploads and updates, and session-based tracking of synced files.

## Features

* **Google Drive Integration (OAuth)**: Sync local files to your Google Drive account securely.
* **Automatic File Updates**: Changes in local files are detected and mirrored on Drive.
* **Nested Directory Support**: Creates and maintains folder hierarchy on Drive.
* **Session-Based Tracking**: Tracks files uploaded or updated within the current session.
* **Cross-Platform**: Works on both Linux and Windows environments.
* **Configurable Sync**: Adjustable sync intervals for your workflow.
* **Error Handling**: Handles HTTP errors and permission issues gracefully.

## Requirements

* Python 3.8 or higher
* Packages listed in `requirements.txt` (google-auth, google-auth-oauthlib, google-api-python-client)
* Google Cloud OAuth credentials (`client_secret.json`)

## Setup

1. Clone the repository:

```bash
git clone https://github.com/YeswanthRam28/FUSEfs.git
cd FUSEfs
```

2. Create and activate a virtual environment:

```bash
python -m venv env
source env/bin/activate   # Linux/macOS
env\Scripts\activate    # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Place your `client_secret.json` in the project root.

5. Run the sync daemon:

```bash
python drive_sync.py
```

6. The first time you run it, a browser will open to authenticate with Google OAuth. After authentication, a `token.json` will be created for future sessions.

## Usage

* Add files to `MOUNT_DIR/notes` (default: `/tmp/myfs_mount/notes`).
* The daemon automatically uploads new files or updates changed files to Google Drive.
* Stop the daemon with `Ctrl+C`.

## Configuration

* `MOUNT_DIR`: Local directory to monitor.
* `DRIVE_FOLDER_ID`: Target folder ID on Google Drive.
* `SYNC_INTERVAL`: Time in seconds between sync scans.

## Git

Add `.gitignore` to exclude sensitive and temporary files:

```
env/
*.pyc
__pycache__/
token.json
```

## Contributing

Feel free to submit issues or pull requests for improvements, bug fixes, or new features.

## License

MIT License
