from __future__ import annotations

from typing import Any

from ytmusicapi import YTMusic

from ytm_daily_drive.config import NewsConfig, SongsConfig
from ytm_daily_drive.models import PlaylistEntry, RefreshPlan


def build_refresh_plan(ytmusic: YTMusic, news: NewsConfig, songs: SongsConfig) -> RefreshPlan:
    news_entry = select_news_episode(ytmusic, news)
    song_entries = select_recent_songs(ytmusic, songs, excluded_video_ids={news_entry.video_id} if news_entry else set())
    return RefreshPlan(news_entry=news_entry, song_entries=song_entries)


def select_news_episode(ytmusic: YTMusic, config: NewsConfig) -> PlaylistEntry | None:
    if not config.sources:
        if config.required:
            raise ValueError("No news.sources were configured, but news.required is true.")
        return None

    for source in config.sources:
        podcast = ytmusic.get_podcast(source.podcast_id, limit=5)
        episodes = podcast.get("episodes") or []
        if not episodes:
            continue

        episode = episodes[0]
        video_id = str(episode.get("videoId", "")).strip()
        title = str(episode.get("title", "")).strip()
        if video_id and title:
            return PlaylistEntry(video_id=video_id, title=title, source_label=source.name)

    if config.required:
        raise RuntimeError("Unable to find a playable episode from any configured news source.")

    return None


def select_recent_songs(
    ytmusic: YTMusic,
    config: SongsConfig,
    excluded_video_ids: set[str] | None = None,
) -> list[PlaylistEntry]:
    excluded_video_ids = excluded_video_ids or set()
    history = ytmusic.get_history()
    entries: list[PlaylistEntry] = []
    seen_video_ids = set(excluded_video_ids)

    for item in history[: config.history_limit]:
        if not _is_recent_music_item(item):
            continue

        video_id = str(item.get("videoId", "")).strip()
        title = str(item.get("title", "")).strip()
        if not video_id or not title or video_id in seen_video_ids:
            continue

        artist_names = ", ".join(
            str(artist.get("name", "")).strip()
            for artist in item.get("artists", [])
            if isinstance(artist, dict) and str(artist.get("name", "")).strip()
        )
        source_label = artist_names or "Recent listening"
        entries.append(PlaylistEntry(video_id=video_id, title=title, source_label=source_label))
        seen_video_ids.add(video_id)

        if len(entries) >= config.count:
            break

    if len(entries) < config.min_results:
        raise RuntimeError(
            "Not enough recent songs were found in YouTube Music history. "
            f"Needed at least {config.min_results}, found {len(entries)}."
        )

    return entries


def _is_recent_music_item(item: dict[str, Any]) -> bool:
    video_type = str(item.get("videoType", "")).strip()
    if video_type == "MUSIC_VIDEO_TYPE_PODCAST_EPISODE":
        return False

    artists = item.get("artists")
    if not isinstance(artists, list) or not artists:
        return False

    if not item.get("isAvailable", True):
        return False

    return True
