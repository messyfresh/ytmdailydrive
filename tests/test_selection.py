from ytm_daily_drive.config import SongsConfig
from ytm_daily_drive.selection import select_recent_songs


class FakeYTMusic:
    def __init__(self, history):
        self._history = history

    def get_history(self):
        return self._history


def test_select_recent_songs_skips_podcasts_and_duplicates():
    ytmusic = FakeYTMusic(
        [
            {
                "videoId": "podcast-1",
                "title": "Morning News",
                "videoType": "MUSIC_VIDEO_TYPE_PODCAST_EPISODE",
                "artists": [{"name": "NPR"}],
            },
            {
                "videoId": "song-1",
                "title": "First Song",
                "artists": [{"name": "Artist A"}],
                "isAvailable": True,
            },
            {
                "videoId": "song-1",
                "title": "First Song",
                "artists": [{"name": "Artist A"}],
                "isAvailable": True,
            },
            {
                "videoId": "song-2",
                "title": "Second Song",
                "artists": [{"name": "Artist B"}],
                "isAvailable": True,
            },
        ]
    )

    result = select_recent_songs(
        ytmusic,
        SongsConfig(count=2, min_results=2, history_limit=10),
    )

    assert [entry.video_id for entry in result] == ["song-1", "song-2"]
