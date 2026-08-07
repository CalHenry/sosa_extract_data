import os
import random
import time
import logging
from datetime import date, timedelta
from getpass import getpass

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
    STATS_PAGE_URL,
    WELCOME_PAGE_URL,
)

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
    """Second loding - personal account..."""
    log.info("Logging in personal account")
    page.goto(LOGIN_PERSONAL_ACCOUNT_URL)

    page.fill('input[name="login"]', username)
    page.fill('input[name="mdp"], input[type="password"], #pwd', password)
    with page.expect_navigation():
        page.click('button[type="submit"], input[type="submit"]')

    page.wait_for_load_state("networkidle")
    log.info("Login personnal complete")

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

    federal_username = os.environ.get("STATS_MODULE_FEDERAL_USER") or input("Username: ")
    federal_password = os.environ.get("STATS_MODULE_FEDERAL_PASS") or getpass("Password: ")
    personal_username = os.environ.get("STATS_MODULE_USER") or input("Username: ")
    personal_password = os.environ.get("STATS_MODULE_PASS") or getpass("Password: ")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        login_federal(page, federal_username, federal_password)
        page.wait_for_load_state("networkidle")
        login_personal(page, personal_username, personal_password)
        page.wait_for_url("**/accueil_global**")
        print(page.url)

        with page.expect_popup() as page1_info:
            page.get_by_role("link", name="Statistiques Fédérales").click()
        page1 = page1_info.value
        page1.get_by_role("link", name="Module Statistique").click()
        page1.wait_for_load_state("networkidle")
        page1.locator("select[name=\"id_requete\"]").select_option("ecoutants1")
        page1.goto("https://presta.sirom.net/statappel/stats_module.php")
        #page1.locator('select[name="id_poste"]', label="ecoutant1").select_option("ecoutant1")
        print('yes')
        """
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
            """
        browser.close()

    log.info("Done")


if __name__ == "__main__":
    main()
