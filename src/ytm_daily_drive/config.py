from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any

import yaml


@dataclass(slots=True)
class AuthConfig:
    method: str
    json_path: Path
    brand_account_id: str | None = None


@dataclass(slots=True)
class PlaylistConfig:
    name: str
    description: str
    privacy: str


@dataclass(slots=True)
class NewsSourceConfig:
    name: str
    podcast_id: str


@dataclass(slots=True)
class NewsConfig:
    required: bool
    sources: list[NewsSourceConfig]


@dataclass(slots=True)
class SongsConfig:
    count: int
    min_results: int
    history_limit: int


@dataclass(slots=True)
class SchedulerConfig:
    timezone: str
    cron: str


@dataclass(slots=True)
class StateConfig:
    path: Path


@dataclass(slots=True)
class AppConfig:
    auth: AuthConfig
    playlist: PlaylistConfig
    news: NewsConfig
    songs: SongsConfig
    scheduler: SchedulerConfig
    state: StateConfig


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} must contain a YAML mapping at the top level.")

    return data


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _ensure_mapping(raw: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"Config field '{field_name}' must be a mapping.")
    return raw


def _ensure_list(raw: Any, field_name: str) -> list[Any]:
    if not isinstance(raw, list):
        raise ValueError(f"Config field '{field_name}' must be a list.")
    return raw


def _resolve_path(value: str, config_path: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (config_path.parent / path).resolve()


def load_config(config_path: str | Path | None = None) -> AppConfig:
    config_path = Path(config_path or _env("YTM_DAILY_DRIVE_CONFIG", "config/settings.yaml")).resolve()
    raw = _read_yaml(config_path)

    auth_raw = _ensure_mapping(raw.get("auth", {}), "auth")
    playlist_raw = _ensure_mapping(raw.get("playlist", {}), "playlist")
    news_raw = _ensure_mapping(raw.get("news", {}), "news")
    songs_raw = _ensure_mapping(raw.get("songs", {}), "songs")
    scheduler_raw = _ensure_mapping(raw.get("scheduler", {}), "scheduler")
    state_raw = _ensure_mapping(raw.get("state", {}), "state")

    auth_file = _env("YTM_DAILY_DRIVE_AUTH_FILE", auth_raw.get("json_path", "secrets/auth.json"))
    auth_method = str(auth_raw.get("method", "browser")).lower()
    brand_account_id = _env("YTM_DAILY_DRIVE_BRAND_ACCOUNT_ID", auth_raw.get("brand_account_id"))
    state_path = _env("YTM_DAILY_DRIVE_STATE_FILE", state_raw.get("path", "data/state.json"))

    news_sources = []
    for index, source in enumerate(_ensure_list(news_raw.get("sources", []), "news.sources")):
        source_map = _ensure_mapping(source, f"news.sources[{index}]")
        name = str(source_map.get("name", "")).strip()
        podcast_id = str(source_map.get("podcast_id", "")).strip()
        if not name or not podcast_id:
            raise ValueError(f"news.sources[{index}] must define non-empty 'name' and 'podcast_id'.")
        news_sources.append(NewsSourceConfig(name=name, podcast_id=podcast_id))

    playlist_name = str(playlist_raw.get("name", "")).strip()
    if not playlist_name:
        raise ValueError("playlist.name must be set.")

    privacy = str(playlist_raw.get("privacy", "PRIVATE")).upper()
    if privacy not in {"PRIVATE", "PUBLIC", "UNLISTED"}:
        raise ValueError("playlist.privacy must be one of PRIVATE, PUBLIC, or UNLISTED.")

    songs_count = int(songs_raw.get("count", 4))
    min_results = int(songs_raw.get("min_results", min(songs_count, 3)))
    history_limit = int(songs_raw.get("history_limit", 100))

    if songs_count < 1:
        raise ValueError("songs.count must be at least 1.")
    if min_results < 1 or min_results > songs_count:
        raise ValueError("songs.min_results must be between 1 and songs.count.")
    if history_limit < songs_count:
        raise ValueError("songs.history_limit must be at least songs.count.")
    if auth_method not in {"browser", "oauth"}:
        raise ValueError("auth.method must be either 'browser' or 'oauth'.")

    return AppConfig(
        auth=AuthConfig(
            method=auth_method,
            json_path=_resolve_path(str(auth_file), config_path),
            brand_account_id=brand_account_id,
        ),
        playlist=PlaylistConfig(
            name=playlist_name,
            description=str(playlist_raw.get("description", "")).strip(),
            privacy=privacy,
        ),
        news=NewsConfig(
            required=bool(news_raw.get("required", True)),
            sources=news_sources,
        ),
        songs=SongsConfig(
            count=songs_count,
            min_results=min_results,
            history_limit=history_limit,
        ),
        scheduler=SchedulerConfig(
            timezone=str(scheduler_raw.get("timezone", "America/Chicago")).strip(),
            cron=str(scheduler_raw.get("cron", "0 6 * * *")).strip(),
        ),
        state=StateConfig(
            path=_resolve_path(str(state_path), config_path),
        ),
    )
