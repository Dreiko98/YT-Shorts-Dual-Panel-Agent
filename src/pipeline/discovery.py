"""Discovery module: fetch new long-form podcast videos from configured YouTube channels.

Stage 1 scope (MVP):
- Read channel list from configs/channels.yaml
- Query YouTube Data API v3 (search + videos) for recent uploads within lookback window
- Apply per-channel + global filters (duration, keywords, views, age, avoid shorts)
- Store new video metadata into PipelineDB (status=discovered)
- Respect simple quota budgeting (max results per channel, global daily limit placeholder)

Environment requirements:
- YOUTUBE_API_KEY must be set (simple API key usage)

Future extensions (not in MVP):
- OAuth authenticated calls to list private data
- Channel uploads playlist crawling for pagination beyond 50
- Retry with exponential backoff on quota exhaustion
- Adaptive scheduling based on channel activity
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml

from .db import PipelineDB

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

class DiscoveryError(Exception):
    pass

def load_channels_config(path: Path = Path("configs/channels.yaml")) -> Dict[str, Any]:
    if not path.exists():
        raise DiscoveryError(f"Archivo de configuración no encontrado: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    return data

def _parse_iso8601_duration(dur: str) -> int:
    # Very small parser for patterns like PT1H23M45S PT45M12S PT30M PT2H
    hours = minutes = seconds = 0
    cur = dur.replace('PT','')
    num = ''
    for ch in cur:
        if ch.isdigit():
            num += ch
        else:
            if ch == 'H':
                hours = int(num or 0); num=''
            elif ch == 'M':
                minutes = int(num or 0); num=''
            elif ch == 'S':
                seconds = int(num or 0); num=''
    total = hours*3600 + minutes*60 + seconds
    return total

def discover_new_videos(db: PipelineDB, config_path: Path = Path('configs/channels.yaml')) -> List[Dict[str, Any]]:
    cfg = load_channels_config(config_path)
    channels = [c for c in cfg.get('channels', []) if c.get('enabled', True)]
    discovery_cfg = cfg.get('discovery', {})
    lookback_days = discovery_cfg.get('lookback_days', 7)
    global_filters = discovery_cfg.get('global_filters', {})
    max_age_days = global_filters.get('max_age_days', 30)
    min_views = global_filters.get('min_views', 0)
    avoid_shorts = global_filters.get('avoid_shorts', True)

    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        raise DiscoveryError('YOUTUBE_API_KEY no configurada (añádela a .env o exporta en el entorno)')

    published_after = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
    new_videos: List[Dict[str, Any]] = []

    for ch in channels:
        channel_id = ch['id']
        max_results = int(ch.get('max_videos_per_check', 5))
        min_duration_minutes = int(ch.get('min_duration_minutes', 15))
        kw_filter = [k.lower() for k in ch.get('keywords_filter', [])]
        exclude_kw = [k.lower() for k in ch.get('exclude_keywords', [])]

        logger.info(f"Buscando videos canal {channel_id} ...")
        params = {
            'key': api_key,
            'channelId': channel_id,
            'part': 'snippet',
            'order': 'date',
            'publishedAfter': published_after,
            'maxResults': min(50, max_results),
            'type': 'video'
        }
        r = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=20)
        if r.status_code != 200:
            logger.warning(f"Search fallo canal {channel_id}: {r.status_code} {r.text[:100]}")
            continue
        items = r.json().get('items', [])
        video_ids = [it['id']['videoId'] for it in items if 'videoId' in it.get('id', {})]
        if not video_ids:
            continue
        # Fetch details
        params_details = {
            'key': api_key,
            'id': ','.join(video_ids),
            'part': 'contentDetails,statistics,snippet'
        }
        dr = requests.get(YOUTUBE_VIDEOS_URL, params=params_details, timeout=20)
        if dr.status_code != 200:
            logger.warning(f"Videos fallo canal {channel_id}: {dr.status_code} {dr.text[:100]}")
            continue
        for vid in dr.json().get('items', []):
            vid_id = vid['id']
            if db.video_exists(vid_id):
                continue
            snippet = vid.get('snippet', {})
            title = snippet.get('title', '')
            description = snippet.get('description', '')
            published_at = snippet.get('publishedAt')
            # Filters title/text
            lower_all = f"{title}\n{description}".lower()
            if kw_filter and not any(k in lower_all for k in kw_filter):
                continue
            if exclude_kw and any(k in lower_all for k in exclude_kw):
                continue
            # Avoid shorts by simple heuristics
            if avoid_shorts and (' #shorts' in lower_all or ' #short ' in lower_all or 'shorts/' in lower_all):
                continue
            # Age filter
            try:
                pub_dt = datetime.fromisoformat(published_at.replace('Z','+00:00'))
                age_days = (datetime.now(timezone.utc) - pub_dt).days
                if age_days > max_age_days:
                    continue
            except Exception:
                pass
            # Duration and views
            duration_iso = vid.get('contentDetails', {}).get('duration', 'PT0M0S')
            duration_seconds = _parse_iso8601_duration(duration_iso)
            if duration_seconds < min_duration_minutes * 60:
                continue
            view_count = int(vid.get('statistics', {}).get('viewCount', 0))
            if view_count < min_views:
                continue
            # Build record
            rec = {
                'video_id': vid_id,
                'channel_id': channel_id,
                'title': title,
                'description': description,
                'published_at': published_at,
                'duration_seconds': duration_seconds,
                'view_count': view_count,
            }
            if db.add_video(rec):
                new_videos.append(rec)
    return new_videos

__all__ = [
    'discover_new_videos', 'DiscoveryError'
]
