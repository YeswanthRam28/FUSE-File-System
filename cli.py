#!/usr/bin/env python3
"""
fusefs CLI - enhanced version (AI + Cloud integrated)

Commands:
  mount <path>    : mount filesystem (default /tmp/myfs_mount) and start sync daemon
  unmount         : stop sync and unmount filesystem
  status          : show status of mount + sync
  ls              : list files under mount
  push <local>    : copy local file into mount/notes to trigger upload
  pull <name>     : read file from mount (if present)
  summary <file>  : generate AI-based summary for a file
  chat            : open AI chatbot assistant (Gemini)
  logout          : remove token.json to force re-authentication

Notes:
 - This script expects `./myfs` (binary), `drive_sync.py`, and `ai/` folder (with summary.py & chat.py)
 - Default mount directory: /tmp/myfs_mount
 - PID files: .fusefs_myfs.pid and .fusefs_sync.pid in project root
"""

import argparse
import os
import subprocess
import sys
import time
import signal
import shutil
from pathlib import Path

PROJECT_ROOT = Path("/mnt/d/Projects/FUSEfs").resolve()
MYFS_BIN = PROJECT_ROOT / 'myfs'
DRIVE_SYNC = PROJECT_ROOT / 'drive_sync.py'
AI_DIR = PROJECT_ROOT / 'ai'
AI_SUMMARY = AI_DIR / 'summary.py'
AI_CHAT = AI_DIR / 'chat.py'
PID_MYFS = PROJECT_ROOT / '.fusefs_myfs.pid'
PID_SYNC = PROJECT_ROOT / '.fusefs_sync.pid'
DEFAULT_MOUNT = Path('/tmp/myfs_mount')
SYNC_LOG = PROJECT_ROOT / 'drive_sync.log'

BRAND = "🔥 FUSEfs"


def print_brand(msg):
    print(f"{BRAND} {msg}")


def write_pid(path: Path, pid: int):
    path.write_text(str(pid))


def read_pid(path: Path):
    if not path.exists():
        return None
    try:
        return int(path.read_text().strip())
    except Exception:
        return None


def is_process_running(pid: int):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def start_myfs(mountpoint: Path):
    if not MYFS_BIN.exists():
        print_brand("Error: myfs binary not found. Build it first.")
        sys.exit(1)
    mountpoint.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen([str(MYFS_BIN), str(mountpoint)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    write_pid(PID_MYFS, proc.pid)
    time.sleep(0.5)
    print_brand(f"mounted at {mountpoint} (pid {proc.pid})")
    return proc.pid


def start_sync():
    if not DRIVE_SYNC.exists():
        print_brand("Error: drive_sync.py not found. Put it in project root.")
        sys.exit(1)
    proc = subprocess.Popen([sys.executable, str(DRIVE_SYNC)],
                            stdout=open(SYNC_LOG, 'a'),
                            stderr=subprocess.STDOUT)
    write_pid(PID_SYNC, proc.pid)
    time.sleep(0.2)
    print_brand(f"Cloud sync started (pid {proc.pid})")
    return proc.pid


def stop_process(pidfile: Path, name: str):
    pid = read_pid(pidfile)
    if not pid:
        print_brand(f"{name} not running (no PID found).")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.5)
        if is_process_running(pid):
            os.kill(pid, signal.SIGKILL)
        print_brand(f"Stopped {name} (pid {pid})")
    except Exception as e:
        print_brand(f"Failed to stop {name}: {e}")
    finally:
        try:
            pidfile.unlink()
        except Exception:
            pass


def mount(args):
    mountpoint = Path(args.path) if args.path else DEFAULT_MOUNT
    if read_pid(PID_MYFS) and is_process_running(read_pid(PID_MYFS)):
        print_brand("Already mounted. Use 'status' to check.")
        return
    start_myfs(mountpoint)
    start_sync()
    print_brand("All systems go. Use 'fusefs status' to monitor.")


def unmount(args):
    stop_process(PID_SYNC, 'drive_sync')
    mountpoint = Path(args.path) if args.path else DEFAULT_MOUNT
    try:
        subprocess.run(['fusermount3', '-u', str(mountpoint)],
                       check=True,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        print_brand(f"Unmounted {mountpoint}")
    except subprocess.CalledProcessError:
        try:
            subprocess.run(['fusermount', '-u', str(mountpoint)],
                           check=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            print_brand(f"Unmounted {mountpoint}")
        except Exception as e:
            print_brand(f"fusermount failed: {e}")
    stop_process(PID_MYFS, 'myfs')


def status(args):
    pid_myfs = read_pid(PID_MYFS)
    pid_sync = read_pid(PID_SYNC)
    myfs_running = pid_myfs and is_process_running(pid_myfs)
    sync_running = pid_sync and is_process_running(pid_sync)
    print_brand("Status Report:")
    print(f"  myfs: {'running (pid '+str(pid_myfs)+')' if myfs_running else 'stopped'}")
    print(f"  sync: {'running (pid '+str(pid_sync)+')' if sync_running else 'stopped'}")
    if SYNC_LOG.exists():
        tail = ''.join(SYNC_LOG.read_text().splitlines()[-8:])
        print("\n  Recent sync log:")
        for line in tail.splitlines():
            print(f"    {line}")
    else:
        print("\n  No sync log available yet.")


def ls(args):
    mountpoint = Path(args.path) if args.path else DEFAULT_MOUNT
    if not mountpoint.exists():
        print_brand(f"Mountpoint {mountpoint} does not exist.")
        return
    print_brand(f"Listing {mountpoint}:")
    for p in sorted(mountpoint.iterdir()):
        print(f"  {p.name}")


def push(args):
    src = Path(args.file)
    if not src.exists():
        print_brand(f"Source file {src} not found.")
        return
    mountpoint = Path(args.mount) if args.mount else DEFAULT_MOUNT
    notes = mountpoint / 'notes'
    notes.mkdir(parents=True, exist_ok=True)
    dest = notes / src.name
    try:
        shutil.copy2(src, dest)
        print_brand(f"Copied {src} -> {dest} (sync will pick this up)")
        time.sleep(1)
        print_brand("Give the sync a few seconds; check 'fusefs status' or Drive web UI.")
    except Exception as e:
        print_brand(f"Failed to copy: {e}")


def pull(args):
    mountpoint = Path(args.mount) if args.mount else DEFAULT_MOUNT
    target = mountpoint / (args.name)
    if target.exists():
        print_brand(f"Found {target} — contents:\n")
        print(target.read_text())
    else:
        print_brand(f"{args.name} not present in mount. Pull from Drive UI or implement drive download.")


def logout(args):
    token = PROJECT_ROOT / 'token.json'
    token2 = PROJECT_ROOT / 'credentials.json'
    removed = False
    for f in (token, token2):
        if f.exists():
            try:
                f.unlink()
                print_brand(f"Removed {f.name}")
                removed = True
            except Exception as e:
                print_brand(f"Failed to remove {f.name}: {e}")
    if not removed:
        print_brand("No token files found.")


# ----------- AI FEATURES --------------

def ai_summary(args):
    if not AI_SUMMARY.exists():
        print_brand("AI summary module not found in ./ai/summary.py")
        return
    file_path = args.file
    subprocess.run(["python3", str(AI_SUMMARY), file_path])


def ai_chat(args):
    if not AI_CHAT.exists():
        print_brand("AI chat module not found in ./ai/chat.py")
        return
    subprocess.run(["python3", str(AI_CHAT)])


# --------------------------------------

def main():
    parser = argparse.ArgumentParser(prog='fusefs', description='FUSEfs CLI (AI + Cloud Integrated)')
    sub = parser.add_subparsers(dest='cmd')

    p_mount = sub.add_parser('mount')
    p_mount.add_argument('path', nargs='?', help='mount directory (default /tmp/myfs_mount)')

    p_unmount = sub.add_parser('unmount')
    p_unmount.add_argument('path', nargs='?', help='mount directory (default /tmp/myfs_mount)')

    p_status = sub.add_parser('status')
    p_ls = sub.add_parser('ls')
    p_ls.add_argument('path', nargs='?', help='mount directory (default /tmp/myfs_mount)')

    p_push = sub.add_parser('push')
    p_push.add_argument('file', help='local file to push into mount/notes')
    p_push.add_argument('--mount', help='mount directory (default /tmp/myfs_mount)')

    p_pull = sub.add_parser('pull')
    p_pull.add_argument('name', help='file name to read from mount')
    p_pull.add_argument('--mount', help='mount directory (default /tmp/myfs_mount)')

    p_summary = sub.add_parser('summary')
    p_summary.add_argument('file', help='file path to summarize using AI')

    p_chat = sub.add_parser('chat')

    p_logout = sub.add_parser('logout')

    args = parser.parse_args()

    if args.cmd == 'mount':
        mount(args)
    elif args.cmd == 'unmount':
        unmount(args)
    elif args.cmd == 'status':
        status(args)
    elif args.cmd == 'ls':
        ls(args)
    elif args.cmd == 'push':
        push(args)
    elif args.cmd == 'pull':
        pull(args)
    elif args.cmd == 'summary':
        ai_summary(args)
    elif args.cmd == 'chat':
        ai_chat(args)
    elif args.cmd == 'logout':
        logout(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
