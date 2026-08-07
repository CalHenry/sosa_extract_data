from datetime import date
import logging
#"https://presta.sirom.net/statappel/stats_module.php
# stats_module
BASE_URL = "https://presta.sirom.net/statappel"
STATS_PAGE_URL = f"{BASE_URL}/stats_module.php"
LOGIN_FEDERAL_URL = f"{BASE_URL}/index_poste.php"
LOGIN_PERSONAL_ACCOUNT_URL = f"{BASE_URL}/login.php"
WELCOME_PAGE_URL = f"{BASE_URL}/accueil_global.php?arrivee=1"

START_DATE = date(2026, 5, 13)
END_DATE = date(2026, 7, 31)

OUTPUT_DIR = "data/stats_module"

MIN_DELAY_SECONDS = 10
MAX_DELAY_SECONDS = 20

MAX_RETRIES_PER_DAY = 1

HEADLESS = False  # set False to watch it

LOG_LEVEL = logging.INFO
