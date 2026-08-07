import os
import random
import time
import logging
from datetime import date, timedelta
from getpass import getpass

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from sos_extract_data.sosatel.config import (
    LOGIN_URL,
    LOG_LEVEL,
    START_DATE,
    END_DATE,
    HEADLESS,
    MAX_RETRIES_PER_DAY,
    MAX_DELAY_SECONDS,
    MIN_DELAY_SECONDS,
    OUTPUT_DIR,
    STATS_PAGE_URL,
)

load_dotenv()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scrape_sosatel.log"),
    ],
)
log = logging.getLogger(__name__)


def login(page, username: str, password: str):
    """Log into the dashboard"""
    log.info("Logging in...")
    page.goto(LOGIN_URL)

    page.fill('input[name="username"], input[type="email"], #username', username)
    page.fill('input[name="password"], input[type="password"], #password', password)
    page.click('button[type="submit"], input[type="submit"]')

    page.wait_for_load_state("networkidle")
    log.info("Login step complete")


def set_date_range(page, day: date):
    """Fill both date fields with the same day"""
    start_iso = day.isoformat()
    end_iso = (day + timedelta(days=1)).isoformat()

    page.fill("#stats_minStartTime", start_iso)
    page.fill("#stats_maxStartTime", end_iso)


def export_day(page, day: date, out_path: str) -> bool:
    """Run one day's query and save the resulting CSV. Returns True on success."""
    set_date_range(page, day)

    page.click("#searchBtnLabel")

    try:
        page.wait_for_selector("text=lignes retournées", timeout=30_000)
    except PWTimeout:
        log.warning(f"{day}: timed out waiting for results to load")
        return False

    try:
        with page.expect_download(timeout=30_000) as dl_info:
            page.click("text=Exporter en CSV")
        download = dl_info.value
        download.save_as(out_path)
    except PWTimeout:
        log.warning(f"{day}: timed out waiting for CSV download")
        return False

    return True


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    username = os.environ.get("SOSATEL_USER") or input("Username: ")
    password = os.environ.get("SOSATEL_PASS") or getpass("Password: ")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        login(page, username, password)
        page.goto(STATS_PAGE_URL)
        page.wait_for_load_state("networkidle")

        page.select_option("#stats_stat", label="Appels par heure de la journée")

        total_days = (END_DATE - START_DATE).days + 1
        for i, d in enumerate(daterange(START_DATE, END_DATE), start=1):
            out_path = os.path.join(OUTPUT_DIR, f"{d.isoformat()}.csv")

            if os.path.exists(out_path):
                log.info(f"[{i}/{total_days}] {d} already downloaded, skipping.")
                continue

            log.info(f"[{i}/{total_days}] Fetching {d} ...")

            success = False
            attempts = 0
            while not success and attempts <= MAX_RETRIES_PER_DAY:
                attempts += 1
                success = export_day(page, d, out_path)
                if not success and attempts <= MAX_RETRIES_PER_DAY:
                    log.info(f"{d}: retrying ({attempts}/{MAX_RETRIES_PER_DAY})...")
                    time.sleep(5)

            if not success:
                log.error(f"{d}: FAILED after retries, moving on.")

            delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
            log.info(f"Waiting {delay:.1f}s before next day...")
            time.sleep(delay)

        browser.close()

    log.info("Done")


if __name__ == "__main__":
    main()
