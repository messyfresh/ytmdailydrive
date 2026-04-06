from __future__ import annotations

import os

from ytmusicapi import OAuthCredentials, YTMusic

from ytm_daily_drive.config import AuthConfig


def build_client(auth: AuthConfig) -> YTMusic:
    if not auth.json_path.exists():
        raise FileNotFoundError(
            f"Auth file not found at {auth.json_path}. "
            "Create it outside git and mount it into the container."
        )

    if auth.method == "oauth":
        client_id = os.getenv("YTMUSIC_OAUTH_CLIENT_ID")
        client_secret = os.getenv("YTMUSIC_OAUTH_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise ValueError(
                "OAuth mode requires YTMUSIC_OAUTH_CLIENT_ID and "
                "YTMUSIC_OAUTH_CLIENT_SECRET to be set."
            )
        credentials = OAuthCredentials(client_id=client_id, client_secret=client_secret)
        return YTMusic(str(auth.json_path), auth.brand_account_id, oauth_credentials=credentials)

    return YTMusic(str(auth.json_path), auth.brand_account_id)
