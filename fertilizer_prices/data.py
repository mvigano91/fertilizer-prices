"""Caricamento e normalizzazione delle serie storiche di prezzo.

Due fonti disponibili:
- World Bank "Pink Sheet" (file Excel locale, prezzi mensili in $/mt): tutte le 71
  commodity del file sono esposte (non solo fertilizzanti), per poter correlare i
  fertilizzanti con materie prime collegate (es. gas naturale) o generiche.
- FRED (indici PPI mensili e alcune serie di prezzo, via API REST, richiede
  FRED_API_KEY): selezione curata di serie fertilizzanti + gas naturale + settore +
  lato domanda, vedi DATA_SOURCES_CATALOG.md per l'elenco completo di cosa e'
  disponibile e cosa e' stato scartato.
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

# Etichetta prodotto (mostrata in GUI) -> colonna nel file Pink Sheet.
# Elenco completo delle 71 colonne del file, non solo fertilizzanti: vedi
# DATA_SOURCES_CATALOG.md per unita' di misura e range di date di ognuna.
PINK_SHEET_PRODUCTS = {
    "Azoto - Urea": "Urea",
    "Fosforo - DAP": "DAP",
    "Fosforo - TSP": "TSP",
    "Fosforo - Phosphate rock": "Phosphate rock",
    "Potassio - Cloruro di potassio (MOP)": "Potassium chloride",
    "Energia - Petrolio greggio (media)": "Crude oil, average",
    "Energia - Petrolio greggio Brent": "Crude oil, Brent",
    "Energia - Petrolio greggio Dubai": "Crude oil, Dubai",
    "Energia - Petrolio greggio WTI": "Crude oil, WTI",
    "Energia - Carbone australiano": "Coal, Australian",
    "Energia - Carbone sudafricano": "Coal, South African",
    "Energia - Gas naturale USA (Henry Hub)": "Natural gas, US",
    "Energia - Gas naturale Europa (TTF)": "Natural gas, Europe",
    "Energia - GNL Giappone": "Liquefied natural gas, Japan",
    "Energia - Indice gas naturale": "Natural gas index",
    "Bevande - Cacao": "Cocoa",
    "Bevande - Caffe' Arabica": "Coffee, Arabica",
    "Bevande - Caffe' Robusta": "Coffee, Robusta",
    "Bevande - Te' (media 3 aste)": "Tea, avg 3 auctions",
    "Bevande - Te' Colombo": "Tea, Colombo",
    "Bevande - Te' Kolkata": "Tea, Kolkata",
    "Bevande - Te' Mombasa": "Tea, Mombasa",
    "Oli e semi - Olio di cocco": "Coconut oil",
    "Oli e semi - Arachidi": "Groundnuts",
    "Oli e semi - Farina di pesce": "Fish meal",
    "Oli e semi - Olio di arachidi": "Groundnut oil",
    "Oli e semi - Olio di palma": "Palm oil",
    "Oli e semi - Olio di palmisto": "Palm kernel oil",
    "Oli e semi - Soia": "Soybeans",
    "Oli e semi - Olio di soia": "Soybean oil",
    "Oli e semi - Farina di soia": "Soybean meal",
    "Oli e semi - Olio di colza": "Rapeseed oil",
    "Oli e semi - Olio di girasole": "Sunflower oil",
    "Cereali - Orzo": "Barley",
    "Cereali - Mais": "Maize",
    "Cereali - Sorgo": "Sorghum",
    "Cereali - Riso Thai 5%": "Rice, Thai 5%",
    "Cereali - Riso Thai 25%": "Rice, Thai 25%",
    "Cereali - Riso Thai A.1": "Rice, Thai A.1",
    "Cereali - Riso Vietnamita 5%": "Rice, Viet Namese 5%",
    "Cereali - Grano USA SRW": "Wheat, US SRW",
    "Cereali - Grano USA HRW": "Wheat, US HRW",
    "Alimentari - Banana Europa": "Banana, Europe",
    "Alimentari - Banana USA": "Banana, US",
    "Alimentari - Arancia": "Orange",
    "Alimentari - Manzo": "Beef",
    "Alimentari - Pollo": "Chicken",
    "Alimentari - Agnello": "Lamb",
    "Alimentari - Gamberetti messicani": "Shrimps, Mexican",
    "Alimentari - Zucchero UE": "Sugar, EU",
    "Alimentari - Zucchero USA": "Sugar, US",
    "Alimentari - Zucchero mondo": "Sugar, world",
    "Alimentari - Tabacco USA": "Tobacco, US import u.v.",
    "Legname - Tronchi Camerun": "Logs, Cameroon",
    "Legname - Tronchi Malesia": "Logs, Malaysian",
    "Legname - Legname segato Camerun": "Sawnwood, Cameroon",
    "Legname - Legname segato Malesia": "Sawnwood, Malaysian",
    "Legname - Compensato": "Plywood",
    "Materie prime - Cotone": "Cotton, A Index",
    "Materie prime - Gomma TSR20": "Rubber, TSR20",
    "Materie prime - Gomma RSS3": "Rubber, RSS3",
    "Metalli - Alluminio": "Aluminum",
    "Metalli - Minerale di ferro": "Iron ore, cfr spot",
    "Metalli - Rame": "Copper",
    "Metalli - Piombo": "Lead",
    "Metalli - Stagno": "Tin",
    "Metalli - Nickel": "Nickel",
    "Metalli - Zinco": "Zinc",
    "Metalli preziosi - Oro": "Gold",
    "Metalli preziosi - Platino": "Platinum",
    "Metalli preziosi - Argento": "Silver",
}

# Etichetta prodotto (mostrata in GUI) -> series id FRED.
# Selezione curata (non tutte le serie FRED esistenti): gas naturale, dettagli di
# settore e indicatori lato domanda. Vedi DATA_SOURCES_CATALOG.md per le serie scartate
# (duplicate o discontinuate) e per come aggiungerne altre in futuro.
FRED_PRODUCTS = {
    "Azoto - PPI Fertilizzanti Azotati": "PCU325311325311",
    "Azoto - PPI Urea": "PCU325311325311A4",
    "Fosforo - PPI Fertilizzanti Fosfatici": "PCU325312325312",
    "Potassio - PPI Potassa (mining)": "PCU212391212391",
    "Gas naturale - PPI Gas naturale": "WPU0531",
    "Gas naturale - PPI Gas naturale industriale": "WPU05532101",
    "Gas naturale - Prezzo spot Henry Hub": "MHHNGSP",
    "Settore - PPI Agrochimici (totale settore)": "PCU32533253",
    "Settore - PPI Ammoniaca e Urea (a monte)": "PCU325311325311A",
    "Settore - PPI Fertilizzanti organici": "PCU3253113253117",
    "Settore - PPI Acido fosforico e superfosfati": "PCU325312325312A",
    "Settore - PPI Fosfati (storico dal 1947)": "WPU065202",
    "Domanda - PPI Prodotti agricoli (generale)": "WPU01",
    "Domanda - PPI Mais (USA)": "WPU012202",
    "Domanda - PPI Soia (USA)": "WPU01830131",
    "Domanda - PPI Grano Hard Red Spring (USA)": "WPU01210102",
    "Domanda - PPI Grano Soft White (USA)": "WPU01210103",
    "Domanda - Prezzo mondiale Mais (IMF)": "PMAIZMTUSDM",
    "Domanda - Prezzo mondiale Soia (IMF)": "PSOYBUSDM",
    "Domanda - Prezzo mondiale Grano (IMF)": "PWHEAMTUSDM",
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
