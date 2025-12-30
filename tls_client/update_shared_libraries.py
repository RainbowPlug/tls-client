"""
Update tls-client shared library binaries from bogdanfinn/tls-client.
Based on Nintendocustom's update_lib.py approach.

Note: We use RainbowPlug/tls-client (fork of iamtorsten/tls-client) as our package,
but download binaries from bogdanfinn/tls-client since it has regular releases.
"""
from __future__ import annotations

import os
import sys
import platform
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import requests
import shutil

# Try to import tls_client to find its location
try:
    import tls_client
    TLS_CLIENT_PATH = os.path.dirname(tls_client.__file__)
except ImportError:
    # Fallback: search in site-packages
    for path in sys.path:
        if 'site-packages' in path:
            tls_client_path = os.path.join(path, 'tls_client')
            if os.path.exists(tls_client_path):
                TLS_CLIENT_PATH = tls_client_path
                break
    else:
        raise ImportError("tls_client package not found")

# Use bogdanfinn/tls-client as the source for binaries (most reliable with releases)
# RainbowPlug/tls-client is the fork we use, but it doesn't have releases
GITHUB_API_URL = "https://api.github.com/repos/bogdanfinn/tls-client/releases/latest"
DEPENDENCIES_DIR = os.path.join(TLS_CLIENT_PATH, "dependencies")
LOCAL_VERSION_FILE = os.path.join(DEPENDENCIES_DIR, "version.txt")
CHECK_INTERVAL = timedelta(hours=24)


def get_dependency_filename() -> str:
    """Get the expected binary filename based on platform"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "windows":
        if machine in ["amd64", "x86_64"]:
            return "tls-client-windows-amd64.dll"
        elif machine in ["x86", "i386"]:
            return "tls-client-windows-386.dll"
        else:
            return "tls-client-windows-amd64.dll"  # Default
    elif system == "linux":
        if machine in ["amd64", "x86_64"]:
            return "tls-client-linux-amd64.so"
        elif machine in ["arm64", "aarch64"]:
            return "tls-client-linux-arm64.so"
        else:
            return "tls-client-linux-amd64.so"  # Default
    elif system == "darwin":
        if machine in ["arm64", "aarch64"]:
            return "tls-client-darwin-arm64.dylib"
        else:
            return "tls-client-darwin-amd64.dylib"
    else:
        raise ValueError(f"Unsupported platform: {system}")


CURRENT_DEPENDENCY_FILENAME = get_dependency_filename()


def get_latest_release(session: requests.Session) -> tuple[Any, str | None] | None:
    """Get the latest release from bogdanfinn/tls-client GitHub API"""
    headers = {}
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    local_version_info = read_local_version()
    if local_version_info and 'Etag' in local_version_info:
        headers['If-None-Match'] = local_version_info['Etag']

    try:
        response = session.get(GITHUB_API_URL, headers=headers, timeout=30)
        if response.status_code == 304:  # Not Modified
            return None

        response.raise_for_status()
        latest_release = response.json()
        
        # Check if release has assets (releases without assets are not useful)
        if not latest_release.get("assets") or len(latest_release["assets"]) == 0:
            print("No assets found in release")
            return None
        
        return latest_release, response.headers.get('Etag')
    except requests.RequestException as e:
        print(f"Error fetching latest release from bogdanfinn/tls-client: {e}")
        return None


def read_local_version() -> Optional[Dict[str, str]]:
    """Read local version information from version.txt"""
    if os.path.exists(LOCAL_VERSION_FILE):
        try:
            with open(LOCAL_VERSION_FILE, "r") as f:
                lines = f.read().splitlines(False)
                if len(lines) >= 3:
                    return {
                        'version': lines[0],
                        'last_modified': lines[1],
                        'last_check': lines[2],
                        'Etag': lines[3] if len(lines) >= 4 else None
                    }
        except Exception as e:
            print(f"Error reading version file: {e}")
    return None


def save_local_version(version: str, last_modified: str, etag: Optional[str] = None) -> None:
    """Save version information to version.txt"""
    os.makedirs(DEPENDENCIES_DIR, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    try:
        with open(LOCAL_VERSION_FILE, "w") as f:
            f.write(f"{version}\n{last_modified}\n{now}")
            if etag:
                f.write(f"\n{etag}")
    except Exception as e:
        print(f"Error saving version file: {e}")


def download_file(session: requests.Session, url: str, dest_path: str) -> bool:
    """Download a file from URL to destination path"""
    try:
        response = session.get(url, timeout=60, stream=True)
        response.raise_for_status()
        
        # Create backup of existing file if it exists
        if os.path.exists(dest_path):
            backup_path = f"{dest_path}.backup"
            shutil.copy2(dest_path, backup_path)
        
        # Download to temporary file first
        temp_path = f"{dest_path}.tmp"
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Move temp file to final location
        shutil.move(temp_path, dest_path)
        
        # Remove backup if download succeeded
        backup_path = f"{dest_path}.backup"
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        return True
    except Exception as e:
        print(f"Error downloading file: {e}")
        # Restore backup if download failed
        backup_path = f"{dest_path}.backup"
        if os.path.exists(backup_path):
            shutil.move(backup_path, dest_path)
        return False


def should_check_update() -> bool:
    """Check if we should check for updates based on last check time"""
    local_version_info = read_local_version()
    if not local_version_info or 'last_check' not in local_version_info:
        return True
    
    try:
        last_check = datetime.fromisoformat(local_version_info['last_check'])
        return datetime.now(timezone.utc) - last_check > CHECK_INTERVAL
    except Exception:
        return True


def update_lib(force: bool = False) -> bool:
    """
    Update tls-client binaries if a new version is available.
    
    Args:
        force: If True, force update even if version matches
        
    Returns:
        True if update was successful or not needed, False on error
    """
    if not force and not should_check_update():
        return True

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    os.makedirs(DEPENDENCIES_DIR, exist_ok=True)

    result = get_latest_release(session)
    if result is None:
        if force:
            print("No update available or already up to date")
        return True

    latest_release, etag = result
    latest_version = latest_release["tag_name"]
    last_modified = latest_release.get("published_at", datetime.now(timezone.utc).isoformat())
    
    local_version_info = read_local_version()

    if not force and local_version_info and latest_version == local_version_info.get('version'):
        # Update last check time even if version is the same
        save_local_version(latest_version, last_modified, etag)
        return True

    print(f"New version found: {latest_version}. Updating...")

    assets = latest_release["assets"]
    dependency_base = CURRENT_DEPENDENCY_FILENAME.rsplit(".", 1)[0]
    
    found_asset = False
    for asset in assets:
        if asset["name"].startswith(dependency_base):
            download_url = asset["browser_download_url"]
            dest_path = os.path.join(DEPENDENCIES_DIR, CURRENT_DEPENDENCY_FILENAME)
            
            print(f"Downloading {CURRENT_DEPENDENCY_FILENAME} from {download_url}...")
            if download_file(session, download_url, dest_path):
                print(f"Successfully downloaded {CURRENT_DEPENDENCY_FILENAME}")
                save_local_version(latest_version, last_modified, etag)
                print(f"Updated to version {latest_version}")
                found_asset = True
                return True
            else:
                print(f"Failed to download {CURRENT_DEPENDENCY_FILENAME}")
                return False
    
    if not found_asset:
        print(f"Could not find asset for {CURRENT_DEPENDENCY_FILENAME}")
        print(f"Available assets: {[a['name'] for a in assets]}")
        return False
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update tls-client binaries")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update even if version matches"
    )
    args = parser.parse_args()
    
    success = update_lib(force=args.force)
    sys.exit(0 if success else 1)

