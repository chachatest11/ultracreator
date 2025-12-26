"""
YouTube Data API v3 client with multi-key rotation support
"""
import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.googleapis.com/youtube/v3"
KEY_STATE_FILE = ".api_key_state.json"


class YouTubeAPIError(Exception):
    """YouTube API error"""
    pass


class APIKeyManager:
    """Manages multiple YouTube API keys with automatic rotation"""

    def __init__(self):
        self.api_keys = self._load_api_keys()
        self.current_index = self._load_current_index()
        self.exhausted_keys = set()

    def _load_api_keys(self) -> List[str]:
        """Load API keys from environment variable and UI storage"""
        keys = []

        # 1. Load from .env file
        single_key = os.getenv("YOUTUBE_API_KEY", "")
        multi_keys = os.getenv("YOUTUBE_API_KEYS", "")

        if multi_keys:
            # Split by comma and strip whitespace
            env_keys = [key.strip() for key in multi_keys.split(",") if key.strip()]
            keys.extend(env_keys)
        elif single_key:
            keys.append(single_key)

        # 2. Load from UI storage file
        try:
            from .api_key_storage import get_storage
            storage = get_storage()
            ui_keys = storage.get_active_keys()

            # Add UI keys that are not already in env keys
            for ui_key in ui_keys:
                if ui_key not in keys:
                    keys.append(ui_key)
        except:
            # If storage module not available or fails, continue with env keys
            pass

        return keys

    def _load_current_index(self) -> int:
        """Load current key index from state file"""
        try:
            if Path(KEY_STATE_FILE).exists():
                with open(KEY_STATE_FILE, 'r') as f:
                    state = json.load(f)
                    return state.get('current_index', 0)
        except:
            pass
        return 0

    def _save_current_index(self):
        """Save current key index to state file"""
        try:
            with open(KEY_STATE_FILE, 'w') as f:
                json.dump({'current_index': self.current_index}, f)
        except:
            pass

    def get_current_key(self) -> str:
        """Get current API key"""
        if not self.api_keys:
            raise YouTubeAPIError(
                "No YouTube API keys found. Please set YOUTUBE_API_KEY or YOUTUBE_API_KEYS in .env file"
            )

        # If all keys are exhausted, reset and try again
        if len(self.exhausted_keys) >= len(self.api_keys):
            raise YouTubeAPIError(
                f"All {len(self.api_keys)} API keys have exceeded their quota. "
                "Please wait until tomorrow or add more API keys."
            )

        # Find next non-exhausted key
        attempts = 0
        while attempts < len(self.api_keys):
            if self.current_index not in self.exhausted_keys:
                return self.api_keys[self.current_index]

            self.current_index = (self.current_index + 1) % len(self.api_keys)
            attempts += 1

        raise YouTubeAPIError("No available API keys")

    def rotate_key(self, reason: str = "quota_exceeded"):
        """Rotate to next API key"""
        if not self.api_keys:
            return

        # Mark current key as exhausted if quota exceeded
        if reason == "quota_exceeded":
            self.exhausted_keys.add(self.current_index)
            print(f"⚠️  API Key #{self.current_index + 1} quota exceeded. Switching to next key...")

        # Move to next key
        old_index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        self._save_current_index()

        # Print status
        available_keys = len(self.api_keys) - len(self.exhausted_keys)
        print(f"📍 Switched from Key #{old_index + 1} to Key #{self.current_index + 1}")
        print(f"✅ Available keys: {available_keys}/{len(self.api_keys)}")

    def is_quota_error(self, response_data: dict) -> bool:
        """Check if response contains quota exceeded error"""
        if "error" in response_data:
            error = response_data["error"]
            if isinstance(error, dict):
                errors = error.get("errors", [])
                for err in errors:
                    if err.get("reason") == "quotaExceeded":
                        return True
                # Also check error code
                if error.get("code") == 403 and "quota" in str(error).lower():
                    return True
        return False

    def get_key_count(self) -> int:
        """Get total number of API keys"""
        return len(self.api_keys)

    def get_available_key_count(self) -> int:
        """Get number of available (not exhausted) keys"""
        return len(self.api_keys) - len(self.exhausted_keys)


# Global API key manager instance
_key_manager = APIKeyManager()


def parse_duration(duration_str: str) -> int:
    """
    Parse ISO 8601 duration (PT#M#S) to seconds
    Examples:
        PT1M30S -> 90
        PT45S -> 45
        PT10M -> 600
    """
    if not duration_str:
        return 0

    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)

    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


def _make_api_request(url: str, params: dict, max_retries: int = None) -> dict:
    """
    Make API request with automatic key rotation on quota exceeded

    Args:
        url: API endpoint URL
        params: Request parameters (without 'key')
        max_retries: Maximum number of key rotations (default: number of available keys)

    Returns:
        API response data
    """
    if max_retries is None:
        max_retries = _key_manager.get_key_count()

    attempt = 0
    while attempt < max_retries:
        try:
            # Get current API key
            api_key = _key_manager.get_current_key()

            # Add key to params
            request_params = {**params, "key": api_key}

            # Make request
            response = requests.get(url, params=request_params, timeout=10)

            # Parse response
            data = response.json()

            # Check for quota error
            if _key_manager.is_quota_error(data):
                _key_manager.rotate_key("quota_exceeded")
                attempt += 1
                continue

            # Raise for other HTTP errors
            response.raise_for_status()

            return data

        except requests.exceptions.RequestException as e:
            # Don't retry on network errors
            raise YouTubeAPIError(f"Network error: {e}")

    # All keys exhausted
    raise YouTubeAPIError(
        f"All API keys have exceeded their quota. "
        f"Tried {max_retries} keys. Please wait until tomorrow or add more API keys."
    )


def get_channel_info(channel_id: str) -> Dict[str, Any]:
    """
    Get channel information
    Returns: dict with channel data
    """
    url = f"{BASE_URL}/channels"
    params = {
        "id": channel_id,
        "part": "snippet,statistics,contentDetails"
    }

    try:
        data = _make_api_request(url, params)

        if not data.get("items"):
            raise YouTubeAPIError(f"Channel not found: {channel_id}")

        item = data["items"][0]
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        content_details = item.get("contentDetails", {})

        return {
            "channel_id": item["id"],
            "title": snippet.get("title", ""),
            "handle": snippet.get("customUrl", ""),
            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "subscriber_count": int(statistics.get("subscriberCount", 0)),
            "view_count": int(statistics.get("viewCount", 0)),
            "video_count": int(statistics.get("videoCount", 0)),
            "uploads_playlist_id": content_details.get("relatedPlaylists", {}).get("uploads", "")
        }

    except (KeyError, ValueError) as e:
        raise YouTubeAPIError(f"Failed to parse channel data: {e}")


def get_channel_by_handle(handle: str) -> Dict[str, Any]:
    """
    Get channel information by handle (@username)
    """
    # Remove @ if present
    handle = handle.lstrip("@")

    url = f"{BASE_URL}/channels"
    params = {
        "forHandle": handle,
        "part": "snippet,statistics,contentDetails"
    }

    try:
        data = _make_api_request(url, params)

        if not data.get("items"):
            raise YouTubeAPIError(f"Channel not found for handle: @{handle}")

        item = data["items"][0]
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        content_details = item.get("contentDetails", {})

        return {
            "channel_id": item["id"],
            "title": snippet.get("title", ""),
            "handle": snippet.get("customUrl", ""),
            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "subscriber_count": int(statistics.get("subscriberCount", 0)),
            "view_count": int(statistics.get("viewCount", 0)),
            "video_count": int(statistics.get("videoCount", 0)),
            "uploads_playlist_id": content_details.get("relatedPlaylists", {}).get("uploads", "")
        }

    except (KeyError, ValueError) as e:
        raise YouTubeAPIError(f"Failed to parse channel data: {e}")


def get_playlist_videos(playlist_id: str, max_results: int = 50) -> List[str]:
    """
    Get video IDs from playlist
    Returns: list of video IDs
    """
    video_ids = []
    next_page_token = None

    url = f"{BASE_URL}/playlistItems"

    try:
        while len(video_ids) < max_results:
            params = {
                "playlistId": playlist_id,
                "part": "contentDetails",
                "maxResults": min(50, max_results - len(video_ids))
            }

            if next_page_token:
                params["pageToken"] = next_page_token

            data = _make_api_request(url, params)

            for item in data.get("items", []):
                video_id = item.get("contentDetails", {}).get("videoId")
                if video_id:
                    video_ids.append(video_id)

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        return video_ids

    except (KeyError, ValueError) as e:
        raise YouTubeAPIError(f"Failed to parse playlist data: {e}")


def get_videos_info(video_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Get detailed information for multiple videos
    Returns: list of video data dicts
    """
    if not video_ids:
        return []

    url = f"{BASE_URL}/videos"
    videos = []

    # Process in batches of 50 (API limit)
    for i in range(0, len(video_ids), 50):
        batch_ids = video_ids[i:i + 50]

        params = {
            "id": ",".join(batch_ids),
            "part": "snippet,contentDetails,statistics"
        }

        try:
            data = _make_api_request(url, params)

            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                content_details = item.get("contentDetails", {})
                statistics = item.get("statistics", {})

                videos.append({
                    "video_id": item["id"],
                    "channel_id": snippet.get("channelId", ""),
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                    "duration_seconds": parse_duration(content_details.get("duration", "")),
                    "tags": snippet.get("tags", []),
                    "view_count": int(statistics.get("viewCount", 0)),
                    "like_count": int(statistics.get("likeCount", 0)),
                    "comment_count": int(statistics.get("commentCount", 0))
                })

        except (KeyError, ValueError) as e:
            raise YouTubeAPIError(f"Failed to parse video data: {e}")

    return videos


def search_videos(keyword: str, max_results: int = 200,
                 order: str = "relevance") -> List[str]:
    """
    Search for videos by keyword
    Returns: list of video IDs

    Args:
        keyword: search query
        max_results: maximum number of results (up to 500)
        order: relevance, date, viewCount, rating
    """
    video_ids = []
    next_page_token = None

    url = f"{BASE_URL}/search"

    try:
        while len(video_ids) < max_results:
            params = {
                "q": keyword,
                "part": "id",
                "type": "video",
                "maxResults": min(50, max_results - len(video_ids)),
                "order": order
            }

            if next_page_token:
                params["pageToken"] = next_page_token

            data = _make_api_request(url, params)

            for item in data.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if video_id:
                    video_ids.append(video_id)

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        return video_ids

    except (KeyError, ValueError) as e:
        raise YouTubeAPIError(f"Failed to parse search results: {e}")


def parse_channel_identifier(identifier: str) -> Tuple[str, str]:
    """
    Parse channel identifier and determine type
    Returns: (type, value) where type is 'id', 'handle', or 'url'

    Examples:
        UC1234... -> ('id', 'UC1234...')
        @username -> ('handle', 'username')
        https://youtube.com/@username -> ('handle', 'username')
        https://youtube.com/channel/UC1234 -> ('id', 'UC1234...')
    """
    identifier = identifier.strip()

    # Channel ID (starts with UC)
    if identifier.startswith("UC") and len(identifier) == 24:
        return ("id", identifier)

    # Handle with @
    if identifier.startswith("@"):
        return ("handle", identifier[1:])

    # URL patterns
    url_patterns = [
        (r'youtube\.com/@([^/\?]+)', 'handle'),
        (r'youtube\.com/channel/([^/\?]+)', 'id'),
        (r'youtube\.com/c/([^/\?]+)', 'handle'),
        (r'youtube\.com/user/([^/\?]+)', 'handle'),
    ]

    for pattern, id_type in url_patterns:
        match = re.search(pattern, identifier)
        if match:
            return (id_type, match.group(1))

    # Default: treat as handle without @
    return ("handle", identifier)


def get_channel_by_identifier(identifier: str) -> Dict[str, Any]:
    """
    Get channel info by any identifier (ID, handle, or URL)
    """
    id_type, value = parse_channel_identifier(identifier)

    if id_type == "id":
        return get_channel_info(value)
    else:
        return get_channel_by_handle(value)
