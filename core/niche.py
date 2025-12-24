"""
Niche exploration with clustering and analysis
"""
import json
import math
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter
import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer

from . import youtube_api, db
from .models import NicheRun, NicheCluster


class NicheExplorer:
    """Niche exploration engine"""

    def __init__(self):
        self.model = None

    def load_model(self):
        """Load sentence transformer model"""
        if self.model is None:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def explore(
        self,
        keyword: str,
        max_videos: int = 200,
        n_clusters: int = 8,
        use_cache: bool = True,
        cache_hours: int = 24
    ) -> Optional[int]:
        """
        Explore niche by keyword
        Returns: niche_run_id if successful, None otherwise
        """
        params = {
            "max_videos": max_videos,
            "n_clusters": n_clusters
        }

        # Check cache
        if use_cache:
            cached_run = db.get_recent_niche_run(keyword, params, cache_hours)
            if cached_run:
                return cached_run.id

        # Search videos
        video_ids = youtube_api.search_videos(keyword, max_videos)

        if not video_ids:
            return None

        # Get video details
        videos_data = youtube_api.get_videos_info(video_ids)

        if not videos_data:
            return None

        # Create embeddings
        self.load_model()
        texts = [f"{v['title']} {v['description'][:200]}" for v in videos_data]
        embeddings = self.model.encode(texts)

        # Cluster
        kmeans = KMeans(n_clusters=min(n_clusters, len(videos_data)), random_state=42)
        labels = kmeans.fit_predict(embeddings)

        # Create niche run
        niche_run = NicheRun(
            keyword=keyword,
            fetched_at=datetime.now(),
            params_json=json.dumps(params)
        )
        niche_run_id = db.insert_niche_run(niche_run)

        # Analyze each cluster
        for cluster_idx in range(kmeans.n_clusters):
            cluster_videos = [
                videos_data[i] for i in range(len(videos_data))
                if labels[i] == cluster_idx
            ]

            # Generate cluster label using TF-IDF
            cluster_texts = [v['title'] for v in cluster_videos]
            cluster_label = self._generate_cluster_label(cluster_texts)

            # Calculate metrics
            metrics = self._calculate_cluster_metrics(cluster_videos)

            # Get sample videos (top 5 by views)
            sample_videos = sorted(
                cluster_videos,
                key=lambda x: x['view_count'],
                reverse=True
            )[:5]

            # Get unique channels
            channel_counter = Counter(v['channel_id'] for v in cluster_videos)
            sample_channels = [
                {"channel_id": ch_id, "video_count": count}
                for ch_id, count in channel_counter.most_common(5)
            ]

            # Save cluster
            cluster = NicheCluster(
                niche_run_id=niche_run_id,
                cluster_index=cluster_idx,
                label=cluster_label,
                metrics_json=json.dumps(metrics),
                sample_videos_json=json.dumps([
                    {
                        "video_id": v['video_id'],
                        "title": v['title'],
                        "view_count": v['view_count'],
                        "channel_id": v['channel_id']
                    }
                    for v in sample_videos
                ]),
                sample_channels_json=json.dumps(sample_channels)
            )
            db.insert_niche_cluster(cluster)

        return niche_run_id

    def _generate_cluster_label(self, texts: List[str]) -> str:
        """Generate cluster label using TF-IDF"""
        if not texts:
            return "Unknown"

        try:
            vectorizer = TfidfVectorizer(
                max_features=50,
                stop_words='english',
                ngram_range=(1, 2)
            )
            vectorizer.fit(texts)

            # Get top 5 terms
            feature_names = vectorizer.get_feature_names_out()
            top_terms = list(feature_names[:5])

            return " | ".join(top_terms)
        except:
            return "Cluster"

    def _calculate_cluster_metrics(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate cluster metrics"""
        if not videos:
            return {}

        view_counts = [v['view_count'] for v in videos]
        durations = [v['duration_seconds'] for v in videos]

        median_views = np.median(view_counts)
        total_views = sum(view_counts)

        # Count unique channels
        unique_channels = len(set(v['channel_id'] for v in videos))

        # Top 10 view concentration
        sorted_views = sorted(view_counts, reverse=True)
        top10_views = sum(sorted_views[:10])
        concentration = top10_views / total_views if total_views > 0 else 0

        # Shorts ratio
        shorts_count = sum(1 for d in durations if d <= 60)
        shorts_ratio = shorts_count / len(durations) if durations else 0

        # Calculate score
        # Performance: log of median views
        performance_score = math.log(median_views + 1)

        # Competition: log of unique channels
        competition_score = math.log(unique_channels + 1)

        # Concentration: higher = more concentrated (bad for entry)
        concentration_score = concentration

        # Final score: higher is better
        final_score = performance_score - 0.7 * competition_score - 0.5 * concentration_score

        return {
            "video_count": len(videos),
            "median_views": int(median_views),
            "total_views": int(total_views),
            "avg_views": int(np.mean(view_counts)),
            "unique_channels": unique_channels,
            "top10_concentration": concentration,
            "shorts_ratio": shorts_ratio,
            "performance_score": performance_score,
            "competition_score": competition_score,
            "concentration_score": concentration_score,
            "final_score": final_score
        }


def get_niche_results(niche_run_id: int) -> Dict[str, Any]:
    """Get niche exploration results"""
    clusters = db.get_niche_clusters(niche_run_id)

    results = []
    for cluster in clusters:
        metrics = cluster.metrics
        sample_videos = cluster.sample_videos
        sample_channels = cluster.sample_channels

        results.append({
            "cluster_index": cluster.cluster_index,
            "label": cluster.label,
            "video_count": metrics.get("video_count", 0),
            "median_views": metrics.get("median_views", 0),
            "avg_views": metrics.get("avg_views", 0),
            "unique_channels": metrics.get("unique_channels", 0),
            "top10_concentration": metrics.get("top10_concentration", 0),
            "shorts_ratio": metrics.get("shorts_ratio", 0),
            "final_score": metrics.get("final_score", 0),
            "sample_videos": sample_videos,
            "sample_channels": sample_channels
        })

    # Sort by final score descending
    results.sort(key=lambda x: x["final_score"], reverse=True)

    return {
        "clusters": results,
        "total_clusters": len(results)
    }
