from datetime import date
import logging
import polars as pl

# stats_module
BASE_URL: str = "https://presta.sirom.net/statappel"
STATS_PAGE_URL: str = f"{BASE_URL}/stats_module.php"
LOGIN_FEDERAL_URL: str = f"{BASE_URL}/index_poste.php"
LOGIN_PERSONAL_ACCOUNT_URL: str = f"{BASE_URL}/login.php"
WELCOME_PAGE_URL: str = f"{BASE_URL}/accueil_global.php?arrivee=1"

START_DATE = date(2010, 1, 1)
END_DATE = date.today()

OUTPUT_DIR: str = "data/stats_module/extracted"

MIN_DELAY_SECONDS: int = 10
MAX_DELAY_SECONDS: int = 15

MAX_RETRIES_PER_DAY: int = 1

HEADLESS = True  # set False to watch it

LOG_LEVEL = logging.INFO

FINAL_SCHEMA = pl.Schema({
    "activite_ecoutant": pl.Categorical(),
    "attitude": pl.Categorical(),
    "commentaire_appel": pl.String(),
    "date_appel": pl.Date(),
    "date_debut_plage": pl.Date(),
    "date_fin_plage": pl.Date(),
    "date_message": pl.Date(),
    "duree_appel": pl.Duration(),
    "ecoutant": pl.String(),
    "grande_region": pl.Categorical(),
    "heure_debut_appel": pl.Time(),
    "heure_debut_plage": pl.Time(),
    "heure_fin_appel": pl.Time(),
    "heure_fin_plage": pl.Time(),
    "heure_message": pl.Time(),
    "nom_poste": pl.Categorical(),
    "sexe_appelant": pl.Enum(["Homme", "Femme", "Non déterminé"]),
    "sexe_ecoutant": pl.Enum(["Homme", "Femme", "Non déterminé"]),
    "situation1": pl.Categorical(),
    "situation2": pl.Categorical(),
    "situation3": pl.Categorical(),
    "age_appelant": pl.Categorical(),
    "age_ecoutant": pl.Categorical(),
    "type_communication": pl.Categorical(),
    "typologie_appel": pl.Categorical(),
    "appel_datetime": pl.Datetime(),  # built by create_appel_datetime - not present in raw data
})
