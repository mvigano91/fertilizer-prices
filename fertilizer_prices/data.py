"""Caricamento e normalizzazione delle serie storiche di prezzo dei fertilizzanti.

Due fonti disponibili:
- World Bank "Pink Sheet" (file Excel locale, prezzi mensili in $/mt)
- FRED (indici PPI mensili, via API REST, richiede FRED_API_KEY)
"""

import os
import re
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).parent / "data"
PINK_SHEET_PATH = DATA_DIR / "CMO-Historical-Data-Monthly.xlsx"

FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"

# Pagina da cui si fa scraping del link di download del file Pink Sheet: l'URL del file
# stesso (thedocs.worldbank.org/.../CMO-Historical-Data-Monthly.xlsx) contiene un hash di
# versione che cambia ad ogni pubblicazione, quindi non e' referenziabile direttamente e va
# individuato di volta in volta cercandolo in questa pagina.
COMMODITY_MARKETS_PAGE = "https://www.worldbank.org/en/research/commodity-markets"
_XLSX_LINK_RE = re.compile(
    r"https://thedocs\.worldbank\.org/[^\"'<>\s]*?CMO-Historical-Data-Monthly\.xlsx"
)
_HTTP_HEADERS = {"User-Agent": "Mozilla/5.0"}

# Etichetta prodotto (mostrata in GUI) -> colonna nel file Pink Sheet
PINK_SHEET_PRODUCTS = {
    "Azoto - Urea": "Urea",
    "Fosforo - DAP": "DAP",
    "Fosforo - TSP": "TSP",
    "Fosforo - Phosphate rock": "Phosphate rock",
    "Potassio - Cloruro di potassio (MOP)": "Potassium chloride",
}

# Etichetta prodotto (mostrata in GUI) -> series id FRED
FRED_PRODUCTS = {
    "Azoto - PPI Fertilizzanti Azotati": "PCU325311325311",
    "Azoto - PPI Urea": "PCU325311325311A4",
    "Fosforo - PPI Fertilizzanti Fosfatici": "PCU325312325312",
    "Potassio - PPI Potassa (mining)": "PCU212391212391",
}

SOURCES = {
    "World Bank Pink Sheet": PINK_SHEET_PRODUCTS,
    "FRED (PPI)": FRED_PRODUCTS,
}

GRANULARITIES = ["Mensile", "Trimestrale", "Annuale"]
MODES = ["Valore assoluto", "Variazione %"]

_RESAMPLE_RULE = {
    "Mensile": None,
    "Trimestrale": "QE",
    "Annuale": "YE",
}


class FredApiKeyMissing(Exception):
    pass


class FredRequestError(Exception):
    pass


class PinkSheetRefreshError(Exception):
    pass


_pink_sheet_cache = None


def refresh_pink_sheet_file() -> None:
    """Scarica l'ultima versione del file Pink Sheet dal sito World Bank e sovrascrive
    il file locale, poi invalida la cache in memoria cosi' la prossima lettura prende i
    dati appena scaricati."""
    try:
        page = requests.get(COMMODITY_MARKETS_PAGE, timeout=20, headers=_HTTP_HEADERS)
        page.raise_for_status()
    except requests.RequestException as exc:
        raise PinkSheetRefreshError(f"Impossibile raggiungere il sito World Bank: {exc}") from exc

    match = _XLSX_LINK_RE.search(page.text)
    if not match:
        raise PinkSheetRefreshError(
            "Non ho trovato il link al file Excel nella pagina World Bank: "
            "la struttura del sito potrebbe essere cambiata."
        )

    try:
        file_response = requests.get(match.group(0), timeout=30, headers=_HTTP_HEADERS)
        file_response.raise_for_status()
    except requests.RequestException as exc:
        raise PinkSheetRefreshError(f"Download del file Excel fallito: {exc}") from exc

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PINK_SHEET_PATH.write_bytes(file_response.content)

    global _pink_sheet_cache
    _pink_sheet_cache = None


def load_pink_sheet_prices() -> pd.DataFrame:
    """Legge il foglio 'Monthly Prices' del file World Bank locale."""
    global _pink_sheet_cache
    if _pink_sheet_cache is not None:
        return _pink_sheet_cache

    raw = pd.read_excel(PINK_SHEET_PATH, sheet_name="Monthly Prices", header=4)
    raw = raw.iloc[1:]  # riga 0 dopo l'header contiene le unita' di misura, non dati
    raw = raw.rename(columns={raw.columns[0]: "Date"})
    raw.columns = ["Date"] + [str(c).strip().rstrip("*").strip() for c in raw.columns[1:]]

    raw = raw.dropna(subset=["Date"])
    raw["Date"] = pd.to_datetime(raw["Date"].astype(str).str.replace("M", "-"), format="%Y-%m")
    raw = raw.set_index("Date").sort_index()
    for column in raw.columns:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")

    _pink_sheet_cache = raw
    return raw


def load_fred_series(series_id: str) -> pd.Series:
    """Scarica una serie FRED via REST API. Richiede FRED_API_KEY nell'ambiente."""
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise FredApiKeyMissing(
            "Variabile d'ambiente FRED_API_KEY non impostata. "
            "Registrati gratuitamente su https://fred.stlouisfed.org/docs/api/api_key.html "
            "e imposta la variabile prima di usare questa fonte dati."
        )

    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
    }
    try:
        response = requests.get(FRED_OBSERVATIONS_URL, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FredRequestError(f"Chiamata a FRED fallita: {exc}") from exc

    observations = response.json().get("observations", [])
    dates = [pd.to_datetime(o["date"]) for o in observations]
    values = [float(o["value"]) if o["value"] != "." else float("nan") for o in observations]
    series = pd.Series(values, index=pd.DatetimeIndex(dates), name=series_id).dropna()
    return series


def get_available_range(source: str, product_label: str) -> tuple:
    """Ritorna (data minima, data massima) disponibili per la combinazione scelta."""
    series = _load_raw_series(source, product_label)
    return series.index.min(), series.index.max()


def _load_raw_series(source: str, product_label: str) -> pd.Series:
    if source == "World Bank Pink Sheet":
        column = PINK_SHEET_PRODUCTS[product_label]
        df = load_pink_sheet_prices()
        return df[column].dropna()
    elif source == "FRED (PPI)":
        series_id = FRED_PRODUCTS[product_label]
        return load_fred_series(series_id)
    else:
        raise ValueError(f"Fonte dati sconosciuta: {source}")


def get_series(
    source: str,
    product_label: str,
    years_back: int,
    granularity: str,
    mode: str,
) -> pd.Series:
    """Punto d'ingresso unico usato dalla GUI per ottenere la serie da plottare."""
    series = _load_raw_series(source, product_label)

    end_date = series.index.max()
    start_date = end_date - pd.DateOffset(years=years_back)
    series = series[series.index >= start_date]

    rule = _RESAMPLE_RULE[granularity]
    if rule is not None:
        series = series.resample(rule).mean().dropna()

    if mode == "Variazione %":
        series = series.pct_change().dropna() * 100

    return series
