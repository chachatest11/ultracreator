"""
Similar Channels Discovery
Find similar channels using keyword-based video search
"""
from typing import List, Dict, Any, Optional
from collections import Counter
import re

from . import youtube_api, db


def extract_search_keywords(title: str, max_words: int = 5) -> str:
    """
    Extract meaningful keywords from video title for search

    Args:
        title: Video title
        max_words: Maximum number of words to use

    Returns:
        Cleaned search query
    """
    # Remove special characters and extra spaces
    title = re.sub(r'[^\w\s가-힣]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()

    # Common stop words to remove (English and Korean)
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were',
        '그', '이', '저', '것', '수', '등', '들', '및', '또는'
    }

    # Split into words and filter
    words = title.split()
    filtered_words = []

    for word in words:
        if word.lower() not in stop_words and len(word) > 1:
            filtered_words.append(word)
            if len(filtered_words) >= max_words:
                break

    # Use original title if filtering resulted in nothing
    if not filtered_words:
        words = title.split()
        filtered_words = words[:max_words]

    return ' '.join(filtered_words)


def find_similar_channels(
    channel_id: str,
    top_videos_count: int = 10,
    related_per_video: int = 20,
    min_appearances: int = 2
) -> Dict[str, Any]:
    """
    Find similar channels by analyzing related videos

    Args:
        channel_id: Target YouTube channel ID to find similar channels for
        top_videos_count: Number of top videos to analyze (default: 10)
        related_per_video: Number of related videos to fetch per video (default: 20)
        min_appearances: Minimum number of times a channel must appear (default: 2)

    Returns:
        Dict with:
        - channels: List of similar channels with metadata
        - debug_info: Debug information about the search process
    """
    debug_info = {
        "channel_found": False,
        "videos_count": 0,
        "videos_with_snapshots": 0,
        "top_videos_analyzed": 0,
        "total_related_videos": 0,
        "unique_channels_found": 0,
        "channels_after_filter": 0,
        "errors": []
    }

    # Get channel from database by YouTube channel ID
    channel = db.get_channel_by_youtube_id(channel_id)

    if not channel:
        debug_info["errors"].append("채널을 데이터베이스에서 찾을 수 없습니다. Dashboard에서 먼저 채널을 추가해주세요.")
        return {"channels": [], "debug_info": debug_info}

    debug_info["channel_found"] = True

    # Get videos for the channel from database using internal ID
    videos = db.get_videos_by_channel(channel.id, limit=100)
    debug_info["videos_count"] = len(videos)

    if not videos:
        debug_info["errors"].append("이 채널의 영상 데이터가 없습니다. Dashboard에서 '영상 가져오기'를 먼저 실행해주세요.")
        return {"channels": [], "debug_info": debug_info}

    # Get latest snapshots for videos to get view counts
    videos_with_views = []
    for video in videos:
        snapshot = db.get_latest_video_snapshot(video.id)
        if snapshot:
            videos_with_views.append({
                'video': video,
                'view_count': snapshot.view_count
            })

    debug_info["videos_with_snapshots"] = len(videos_with_views)

    if not videos_with_views:
        debug_info["errors"].append("영상의 조회수 데이터(스냅샷)가 없습니다. Dashboard에서 채널 정보를 새로고침해주세요.")
        return {"channels": [], "debug_info": debug_info}

    # Sort by view count and get top N
    videos_with_views.sort(key=lambda x: x['view_count'], reverse=True)
    top_videos = videos_with_views[:top_videos_count]
    debug_info["top_videos_analyzed"] = len(top_videos)

    # Track which channels appear in search results
    channel_counter = Counter()
    total_search_results = 0

    # For each top video, search by keywords from title
    for item in top_videos:
        video = item['video']
        try:
            # Extract keywords from video title
            search_query = extract_search_keywords(video.title, max_words=5)

            if not search_query:
                continue

            # Search for similar videos using keywords
            similar_video_ids = youtube_api.search_videos(
                keyword=search_query,
                max_results=related_per_video,
                order="relevance"
            )

            if not similar_video_ids:
                continue

            # Get channel info for search results
            similar_videos = youtube_api.get_videos_info(similar_video_ids)
            total_search_results += len(similar_videos)

            # Count channel appearances
            for similar_video in similar_videos:
                similar_channel_id = similar_video.get('channel_id')

                # Skip the original channel
                if similar_channel_id and similar_channel_id != channel_id:
                    channel_counter[similar_channel_id] += 1

        except Exception as e:
            # Continue if a video fails
            error_msg = f"영상 '{video.title[:30]}...'의 키워드 검색 실패: {str(e)}"
            debug_info["errors"].append(error_msg)
            print(f"Warning: {error_msg}")
            continue

    debug_info["total_related_videos"] = total_search_results
    debug_info["unique_channels_found"] = len(channel_counter)

    if not channel_counter:
        debug_info["errors"].append(f"검색 결과에서 다른 채널을 찾지 못했습니다. (분석한 영상: {total_search_results}개)")
        return {"channels": [], "debug_info": debug_info}

    # Filter channels by minimum appearances
    similar_channels = []

    for ch_id, count in channel_counter.most_common():
        if count < min_appearances:
            break

        try:
            # Get channel info
            channel_info = youtube_api.get_channel_info(ch_id)

            # Calculate confidence score (0-100)
            # Based on: appearance frequency and proportion of total search results
            appearance_ratio = count / max(total_search_results, 1)
            frequency_score = min(count / len(top_videos) * 100, 100)
            ratio_score = appearance_ratio * 100
            confidence_score = (frequency_score * 0.6 + ratio_score * 0.4)

            similar_channels.append({
                "channel_id": ch_id,
                "title": channel_info["title"],
                "handle": channel_info["handle"],
                "thumbnail_url": channel_info["thumbnail_url"],
                "subscriber_count": channel_info["subscriber_count"],
                "video_count": channel_info["video_count"],
                "appearance_count": count,
                "confidence_score": round(confidence_score, 1)
            })

        except Exception as e:
            # Skip if channel info fetch fails
            error_msg = f"채널 {ch_id} 정보 가져오기 실패: {str(e)}"
            debug_info["errors"].append(error_msg)
            print(f"Warning: {error_msg}")
            continue

    debug_info["channels_after_filter"] = len(similar_channels)

    if not similar_channels:
        debug_info["errors"].append(f"최소 출현 횟수({min_appearances}회) 조건을 만족하는 채널이 없습니다. 유니크 채널 수: {len(channel_counter)}개")

    return {"channels": similar_channels, "debug_info": debug_info}


def find_similar_channels_simple(
    channel_id: str,
    max_similar: int = 10
) -> Dict[str, Any]:
    """
    Simplified version with default parameters

    Args:
        channel_id: Target channel ID
        max_similar: Maximum number of similar channels to return

    Returns:
        Dict with channels list and debug_info (up to max_similar channels)
    """
    result = find_similar_channels(
        channel_id=channel_id,
        top_videos_count=10,
        related_per_video=20,
        min_appearances=2
    )

    result["channels"] = result["channels"][:max_similar]
    return result
