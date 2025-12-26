"""
API Key Storage Manager
Manages YouTube API keys stored in JSON file with basic encryption
"""
import json
import base64
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


API_KEYS_FILE = ".api_keys.json"


class APIKeyStorage:
    """Manages API keys stored in local file"""

    def __init__(self):
        self.file_path = Path(API_KEYS_FILE)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create keys file if it doesn't exist"""
        if not self.file_path.exists():
            self._save_data({"keys": [], "version": "1.0"})

    def _encode_key(self, key: str) -> str:
        """Simple encoding for API key (not strong encryption, just obfuscation)"""
        return base64.b64encode(key.encode()).decode()

    def _decode_key(self, encoded_key: str) -> str:
        """Decode API key"""
        try:
            return base64.b64decode(encoded_key.encode()).decode()
        except:
            return encoded_key  # Return as-is if decode fails (backward compatibility)

    def _load_data(self) -> dict:
        """Load data from JSON file"""
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except:
            return {"keys": [], "version": "1.0"}

    def _save_data(self, data: dict):
        """Save data to JSON file"""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2)
            # Set restrictive file permissions (Unix-like systems)
            try:
                self.file_path.chmod(0o600)  # rw-------
            except:
                pass
        except Exception as e:
            print(f"Failed to save API keys: {e}")

    def get_all_keys(self) -> List[Dict]:
        """
        Get all stored keys with metadata
        Returns list of dicts with: id, key, name, enabled, created_at, last_used
        """
        data = self._load_data()
        keys = []

        for key_data in data.get("keys", []):
            keys.append({
                "id": key_data.get("id"),
                "key": self._decode_key(key_data.get("key", "")),
                "name": key_data.get("name", ""),
                "enabled": key_data.get("enabled", True),
                "created_at": key_data.get("created_at", ""),
                "last_used": key_data.get("last_used", "")
            })

        return keys

    def get_active_keys(self) -> List[str]:
        """Get only enabled API keys (plain strings)"""
        all_keys = self.get_all_keys()
        return [k["key"] for k in all_keys if k["enabled"]]

    def add_key(self, key: str, name: str = "") -> bool:
        """
        Add new API key
        Returns True if successful, False if key already exists
        """
        if not key or not key.strip():
            return False

        key = key.strip()
        data = self._load_data()

        # Check if key already exists
        for existing_key in data.get("keys", []):
            if self._decode_key(existing_key.get("key", "")) == key:
                return False

        # Generate ID
        key_id = len(data.get("keys", [])) + 1

        # Add new key
        new_key = {
            "id": key_id,
            "key": self._encode_key(key),
            "name": name or f"API Key {key_id}",
            "enabled": True,
            "created_at": datetime.now().isoformat(),
            "last_used": None
        }

        if "keys" not in data:
            data["keys"] = []

        data["keys"].append(new_key)
        self._save_data(data)

        return True

    def remove_key(self, key_id: int) -> bool:
        """Remove API key by ID"""
        data = self._load_data()

        original_count = len(data.get("keys", []))
        data["keys"] = [k for k in data.get("keys", []) if k.get("id") != key_id]

        if len(data["keys"]) < original_count:
            self._save_data(data)
            return True

        return False

    def toggle_key(self, key_id: int, enabled: bool) -> bool:
        """Enable or disable a key"""
        data = self._load_data()

        for key_data in data.get("keys", []):
            if key_data.get("id") == key_id:
                key_data["enabled"] = enabled
                self._save_data(data)
                return True

        return False

    def update_last_used(self, key: str):
        """Update last_used timestamp for a key"""
        data = self._load_data()

        for key_data in data.get("keys", []):
            if self._decode_key(key_data.get("key", "")) == key:
                key_data["last_used"] = datetime.now().isoformat()
                self._save_data(data)
                break

    def rename_key(self, key_id: int, new_name: str) -> bool:
        """Rename a key"""
        data = self._load_data()

        for key_data in data.get("keys", []):
            if key_data.get("id") == key_id:
                key_data["name"] = new_name
                self._save_data(data)
                return True

        return False

    def get_key_count(self) -> int:
        """Get total number of keys"""
        return len(self.get_all_keys())

    def get_active_key_count(self) -> int:
        """Get number of enabled keys"""
        return len(self.get_active_keys())

    def clear_all_keys(self) -> bool:
        """Clear all stored keys"""
        self._save_data({"keys": [], "version": "1.0"})
        return True

    def import_keys_from_string(self, keys_string: str) -> int:
        """
        Import multiple keys from comma-separated string
        Returns number of keys successfully added
        """
        keys = [k.strip() for k in keys_string.split(",") if k.strip()]
        added_count = 0

        for i, key in enumerate(keys):
            if self.add_key(key, f"Imported Key {i + 1}"):
                added_count += 1

        return added_count


# Global storage instance
_storage = APIKeyStorage()


def get_storage() -> APIKeyStorage:
    """Get global API key storage instance"""
    return _storage
