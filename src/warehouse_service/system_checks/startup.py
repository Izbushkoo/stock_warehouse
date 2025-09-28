"""Command line entrypoint for startup checks."""

from __future__ import annotations

import argparse
import asyncio

from warehouse_service.logging import configure_logging, logger
from warehouse_service.notifications import TelegramNotifier
from warehouse_service.system_checks import run_checks


async def main(notify: bool) -> int:
    configure_logging()
    results = await run_checks()
    ok = all(result.ok for result in results)
    summary_lines = [f"{result.name}: {'OK' if result.ok else 'FAILED'} — {result.details}" for result in results]
    summary = "\n".join(summary_lines)

    if notify:
        notifier = TelegramNotifier()
        try:
            await notifier.notify_startup(ok, summary)
        finally:
            await notifier.aclose()
    if ok:
        logger.info("Startup checks passed")
        return 0
    logger.error("Startup checks failed")
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run system startup checks")
    parser.add_argument("--notify", action="store_true", help="Send results to Telegram")
    return parser.parse_args()


def entrypoint() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(main(args.notify)))


if __name__ == "__main__":  # pragma: no cover
    entrypoint()
