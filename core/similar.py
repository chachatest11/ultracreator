"""
Similar Channels Discovery
Find similar channels using related video analysis
"""
from typing import List, Dict, Any, Optional
from collections import Counter

from . import youtube_api, db


def find_similar_channels(
    channel_id: str,
    top_videos_count: int = 10,
    related_per_video: int = 20,
    min_appearances: int = 2
) -> List[Dict[str, Any]]:
    """
    Find similar channels by analyzing related videos

    Args:
        channel_id: Target YouTube channel ID to find similar channels for
        top_videos_count: Number of top videos to analyze (default: 10)
        related_per_video: Number of related videos to fetch per video (default: 20)
        min_appearances: Minimum number of times a channel must appear (default: 2)

    Returns:
        List of similar channels with metadata:
        - channel_id: Channel ID
        - title: Channel name
        - subscriber_count: Subscriber count
        - appearance_count: How many times this channel appeared in related videos
        - confidence_score: Score from 0-100 indicating similarity strength
    """
    # Get channel from database by YouTube channel ID
    channel = db.get_channel_by_youtube_id(channel_id)

    if not channel:
        return []

    # Get videos for the channel from database using internal ID
    videos = db.get_videos_by_channel(channel.id, limit=100)

    if not videos:
        return []

    # Get latest snapshots for videos to get view counts
    videos_with_views = []
    for video in videos:
        snapshot = db.get_latest_video_snapshot(video.id)
        if snapshot:
            videos_with_views.append({
                'video': video,
                'view_count': snapshot.view_count
            })

    if not videos_with_views:
        return []

    # Sort by view count and get top N
    videos_with_views.sort(key=lambda x: x['view_count'], reverse=True)
    top_videos = videos_with_views[:top_videos_count]

    # Track which channels appear in related videos
    channel_counter = Counter()
    total_related_videos = 0

    # For each top video, find related videos
    for item in top_videos:
        video = item['video']
        try:
            related_video_ids = youtube_api.search_related_videos(
                video.youtube_video_id,
                max_results=related_per_video
            )

            if not related_video_ids:
                continue

            # Get channel info for related videos
            related_videos = youtube_api.get_videos_info(related_video_ids)
            total_related_videos += len(related_videos)

            # Count channel appearances
            for related_video in related_videos:
                related_channel_id = related_video.get('channel_id')

                # Skip the original channel
                if related_channel_id and related_channel_id != channel_id:
                    channel_counter[related_channel_id] += 1

        except Exception as e:
            # Continue if a video fails
            print(f"Warning: Failed to get related videos for {video.youtube_video_id}: {e}")
            continue

    # Filter channels by minimum appearances
    similar_channels = []

    for ch_id, count in channel_counter.most_common():
        if count < min_appearances:
            break

        try:
            # Get channel info
            channel_info = youtube_api.get_channel_info(ch_id)

            # Calculate confidence score (0-100)
            # Based on: appearance frequency and proportion of total related videos
            appearance_ratio = count / max(total_related_videos, 1)
            frequency_score = min(count / top_videos_count * 100, 100)
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
            print(f"Warning: Failed to get info for channel {ch_id}: {e}")
            continue

    return similar_channels


def find_similar_channels_simple(
    channel_id: str,
    max_similar: int = 10
) -> List[Dict[str, Any]]:
    """
    Simplified version with default parameters

    Args:
        channel_id: Target channel ID
        max_similar: Maximum number of similar channels to return

    Returns:
        List of similar channels (up to max_similar)
    """
    similar = find_similar_channels(
        channel_id=channel_id,
        top_videos_count=10,
        related_per_video=20,
        min_appearances=2
    )

    return similar[:max_similar]
