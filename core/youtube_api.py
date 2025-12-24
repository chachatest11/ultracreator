"""
YouTube Data API v3 client
"""
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY", "")
BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeAPIError(Exception):
    """YouTube API error"""
    pass


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


def check_api_key():
    """Check if API key is configured"""
    if not API_KEY:
        raise YouTubeAPIError(
            "YouTube API key not found. Please set YOUTUBE_API_KEY in .env file"
        )


def get_channel_info(channel_id: str) -> Dict[str, Any]:
    """
    Get channel information
    Returns: dict with channel data
    """
    check_api_key()

    url = f"{BASE_URL}/channels"
    params = {
        "key": API_KEY,
        "id": channel_id,
        "part": "snippet,statistics,contentDetails"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

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

    except requests.exceptions.RequestException as e:
        raise YouTubeAPIError(f"Network error: {e}")
    except (KeyError, ValueError) as e:
        raise YouTubeAPIError(f"Failed to parse channel data: {e}")


def get_channel_by_handle(handle: str) -> Dict[str, Any]:
    """
    Get channel information by handle (@username)
    """
    check_api_key()

    # Remove @ if present
    handle = handle.lstrip("@")

    url = f"{BASE_URL}/channels"
    params = {
        "key": API_KEY,
        "forHandle": handle,
        "part": "snippet,statistics,contentDetails"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

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

    except requests.exceptions.RequestException as e:
        raise YouTubeAPIError(f"Network error: {e}")
    except (KeyError, ValueError) as e:
        raise YouTubeAPIError(f"Failed to parse channel data: {e}")


def get_playlist_videos(playlist_id: str, max_results: int = 50) -> List[str]:
    """
    Get video IDs from playlist
    Returns: list of video IDs
    """
    check_api_key()

    video_ids = []
    next_page_token = None

    url = f"{BASE_URL}/playlistItems"

    try:
        while len(video_ids) < max_results:
            params = {
                "key": API_KEY,
                "playlistId": playlist_id,
                "part": "contentDetails",
                "maxResults": min(50, max_results - len(video_ids)),
                "pageToken": next_page_token
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                video_id = item.get("contentDetails", {}).get("videoId")
                if video_id:
                    video_ids.append(video_id)

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        return video_ids

    except requests.exceptions.RequestException as e:
        raise YouTubeAPIError(f"Network error: {e}")
    except (KeyError, ValueError) as e:
        raise YouTubeAPIError(f"Failed to parse playlist data: {e}")


def get_videos_info(video_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Get detailed information for multiple videos
    Returns: list of video data dicts
    """
    check_api_key()

    if not video_ids:
        return []

    url = f"{BASE_URL}/videos"
    videos = []

    # Process in batches of 50 (API limit)
    for i in range(0, len(video_ids), 50):
        batch_ids = video_ids[i:i + 50]

        params = {
            "key": API_KEY,
            "id": ",".join(batch_ids),
            "part": "snippet,contentDetails,statistics"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

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

        except requests.exceptions.RequestException as e:
            raise YouTubeAPIError(f"Network error: {e}")
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
    check_api_key()

    video_ids = []
    next_page_token = None

    url = f"{BASE_URL}/search"

    try:
        while len(video_ids) < max_results:
            params = {
                "key": API_KEY,
                "q": keyword,
                "part": "id",
                "type": "video",
                "maxResults": min(50, max_results - len(video_ids)),
                "order": order,
                "pageToken": next_page_token
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if video_id:
                    video_ids.append(video_id)

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        return video_ids

    except requests.exceptions.RequestException as e:
        raise YouTubeAPIError(f"Network error: {e}")
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
