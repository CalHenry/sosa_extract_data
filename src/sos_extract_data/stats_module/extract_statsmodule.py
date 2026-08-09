import os
import random
import time
import logging
from datetime import date, timedelta
from getpass import getpass
from dateutil.relativedelta import relativedelta

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from sos_extract_data.stats_module.config import (
    LOGIN_FEDERAL_URL,
    LOGIN_PERSONAL_ACCOUNT_URL,
    LOG_LEVEL,
    START_DATE,
    END_DATE,
    HEADLESS,
    MAX_RETRIES_PER_DAY,
    MAX_DELAY_SECONDS,
    MIN_DELAY_SECONDS,
    OUTPUT_DIR,
)

# Query used on the "Module Statistique" page
REQUETE_NAME = "ecoutants1"
# date fields expect DD-MM-YYYY
POPUP_DATE_FORMAT = "%d-%m-%Y"

load_dotenv()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scrape_stats_module.log"),
    ],
)
log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Credentials / setup
# --------------------------------------------------------------------------- #
def get_credentials():
    """Pull credentials from .env"""
    federal_username = os.environ.get("STATS_MODULE_FEDERAL_USER") or input("Federal username: ")
    federal_password = os.environ.get("STATS_MODULE_FEDERAL_PASS") or getpass("Federal password: ")
    personal_username = os.environ.get("STATS_MODULE_USER") or input("Personal username: ")
    personal_password = os.environ.get("STATS_MODULE_PASS") or getpass("Personal password: ")
    return federal_username, federal_password, personal_username, personal_password


def launch_browser(playwright):
    """Launch the browser/context/page used for the whole session."""
    browser = playwright.chromium.launch(headless=HEADLESS)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()
    return browser, context, page


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #
def login_federal(page, username: str, password: str):
    """First login - federal account."""
    log.info("Logging in federal...")
    page.goto(LOGIN_FEDERAL_URL)

    page.select_option('select[name="id_poste"]', label="_SIEGE_FEDERAL")
    page.fill('input[name="login_poste"], input[type="text"], #login', username)
    page.fill('input[name="mdp_poste"], input[type="password"], #pwd', password)
    with page.expect_navigation():
        page.click('button[type="submit"], input[type="submit"]')

    page.wait_for_load_state("networkidle")
    log.info("Login federal complete")


def login_personal(page, username: str, password: str):
    """Second login - personal account."""
    log.info("Logging in personal account")
    page.goto(LOGIN_PERSONAL_ACCOUNT_URL)

    page.fill('input[name="login"]', username)
    page.fill('input[name="mdp"], input[type="password"], #pwd', password)
    with page.expect_navigation():
        page.click('button[type="submit"], input[type="submit"]')

    page.wait_for_load_state("networkidle")
    log.info("Login personnal complete")

# --------------------------------------------------------------------------- #
# Navigation to stats module
# --------------------------------------------------------------------------- #
def open_stats_module(page):
    """Open the 'Module Statistique' window and select the query to run."""
    with page.expect_popup() as popup_info:
        page.get_by_role("link", name="Statistiques Fédérales").click()
    stats_page = popup_info.value

    stats_page.get_by_role("link", name="Module Statistique").click()
    stats_page.wait_for_load_state("networkidle")
    stats_page.locator('select[name="id_requete"]').select_option(REQUETE_NAME)

    return stats_page


# --------------------------------------------------------------------------- #
# Date handling
# --------------------------------------------------------------------------- #
def period_range(start: date, end: date, months: int):
    """Yield (period_start, period_end) tuples covering [start, end]."""
    d = start
    while d <= end:
        period_end = min(d + relativedelta(months=months) - timedelta(days=1), end)
        yield d, period_end
        d = period_end + timedelta(days=1)

def set_date_range(stats_page, start: date, end: date):
    stats_page.locator('input[name="valeur[0]"]').fill(start.strftime(POPUP_DATE_FORMAT))
    stats_page.locator('input[name="valeur[1]"]').fill(end.strftime(POPUP_DATE_FORMAT))

# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #
def export_day(stats_page, start: date, end: date, out_path: str) -> bool:
    """Run one day's query on the stats module page and save the resulting CSV.

    Returns True on success, False if it timed out (caller can retry).
    """
    set_date_range(stats_page, start, end)

    try:
        with stats_page.expect_download(timeout=30_000) as download_info:
            stats_page.get_by_role("link", name="valider Exporter le résultat").click()
        download = download_info.value
        download.save_as(out_path)
    except PWTimeout:
        log.warning(f"{start}: timed out waiting for CSV download")
        return False

    return True

def export_date_range(stats_page, start: date, end: date, output_dir: str, months: int = 6):
    """Loop over each period (default: 12-month chunks) in the range, skipping
    periods already downloaded and retrying failed periods up to
    MAX_RETRIES_PER_DAY times."""

    periods = list(period_range(start, end, months=months))
    total_periods = len(periods)

    for i, (period_start, period_end) in enumerate(periods, start=1):
        out_path = os.path.join(
            output_dir, f"{period_start.isoformat()}_{period_end.isoformat()}.csv"
        )

        if os.path.exists(out_path):
            log.info(f"[{i}/{total_periods}] {period_start} to {period_end} already downloaded, skipping.")
            continue

        is_partial = period_end == end and period_end < start + relativedelta(months=months) - timedelta(days=1)
        if is_partial:
            log.info(f"[{i}/{total_periods}] {period_start} to {period_end} is a partial period (clipped to END_DATE).")

        log.info(f"[{i}/{total_periods}] Fetching {period_start} to {period_end} ...")

        success = False
        attempts = 0
        while not success and attempts <= MAX_RETRIES_PER_DAY:
            attempts += 1
            success = export_day(stats_page, period_start, period_end, out_path)
            if not success and attempts <= MAX_RETRIES_PER_DAY:
                log.info(f"{period_start} to {period_end}: retrying ({attempts}/{MAX_RETRIES_PER_DAY})...")
                time.sleep(5)

        if not success:
            log.error(f"{period_start} to {period_end}: FAILED after retries, moving on.")

        delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
        log.info(f"Waiting {delay:.1f}s before next period...")
        time.sleep(delay)

# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    federal_username, federal_password, personal_username, personal_password = get_credentials()

    with sync_playwright() as p:
        browser, context, page = launch_browser(p)

        # Logins (2 steps)
        login_federal(page, federal_username, federal_password)
        page.wait_for_load_state("networkidle")

        login_personal(page, personal_username, personal_password)
        page.wait_for_url("**/accueil_global**")
        log.info(f"Logged in, landed on {page.url}")

        # Query window
        stats_page = open_stats_module(page)

        export_date_range(stats_page, START_DATE, END_DATE, OUTPUT_DIR)

        browser.close()

    log.info("Done")


if __name__ == "__main__":
    main()
