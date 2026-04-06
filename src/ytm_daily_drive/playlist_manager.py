from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ytmusicapi import YTMusic

from ytm_daily_drive.config import AppConfig
from ytm_daily_drive.models import RefreshPlan
from ytm_daily_drive.state import AppState


@dataclass(slots=True)
class RefreshResult:
    playlist_id: str
    video_ids: list[str]


def apply_refresh_plan(
    ytmusic: YTMusic,
    config: AppConfig,
    state: AppState,
    plan: RefreshPlan,
    now: datetime,
    dry_run: bool = False,
) -> RefreshResult:
    playlist_id = resolve_playlist_id(ytmusic, config, state)
    description = render_playlist_description(config, plan, now)

    if dry_run:
        return RefreshResult(playlist_id=playlist_id or "<dry-run>", video_ids=plan.ordered_video_ids)

    if playlist_id is None:
        playlist_id = ytmusic.create_playlist(
            config.playlist.name,
            description,
            privacy_status=config.playlist.privacy,
            video_ids=plan.ordered_video_ids,
        )
    else:
        ytmusic.edit_playlist(
            playlist_id,
            title=config.playlist.name,
            description=description,
            privacyStatus=config.playlist.privacy,
        )
        existing_tracks = ytmusic.get_playlist(playlist_id, limit=None).get("tracks", [])
        if existing_tracks:
            videos_to_remove = [
                {"videoId": item["videoId"], "setVideoId": item["setVideoId"]}
                for item in existing_tracks
                if item.get("videoId") and item.get("setVideoId")
            ]
            if videos_to_remove:
                ytmusic.remove_playlist_items(playlist_id, videos_to_remove)
        if plan.ordered_video_ids:
            ytmusic.add_playlist_items(playlist_id, plan.ordered_video_ids, duplicates=True)

    state.playlist_id = playlist_id
    return RefreshResult(playlist_id=playlist_id, video_ids=plan.ordered_video_ids)


def resolve_playlist_id(ytmusic: YTMusic, config: AppConfig, state: AppState) -> str | None:
    if state.playlist_id:
        try:
            playlist = ytmusic.get_playlist(state.playlist_id, limit=1)
            if playlist.get("id") == state.playlist_id:
                return state.playlist_id
        except Exception:
            state.playlist_id = None

    library_playlists = ytmusic.get_library_playlists(limit=None)
    for playlist in library_playlists:
        if str(playlist.get("title", "")).strip() == config.playlist.name:
            return str(playlist.get("playlistId", "")).strip() or None

    return None


def render_playlist_description(config: AppConfig, plan: RefreshPlan, now: datetime) -> str:
    lines = []
    base = config.playlist.description.strip()
    if base:
        lines.append(base)

    lines.append(f"Refreshed automatically on {now.strftime('%Y-%m-%d %H:%M %Z')}.")

    if plan.news_entry:
        lines.append(f"News lead-in: {plan.news_entry.source_label} - {plan.news_entry.title}")

    if plan.song_entries:
        song_summary = "; ".join(f"{entry.title} - {entry.source_label}" for entry in plan.song_entries)
        lines.append(f"Recent songs: {song_summary}")

    return "\n".join(lines)
