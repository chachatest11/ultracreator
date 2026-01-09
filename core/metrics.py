"""
Analytics metrics calculation
"""
import statistics
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter

from . import db
from .models import Channel, Video, VideoSnapshot


def calculate_avg_views_recent(channel_id: int, count: int = 10) -> float:
    """Calculate average views for recent N videos"""
    videos = db.get_videos_by_channel(channel_id, limit=count)

    if not videos:
        return 0.0

    total_views = 0
    for video in videos:
        snapshot = db.get_latest_video_snapshot(video.id)
        if snapshot:
            total_views += snapshot.view_count

    return total_views / len(videos) if videos else 0.0


def calculate_views_48h(channel_id: int) -> int:
    """Calculate total views from videos published in last 48 hours"""
    videos = db.get_videos_by_channel(channel_id, limit=100)

    if not videos:
        return 0

    now = datetime.now()
    cutoff_time = now - timedelta(hours=48)

    total_views = 0
    for video in videos:
        if video.published_at and video.published_at >= cutoff_time:
            snapshot = db.get_latest_video_snapshot(video.id)
            if snapshot:
                total_views += snapshot.view_count

    return total_views


def calculate_upload_frequency(channel_id: int, count: int = 20) -> Dict[str, float]:
    """
    Calculate upload frequency metrics
    Returns: dict with average_days, median_days
    """
    videos = db.get_videos_by_channel(channel_id, limit=count)

    if len(videos) < 2:
        return {"average_days": 0.0, "median_days": 0.0}

    # Calculate intervals between consecutive uploads
    intervals = []
    for i in range(len(videos) - 1):
        if videos[i].published_at and videos[i + 1].published_at:
            delta = videos[i].published_at - videos[i + 1].published_at
            intervals.append(delta.total_seconds() / 86400)  # Convert to days

    if not intervals:
        return {"average_days": 0.0, "median_days": 0.0}

    return {
        "average_days": statistics.mean(intervals),
        "median_days": statistics.median(intervals)
    }


def calculate_view_variance(channel_id: int, count: int = 20) -> Dict[str, Any]:
    """
    Calculate view variance metrics
    Returns: dict with cv (coefficient of variation), type (stable/hit-based)
    """
    videos = db.get_videos_by_channel(channel_id, limit=count)

    if len(videos) < 2:
        return {"cv": 0.0, "type": "unknown", "stdev": 0.0, "mean": 0.0}

    view_counts = []
    for video in videos:
        snapshot = db.get_latest_video_snapshot(video.id)
        if snapshot:
            view_counts.append(snapshot.view_count)

    if not view_counts or all(v == 0 for v in view_counts):
        return {"cv": 0.0, "type": "unknown", "stdev": 0.0, "mean": 0.0}

    mean_views = statistics.mean(view_counts)
    stdev_views = statistics.stdev(view_counts) if len(view_counts) > 1 else 0.0
    cv = stdev_views / mean_views if mean_views > 0 else 0.0

    # Classify channel type
    # CV < 0.5: stable, CV >= 0.5: hit-based
    channel_type = "안정형" if cv < 0.5 else "한방형"

    return {
        "cv": cv,
        "type": channel_type,
        "stdev": stdev_views,
        "mean": mean_views
    }


def calculate_growth(channel_id: int, days: int) -> Dict[str, Any]:
    """
    Calculate channel growth over N days
    Returns: dict with subscriber_growth, view_growth, growth_rate
    """
    latest = db.get_latest_channel_snapshot(channel_id)
    past = db.get_channel_snapshot_before(channel_id, days)

    if not latest or not past:
        return {
            "subscriber_growth": 0,
            "view_growth": 0,
            "subscriber_growth_rate": 0.0,
            "view_growth_rate": 0.0
        }

    sub_growth = latest.subscriber_count - past.subscriber_count
    view_growth = latest.view_count - past.view_count

    sub_growth_rate = (sub_growth / past.subscriber_count * 100) if past.subscriber_count > 0 else 0.0
    view_growth_rate = (view_growth / past.view_count * 100) if past.view_count > 0 else 0.0

    return {
        "subscriber_growth": sub_growth,
        "view_growth": view_growth,
        "subscriber_growth_rate": sub_growth_rate,
        "view_growth_rate": view_growth_rate
    }


def calculate_shorts_ratio(channel_id: int, count: int = 50) -> Dict[str, float]:
    """
    Calculate Shorts ratio and duration distribution
    Returns: dict with shorts_ratio, duration_distribution
    """
    videos = db.get_videos_by_channel(channel_id, limit=count)

    if not videos:
        return {
            "shorts_ratio": 0.0,
            "under_30s": 0.0,
            "31_to_60s": 0.0,
            "over_60s": 0.0
        }

    under_30 = sum(1 for v in videos if v.duration_seconds <= 30)
    between_31_60 = sum(1 for v in videos if 31 <= v.duration_seconds <= 60)
    over_60 = sum(1 for v in videos if v.duration_seconds > 60)

    total = len(videos)
    shorts_count = under_30 + between_31_60

    return {
        "shorts_ratio": shorts_count / total if total > 0 else 0.0,
        "under_30s": under_30 / total if total > 0 else 0.0,
        "31_to_60s": between_31_60 / total if total > 0 else 0.0,
        "over_60s": over_60 / total if total > 0 else 0.0
    }


def calculate_title_length_avg(channel_id: int, count: int = 50) -> float:
    """Calculate average title length for recent videos"""
    videos = db.get_videos_by_channel(channel_id, limit=count)

    if not videos:
        return 0.0

    total_length = sum(len(v.title) for v in videos)
    return total_length / len(videos)


def calculate_top5_view_concentration(channel_id: int, count: int = 50) -> float:
    """
    Calculate view concentration in top 5 videos
    Returns: ratio of top 5 views to total views
    """
    videos = db.get_videos_by_channel(channel_id, limit=count)

    if not videos:
        return 0.0

    view_counts = []
    for video in videos:
        snapshot = db.get_latest_video_snapshot(video.id)
        if snapshot:
            view_counts.append(snapshot.view_count)

    if not view_counts:
        return 0.0

    total_views = sum(view_counts)
    if total_views == 0:
        return 0.0

    top5_views = sum(sorted(view_counts, reverse=True)[:5])
    return top5_views / total_views


def calculate_upload_patterns(channel_id: int, count: int = 50) -> Dict[str, Any]:
    """
    Calculate upload patterns: day of week, hour distribution
    Returns: dict with day_distribution, hour_distribution
    """
    videos = db.get_videos_by_channel(channel_id, limit=count)

    day_counts = Counter()
    hour_counts = Counter()

    for video in videos:
        if video.published_at:
            # Convert to KST (UTC+9)
            kst_time = video.published_at + timedelta(hours=9)
            day_counts[kst_time.strftime("%A")] += 1
            hour_counts[kst_time.hour] += 1

    total = len(videos)

    day_distribution = {
        day: count / total if total > 0 else 0.0
        for day, count in day_counts.items()
    }

    hour_distribution = {
        hour: count / total if total > 0 else 0.0
        for hour, count in hour_counts.items()
    }

    return {
        "day_distribution": day_distribution,
        "hour_distribution": hour_distribution,
        "most_common_day": day_counts.most_common(1)[0][0] if day_counts else "N/A",
        "most_common_hour": hour_counts.most_common(1)[0][0] if hour_counts else "N/A"
    }


def get_channel_metrics(channel_id: int) -> Dict[str, Any]:
    """
    Calculate all metrics for a channel
    Returns: comprehensive metrics dictionary
    """
    latest_snapshot = db.get_latest_channel_snapshot(channel_id)

    metrics = {
        # Basic stats
        "subscriber_count": latest_snapshot.subscriber_count if latest_snapshot else 0,
        "view_count": latest_snapshot.view_count if latest_snapshot else 0,
        "video_count": latest_snapshot.video_count if latest_snapshot else 0,

        # Performance metrics
        "avg_views_recent_10": calculate_avg_views_recent(channel_id, 10),

        # Upload frequency
        "upload_frequency": calculate_upload_frequency(channel_id, 20),

        # View variance
        "view_variance": calculate_view_variance(channel_id, 20),

        # Growth (7 and 30 days)
        "growth_7d": calculate_growth(channel_id, 7),
        "growth_30d": calculate_growth(channel_id, 30),

        # Shorts analysis
        "shorts_metrics": calculate_shorts_ratio(channel_id, 50),

        # Title length
        "avg_title_length": calculate_title_length_avg(channel_id, 50),

        # View concentration
        "top5_concentration": calculate_top5_view_concentration(channel_id, 50),

        # Upload patterns
        "upload_patterns": calculate_upload_patterns(channel_id, 50)
    }

    return metrics


def get_video_metrics(video_id: int) -> Dict[str, Any]:
    """Get metrics for a single video"""
    video = db.get_video_by_id(video_id)
    if not video:
        return {}

    snapshot = db.get_latest_video_snapshot(video_id)

    return {
        "video_id": video.youtube_video_id,
        "title": video.title,
        "published_at": video.published_at,
        "duration_seconds": video.duration_seconds,
        "is_short": video.duration_seconds <= 60,
        "view_count": snapshot.view_count if snapshot else 0,
        "like_count": snapshot.like_count if snapshot else 0,
        "comment_count": snapshot.comment_count if snapshot else 0,
        "engagement_rate": (
            (snapshot.like_count + snapshot.comment_count) / snapshot.view_count * 100
            if snapshot and snapshot.view_count > 0 else 0.0
        )
    }
