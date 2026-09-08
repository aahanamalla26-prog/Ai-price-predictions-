"""
Worker process entrypoint. Runs the scraper consumer and the persistence
consumer concurrently in one process by default (simplest deployment); scale
horizontally with `docker compose up -d --scale worker=3` — Kafka consumer
groups handle partition rebalancing across replicas automatically.
"""
import asyncio
import logging
import signal

from app.consumers.price_check_consumer import run_price_check_consumer
from app.consumers.price_update_consumer import run_price_update_consumer
from app.scrapers.scraper import PlaywrightScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("pricepulse.worker.main")


async def main() -> None:
    scraper = PlaywrightScraper()
    await scraper.start()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)

    tasks = [
        asyncio.create_task(run_price_check_consumer(scraper), name="price-check-consumer"),
        asyncio.create_task(run_price_update_consumer(), name="price-update-consumer"),
    ]

    logger.info("PricePulse worker started: %d consumer task(s) running", len(tasks))

    try:
        await stop_event.wait()
        logger.info("Shutdown signal received, cancelling consumer tasks")
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await scraper.stop()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
