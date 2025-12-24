"""
Background jobs for data collection
"""
import json
from datetime import datetime
from typing import Optional, Callable

from . import youtube_api, db
from .models import Channel, ChannelSnapshot, Video, VideoSnapshot


def fetch_channel_data(
    channel_identifier: str,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Optional[int]:
    """
    Fetch channel data from YouTube API
    Returns: channel_id if successful, None otherwise
    """
    def log(msg: str):
        if progress_callback:
            progress_callback(msg)

    try:
        log("Parsing channel identifier...")

        # Get channel info
        log("Fetching channel information...")
        channel_data = youtube_api.get_channel_by_identifier(channel_identifier)

        # Check if we should fetch
        if not force_refresh and not db.should_fetch_channel(channel_data['channel_id']):
            existing_channel = db.get_channel_by_youtube_id(channel_data['channel_id'])
            log(f"Channel '{channel_data['title']}' was recently fetched. Skipping.")
            return existing_channel.id if existing_channel else None

        log(f"Processing channel: {channel_data['title']}")

        # Insert/update channel
        channel = Channel(
            youtube_channel_id=channel_data['channel_id'],
            title=channel_data['title'],
            handle=channel_data['handle'],
            thumbnail_url=channel_data['thumbnail_url'],
            last_fetched_at=datetime.now()
        )
        channel_id = db.insert_channel(channel)

        # Insert channel snapshot
        log("Saving channel statistics...")
        snapshot = ChannelSnapshot(
            channel_id=channel_id,
            fetched_at=datetime.now(),
            subscriber_count=channel_data['subscriber_count'],
            view_count=channel_data['view_count'],
            video_count=channel_data['video_count']
        )
        db.insert_channel_snapshot(snapshot)

        # Fetch recent videos
        uploads_playlist_id = channel_data.get('uploads_playlist_id')
        if uploads_playlist_id:
            log("Fetching recent videos...")
            video_ids = youtube_api.get_playlist_videos(uploads_playlist_id, max_results=50)

            if video_ids:
                log(f"Processing {len(video_ids)} videos...")
                videos_data = youtube_api.get_videos_info(video_ids)

                for i, video_data in enumerate(videos_data):
                    if (i + 1) % 10 == 0:
                        log(f"Processing video {i + 1}/{len(videos_data)}...")

                    # Insert/update video
                    video = Video(
                        youtube_video_id=video_data['video_id'],
                        channel_id=channel_id,
                        title=video_data['title'],
                        description=video_data['description'],
                        published_at=datetime.fromisoformat(
                            video_data['published_at'].replace('Z', '+00:00')
                        ) if video_data['published_at'] else None,
                        duration_seconds=video_data['duration_seconds'],
                        tags_json=json.dumps(video_data['tags']),
                        thumbnail_url=video_data['thumbnail_url'],
                        last_fetched_at=datetime.now()
                    )
                    video_id = db.insert_video(video)

                    # Insert video snapshot
                    video_snapshot = VideoSnapshot(
                        video_id=video_id,
                        fetched_at=datetime.now(),
                        view_count=video_data['view_count'],
                        like_count=video_data['like_count'],
                        comment_count=video_data['comment_count']
                    )
                    db.insert_video_snapshot(video_snapshot)

        log(f"✓ Successfully fetched data for '{channel_data['title']}'")
        return channel_id

    except youtube_api.YouTubeAPIError as e:
        log(f"✗ YouTube API error: {e}")
        return None
    except Exception as e:
        log(f"✗ Unexpected error: {e}")
        return None


def refresh_channel_data(
    channel_id: int,
    progress_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Refresh existing channel data
    Returns: True if successful, False otherwise
    """
    def log(msg: str):
        if progress_callback:
            progress_callback(msg)

    try:
        channel = db.get_channel_by_id(channel_id)
        if not channel:
            log("✗ Channel not found")
            return False

        log(f"Refreshing channel: {channel.title}")

        # Fetch updated data
        result = fetch_channel_data(
            channel.youtube_channel_id,
            force_refresh=True,
            progress_callback=progress_callback
        )

        return result is not None

    except Exception as e:
        log(f"✗ Error refreshing channel: {e}")
        return False


def refresh_all_channels(
    progress_callback: Optional[Callable[[str], None]] = None
) -> dict:
    """
    Refresh all channels in database
    Returns: dict with success/failure counts
    """
    def log(msg: str):
        if progress_callback:
            progress_callback(msg)

    channels = db.get_all_channels()
    results = {"success": 0, "failed": 0, "total": len(channels)}

    log(f"Refreshing {len(channels)} channels...")

    for i, channel in enumerate(channels):
        log(f"\n[{i + 1}/{len(channels)}] {channel.title}")

        success = refresh_channel_data(channel.id, progress_callback)

        if success:
            results["success"] += 1
        else:
            results["failed"] += 1

    log(f"\n✓ Refresh complete: {results['success']} succeeded, {results['failed']} failed")
    return results


def fetch_video_updates(
    channel_id: int,
    progress_callback: Optional[Callable[[str], None]] = None
) -> int:
    """
    Fetch only updated statistics for existing videos
    Returns: number of videos updated
    """
    def log(msg: str):
        if progress_callback:
            progress_callback(msg)

    try:
        videos = db.get_videos_by_channel(channel_id, limit=50)

        if not videos:
            log("No videos found for this channel")
            return 0

        log(f"Updating statistics for {len(videos)} videos...")

        video_ids = [v.youtube_video_id for v in videos]
        videos_data = youtube_api.get_videos_info(video_ids)

        video_data_map = {v['video_id']: v for v in videos_data}

        updated_count = 0
        for video in videos:
            if video.youtube_video_id in video_data_map:
                video_data = video_data_map[video.youtube_video_id]

                # Insert new snapshot
                video_snapshot = VideoSnapshot(
                    video_id=video.id,
                    fetched_at=datetime.now(),
                    view_count=video_data['view_count'],
                    like_count=video_data['like_count'],
                    comment_count=video_data['comment_count']
                )
                db.insert_video_snapshot(video_snapshot)
                updated_count += 1

        log(f"✓ Updated {updated_count} videos")
        return updated_count

    except Exception as e:
        log(f"✗ Error updating videos: {e}")
        return 0
