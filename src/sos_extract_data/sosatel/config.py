from datetime import date
import logging

# SOSATEL
BASE_URL = "https://sosatel.sosamitie.org"
STATS_PAGE_URL = f"{BASE_URL}/stats/histories/search"
LOGIN_URL = f"{BASE_URL}/login"

START_DATE = date(2026, 5, 13)
END_DATE = date(2026, 7, 31)

OUTPUT_DIR = "data/sosatel/"

MIN_DELAY_SECONDS = 8
MAX_DELAY_SECONDS = 20

MAX_RETRIES_PER_DAY = 1  # extra attempts after the first failure

HEADLESS = True  # set False to watch it

LOG_LEVEL = logging.INFO
