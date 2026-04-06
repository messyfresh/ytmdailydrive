from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PlaylistEntry:
    video_id: str
    title: str
    source_label: str


@dataclass(slots=True)
class RefreshPlan:
    news_entry: PlaylistEntry | None
    song_entries: list[PlaylistEntry]

    @property
    def ordered_video_ids(self) -> list[str]:
        video_ids: list[str] = []
        if self.news_entry is not None:
            video_ids.append(self.news_entry.video_id)
        video_ids.extend(entry.video_id for entry in self.song_entries)
        return video_ids
