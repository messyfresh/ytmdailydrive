from __future__ import annotations

import argparse
from datetime import datetime
import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from ytm_daily_drive.config import AppConfig, load_config
from ytm_daily_drive.playlist_manager import apply_refresh_plan
from ytm_daily_drive.selection import build_refresh_plan
from ytm_daily_drive.state import load_state, save_state
from ytm_daily_drive.ytmusic_client import build_client


LOGGER = logging.getLogger("ytm_daily_drive")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Daily Drive-style YouTube Music playlist.")
    parser.add_argument("--config", help="Path to the YAML config file.")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Refresh the playlist immediately and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve the playlist contents without mutating YouTube Music.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Python logging level.",
    )
    return parser.parse_args()


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def run_refresh(config: AppConfig, dry_run: bool = False) -> None:
    timezone = ZoneInfo(config.scheduler.timezone)
    now = datetime.now(timezone)
    state = load_state(config.state.path)
    ytmusic = build_client(config.auth)

    account_info = ytmusic.get_account_info()
    LOGGER.info("Authenticated as %s", account_info.get("accountName", "unknown account"))

    plan = build_refresh_plan(ytmusic, config.news, config.songs)
    result = apply_refresh_plan(ytmusic, config, state, plan, now, dry_run=dry_run)

    if not dry_run:
        save_state(config.state.path, state)

    LOGGER.info("Playlist %s now contains %d items", result.playlist_id, len(result.video_ids))
    for index, video_id in enumerate(result.video_ids, start=1):
        LOGGER.info("  %d. %s", index, video_id)


def build_scheduler(config: AppConfig, dry_run: bool) -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone=config.scheduler.timezone)
    trigger = CronTrigger.from_crontab(config.scheduler.cron, timezone=config.scheduler.timezone)
    scheduler.add_job(run_refresh, trigger=trigger, args=[config, dry_run], id="daily-drive-refresh")
    return scheduler


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    config = load_config(args.config)

    if args.run_once:
        run_refresh(config, dry_run=args.dry_run)
        return

    scheduler = build_scheduler(config, dry_run=args.dry_run)
    LOGGER.info(
        "Scheduler started with cron '%s' in timezone %s",
        config.scheduler.cron,
        config.scheduler.timezone,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
