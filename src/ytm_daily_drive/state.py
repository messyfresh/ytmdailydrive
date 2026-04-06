from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(slots=True)
class AppState:
    playlist_id: str | None = None


def load_state(path: Path) -> AppState:
    if not path.exists():
        return AppState()

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"State file {path} must contain a JSON object.")

    playlist_id = data.get("playlist_id")
    if playlist_id is not None and not isinstance(playlist_id, str):
        raise ValueError("state.playlist_id must be a string if present.")

    return AppState(playlist_id=playlist_id)


def save_state(path: Path, state: AppState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"playlist_id": state.playlist_id}
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
