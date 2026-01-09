"""
Similar Channels Discovery
Find similar channels using multi-metric analysis (inspired by NexLev approach)
Includes content similarity analysis via TF-IDF and cosine similarity
"""
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import re
import math
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from . import youtube_api, db, metrics


def calculate_channel_similarity_score(
    base_metrics: Dict[str, Any],
    candidate_metrics: Dict[str, Any]
) -> float:
    """
    Calculate similarity score between two channels based on multiple metrics

    Inspired by NexLev's approach:
    - Subscriber/view ratio similarity
    - Upload frequency similarity
    - Shorts ratio similarity
    - Channel size proximity

    Returns:
        Similarity score (0-100, higher = more similar)
    """
    score = 0.0
    weights = {
        'subscriber_view_ratio': 0.30,  # Most important: content performance pattern
        'shorts_ratio': 0.25,            # Content type similarity
        'upload_frequency': 0.20,        # Upload pattern similarity
        'channel_size': 0.15,            # Similar audience size
        'engagement_pattern': 0.10       # Engagement similarity
    }

    # 1. Subscriber/View Ratio Similarity (NexLev's key metric)
    base_sub = base_metrics.get('subscriber_count', 1)
    base_views = base_metrics.get('avg_views_recent_10', 1)
    cand_sub = candidate_metrics.get('subscriber_count', 1)
    cand_views = candidate_metrics.get('avg_views_recent_10', 1)

    base_ratio = base_views / max(base_sub, 1) if base_sub > 0 else 0
    cand_ratio = cand_views / max(cand_sub, 1) if cand_sub > 0 else 0

    if base_ratio > 0 and cand_ratio > 0:
        ratio_diff = abs(math.log10(base_ratio + 0.0001) - math.log10(cand_ratio + 0.0001))
        ratio_score = max(0, 100 - (ratio_diff * 30))  # Penalize large differences
        score += ratio_score * weights['subscriber_view_ratio']

    # 2. Shorts Ratio Similarity
    base_shorts = base_metrics.get('shorts_metrics', {}).get('shorts_ratio', 0)
    cand_shorts = candidate_metrics.get('shorts_ratio', 0)

    shorts_diff = abs(base_shorts - cand_shorts)
    shorts_score = max(0, 100 - (shorts_diff * 100))  # 0-1 scale
    score += shorts_score * weights['shorts_ratio']

    # 3. Upload Frequency Similarity
    base_freq = base_metrics.get('upload_frequency', {}).get('average_days', 7)
    cand_freq = candidate_metrics.get('upload_frequency', 7)

    # Both upload frequently (< 7 days) or both infrequently
    if base_freq > 0 and cand_freq > 0:
        freq_ratio = min(base_freq, cand_freq) / max(base_freq, cand_freq)
        freq_score = freq_ratio * 100
        score += freq_score * weights['upload_frequency']

    # 4. Channel Size Proximity
    # Prefer channels within 0.1x - 10x size range
    if base_sub > 0 and cand_sub > 0:
        size_ratio = cand_sub / base_sub
        if 0.1 <= size_ratio <= 10:
            # Closer in size = higher score
            size_score = 100 - (abs(math.log10(size_ratio)) * 30)
            score += max(0, size_score) * weights['channel_size']

    # 5. Engagement Pattern (view variance type)
    base_variance = base_metrics.get('view_variance', {}).get('type', '')
    cand_variance = candidate_metrics.get('variance_type', '')

    if base_variance and cand_variance:
        if base_variance == cand_variance:
            score += 100 * weights['engagement_pattern']
        else:
            score += 50 * weights['engagement_pattern']

    return round(score, 2)


def get_channel_profile(channel_id: int) -> Dict[str, Any]:
    """
    Get comprehensive channel profile for similarity matching

    Args:
        channel_id: Internal database channel ID

    Returns:
        Dict with channel metrics profile
    """
    channel_metrics = metrics.get_channel_metrics(channel_id)

    return {
        'subscriber_count': channel_metrics.get('subscriber_count', 0),
        'avg_views_recent_10': channel_metrics.get('avg_views_recent_10', 0),
        'shorts_metrics': channel_metrics.get('shorts_metrics', {}),
        'upload_frequency': channel_metrics.get('upload_frequency', {}),
        'view_variance': channel_metrics.get('view_variance', {}),
        'top5_concentration': channel_metrics.get('top5_concentration', 0)
    }


def get_channel_content_text(channel_id: int, max_videos: int = 50, shorts_only: bool = True) -> str:
    """
    Extract text content from channel's videos (title + description + tags)

    Args:
        channel_id: Internal database channel ID
        max_videos: Maximum number of videos to analyze
        shorts_only: Only analyze shorts videos (≤60s)

    Returns:
        Combined text content of all videos
    """
    videos = db.get_videos_by_channel(channel_id, limit=max_videos)

    if not videos:
        return ""

    content_parts = []
    for video in videos:
        # Filter for shorts only if requested
        if shorts_only and video.duration_seconds > 60:
            continue

        # Combine title, description, and tags
        text_parts = []

        # Title (weight more - appears 3 times)
        if video.title:
            text_parts.append(video.title)
            text_parts.append(video.title)
            text_parts.append(video.title)

        # Description
        if video.description:
            # Take first 500 chars to avoid overwhelming with long descriptions
            desc = video.description[:500]
            text_parts.append(desc)

        # Tags
        if video.tags:
            tags_text = ' '.join(video.tags)
            text_parts.append(tags_text)
            text_parts.append(tags_text)  # Weight tags more

        if text_parts:
            content_parts.append(' '.join(text_parts))

    return ' '.join(content_parts)


def calculate_content_similarity(base_text: str, candidate_text: str) -> float:
    """
    Calculate content similarity between two text corpora using TF-IDF and cosine similarity

    Args:
        base_text: Text content from base channel
        candidate_text: Text content from candidate channel

    Returns:
        Similarity score (0-100, higher = more similar)
    """
    if not base_text or not candidate_text:
        return 0.0

    try:
        # Create TF-IDF vectorizer
        # Use character n-grams to handle Korean and other languages better
        vectorizer = TfidfVectorizer(
            max_features=500,
            ngram_range=(2, 4),  # Character n-grams
            analyzer='char',
            min_df=1,
            lowercase=True
        )

        # Vectorize both texts
        corpus = [base_text, candidate_text]
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

        # Convert to 0-100 scale
        return round(similarity * 100, 2)

    except Exception as e:
        print(f"Warning: Content similarity calculation failed: {e}")
        return 0.0


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
    Find similar channels using NexLev-inspired multi-metric analysis

    Algorithm:
    1. Analyze base channel's metrics profile (subscriber/view ratio, upload frequency, etc.)
    2. Discover candidate channels via keyword-based video search
    3. Calculate similarity scores using multiple metrics
    4. Rank by similarity score instead of simple appearance count

    Args:
        channel_id: Target YouTube channel ID to find similar channels for
        top_videos_count: Number of top videos to analyze (default: 10)
        related_per_video: Number of related videos to fetch per video (default: 20)
        min_appearances: Minimum number of times a channel must appear (default: 2)

    Returns:
        Dict with:
        - channels: List of similar channels ranked by similarity score
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

    # Get base channel's metrics profile for comparison
    base_profile = get_channel_profile(channel.id)

    # Get base channel's content text for content similarity analysis
    base_content_text = get_channel_content_text(channel.id, max_videos=50, shorts_only=True)
    print(f"📝 베이스 채널 콘텐츠 길이: {len(base_content_text)} 글자")

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

    # Analyze candidates and calculate similarity scores (NexLev approach)
    similar_channels = []

    for ch_id, appearance_count in channel_counter.most_common():
        if appearance_count < min_appearances:
            break

        try:
            # Get channel info from YouTube API
            channel_info = youtube_api.get_channel_info(ch_id)

            # Get recent videos to calculate metrics
            candidate_videos = youtube_api.get_videos(ch_id, max_results=50)

            # Calculate candidate channel metrics
            shorts_count = sum(1 for v in candidate_videos if v.get('duration_seconds', 61) <= 60)
            shorts_ratio = shorts_count / len(candidate_videos) if candidate_videos else 0

            # Calculate average views for recent videos
            recent_views = []
            for video in candidate_videos[:10]:
                view_count = video.get('view_count', 0)
                if view_count:
                    recent_views.append(view_count)
            avg_views = sum(recent_views) / len(recent_views) if recent_views else 0

            # Calculate upload frequency
            upload_dates = [v.get('published_at') for v in candidate_videos if v.get('published_at')]
            if len(upload_dates) >= 2:
                from datetime import datetime
                dates = [datetime.fromisoformat(d.replace('Z', '+00:00')) for d in upload_dates[:20]]
                dates.sort(reverse=True)
                intervals = [(dates[i] - dates[i+1]).total_seconds() / 86400 for i in range(len(dates)-1)]
                avg_upload_freq = sum(intervals) / len(intervals) if intervals else 7
            else:
                avg_upload_freq = 7

            # Extract content text from candidate videos (title + description + tags)
            # Filter for shorts only
            candidate_content_parts = []
            for vid in candidate_videos:
                if vid.get('duration_seconds', 61) <= 60:  # Shorts only
                    parts = []
                    # Title (weighted 3x)
                    if vid.get('title'):
                        parts.extend([vid['title']] * 3)
                    # Description (first 500 chars)
                    if vid.get('description'):
                        parts.append(vid['description'][:500])
                    # Tags (weighted 2x)
                    if vid.get('tags'):
                        tags_text = ' '.join(vid['tags'])
                        parts.extend([tags_text] * 2)
                    if parts:
                        candidate_content_parts.append(' '.join(parts))

            candidate_content_text = ' '.join(candidate_content_parts)

            # Calculate content similarity (TF-IDF + cosine similarity)
            content_similarity = calculate_content_similarity(base_content_text, candidate_content_text)

            # Build candidate metrics profile
            candidate_profile = {
                'subscriber_count': channel_info.get('subscriber_count', 0),
                'avg_views_recent_10': avg_views,
                'shorts_ratio': shorts_ratio,
                'upload_frequency': avg_upload_freq,
                'variance_type': '안정형' if len(recent_views) > 1 else 'unknown'
            }

            # Calculate similarity score using NexLev-inspired algorithm
            metrics_similarity = calculate_channel_similarity_score(base_profile, candidate_profile)

            # Calculate keyword relevance score (based on appearance count)
            appearance_ratio = appearance_count / max(total_search_results, 1)
            keyword_relevance = min(appearance_count / len(top_videos) * 100, 100)

            # Combined score: 40% content similarity + 35% metrics similarity + 25% keyword relevance
            final_score = (content_similarity * 0.40) + (metrics_similarity * 0.35) + (keyword_relevance * 0.25)

            similar_channels.append({
                "channel_id": ch_id,
                "title": channel_info["title"],
                "handle": channel_info["handle"],
                "thumbnail_url": channel_info["thumbnail_url"],
                "subscriber_count": channel_info["subscriber_count"],
                "video_count": channel_info["video_count"],
                "appearance_count": appearance_count,
                "content_similarity": round(content_similarity, 1),
                "metrics_similarity": round(metrics_similarity, 1),
                "keyword_relevance": round(keyword_relevance, 1),
                "confidence_score": round(final_score, 1),
                # Extra metrics for display
                "avg_views": int(avg_views),
                "shorts_ratio": round(shorts_ratio * 100, 1),
                "upload_freq_days": round(avg_upload_freq, 1)
            })

        except Exception as e:
            # Skip if channel info fetch fails
            error_msg = f"채널 {ch_id} 정보 가져오기 실패: {str(e)}"
            debug_info["errors"].append(error_msg)
            print(f"Warning: {error_msg}")
            continue

    # Sort by confidence score (similarity + keyword relevance)
    similar_channels.sort(key=lambda x: x['confidence_score'], reverse=True)

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
