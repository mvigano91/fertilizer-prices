"""Caricamento e normalizzazione delle serie storiche di prezzo.

Due fonti disponibili:
- World Bank "Pink Sheet" (file Excel locale, prezzi mensili in $/mt): tutte le 71
  commodity del file sono esposte (non solo fertilizzanti), per poter correlare i
  fertilizzanti con materie prime collegate (es. gas naturale) o generiche.
- FRED (indici PPI mensili e alcune serie di prezzo, via API REST, richiede
  FRED_API_KEY): selezione curata di serie fertilizzanti, gas naturale, zolfo,
  agrochimici e cereali/oli e semi, vedi DATA_SOURCES_CATALOG.md per l'elenco
  completo di cosa e' disponibile e cosa e' stato scartato.
"""

import datetime
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
    "Cereali - Orzo*": "Barley",
    "Cereali - Mais": "Maize",
    "Cereali - Sorgo*": "Sorghum",
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
    "Alimentari - Gamberetti messicani*": "Shrimps, Mexican",
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
# Selezione curata (non tutte le serie FRED esistenti): gas naturale, zolfo, dettagli
# a monte per nutriente e indicatori lato domanda. Le voci "a monte" (ammoniaca/urea,
# acido fosforico, fosfati) sono categorizzate sotto il nutriente a cui appartengono
# (Azoto/Fosforo) invece di un generico "Settore", che non comunicava nulla di concreto
# — l'unica eccezione resta "Agrochimici", perche' quella singola voce e' davvero un
# aggregato dell'intero settore (azoto+fosforo+potassio+pesticidi insieme), non
# riconducibile a un solo nutriente. Vedi DATA_SOURCES_CATALOG.md per le serie scartate
# (duplicate o discontinuate) e per come aggiungerne altre in futuro.
FRED_PRODUCTS = {
    "Azoto - PPI Fertilizzanti Azotati": "PCU325311325311",
    "Azoto - PPI Urea*": "PCU325311325311A4",
    "Azoto - PPI Ammoniaca e Urea (a monte)": "PCU325311325311A",
    "Azoto - PPI Fertilizzanti organici": "PCU3253113253117",
    "Fosforo - PPI Fertilizzanti Fosfatici": "PCU325312325312",
    "Fosforo - PPI Acido fosforico e superfosfati": "PCU325312325312A",
    "Fosforo - PPI Fosfati (storico dal 1947)": "WPU065202",
    "Potassio - PPI Potassa (mining)*": "PCU212391212391",
    "Gas naturale - PPI Gas naturale": "WPU0531",
    "Gas naturale - PPI Gas naturale industriale": "WPU05532101",
    "Gas naturale - Prezzo spot Henry Hub": "MHHNGSP",
    "Zolfo - PPI Acido solforico": "PCU3251803251809",
    "Agrochimici - PPI Settore agrochimico (totale)": "PCU32533253",
    "Agricoltura - PPI Prodotti agricoli (generale)": "WPU01",
    "Cereali - PPI Mais (USA)": "WPU012202",
    "Oli e semi - PPI Soia (USA)": "WPU01830131",
    "Cereali - PPI Grano Hard Red Spring (USA)": "WPU01210102",
    "Cereali - PPI Grano Soft White (USA)": "WPU01210103",
    "Cereali - Prezzo mondiale Mais (IMF)": "PMAIZMTUSDM",
    "Oli e semi - Prezzo mondiale Soia (IMF)": "PSOYBUSDM",
    "Cereali - Prezzo mondiale Grano (IMF)": "PWHEAMTUSDM",
}

# Etichetta prodotto (stessa chiave di PINK_SHEET_PRODUCTS/FRED_PRODUCTS) -> (unita' di
# misura, range di date, descrizione breve). Mostrato in sidebar per le serie compilate.
# Range statico (non ricalcolato live) per evitare di richiamare l'API FRED ad ogni rerun
# di Streamlit solo per mostrare questa info: e' accurato al luglio 2026, la piccola deriva
# nel tempo e' un compromesso accettabile per un testo informativo (la validazione vera in
# validate_years/_validate_series usa invece data.get_available_range, sempre live).
PRODUCT_INFO = {
    "Azoto - Urea": ("$/mt", "1960-2026", "Urea prillata, prezzo spot f.o.b. Medio Oriente (Mar Nero fino al 2022)."),
    "Fosforo - DAP": ("$/mt", "1967-2026", "Fosfato biammonico (DAP), prezzo spot f.o.b. Golfo USA."),
    "Fosforo - TSP": ("$/mt", "1960-2026", "Superfosfato triplo (TSP), prezzo spot import Golfo USA."),
    "Fosforo - Phosphate rock": ("$/mt", "1960-2026", "Roccia fosfatica grezza, prezzo f.o.b. Nord Africa."),
    "Potassio - Cloruro di potassio (MOP)": ("$/mt", "1960-2026", "Cloruro di potassio granulare (MOP), prezzo CFR Brasile (f.o.b. Vancouver fino al 2020)."),
    "Energia - Petrolio greggio (media)": ("$/bbl", "1960-2026", "Media dei tre greggi di riferimento Brent/Dubai/WTI."),
    "Energia - Petrolio greggio Brent": ("$/bbl", "1960-2026", "Greggio Brent, benchmark del Mare del Nord."),
    "Energia - Petrolio greggio Dubai": ("$/bbl", "1960-2026", "Greggio Dubai, benchmark mediorientale/asiatico."),
    "Energia - Petrolio greggio WTI": ("$/bbl", "1982-2026", "Greggio WTI (West Texas Intermediate), benchmark USA."),
    "Energia - Carbone australiano": ("$/mt", "1970-2026", "Carbone termico, esportazione dal porto di Newcastle (Australia)."),
    "Energia - Carbone sudafricano": ("$/mt", "1984-2026", "Carbone termico, esportazione da Richards Bay (Sudafrica)."),
    "Energia - Gas naturale USA (Henry Hub)": ("$/mmbtu", "1960-2026", "Prezzo gas naturale USA, hub Henry Hub — principale materia prima per ammoniaca/urea."),
    "Energia - Gas naturale Europa (TTF)": ("$/mmbtu", "1960-2026", "Prezzo gas naturale Europa (hub TTF dal 2015)."),
    "Energia - GNL Giappone": ("$/mmbtu", "1977-2026", "Prezzo import di gas naturale liquefatto (GNL) in Giappone."),
    "Energia - Indice gas naturale": ("indice 2010=100", "1977-2026", "Indice composito dei tre prezzi gas naturale sopra (media Laspeyres)."),
    "Bevande - Cacao": ("$/kg", "1960-2026", "Prezzo internazionale del cacao in grani."),
    "Bevande - Caffe' Arabica": ("$/kg", "1960-2026", "Prezzo caffe' Arabica, la varieta' pregiata."),
    "Bevande - Caffe' Robusta": ("$/kg", "1960-2026", "Prezzo caffe' Robusta, varieta' piu' economica."),
    "Bevande - Te' (media 3 aste)": ("$/kg", "1960-2026", "Media dei prezzi te' alle tre aste principali (Mombasa, Colombo, Kolkata)."),
    "Bevande - Te' Colombo": ("$/kg", "1960-2026", "Prezzo te', asta di Colombo (Sri Lanka)."),
    "Bevande - Te' Kolkata": ("$/kg", "1960-2026", "Prezzo te', asta di Kolkata (India)."),
    "Bevande - Te' Mombasa": ("$/kg", "1960-2026", "Prezzo te', asta di Mombasa (Kenya)."),
    "Oli e semi - Olio di cocco": ("$/mt", "1960-2026", "Prezzo olio di cocco."),
    "Oli e semi - Arachidi": ("$/mt", "1980-2026", "Prezzo arachidi in guscio."),
    "Oli e semi - Farina di pesce": ("$/mt", "1979-2026", "Prezzo farina di pesce, usata come mangime animale."),
    "Oli e semi - Olio di arachidi": ("$/mt", "1960-2026", "Prezzo olio di arachidi."),
    "Oli e semi - Olio di palma": ("$/mt", "1960-2026", "Prezzo olio di palma."),
    "Oli e semi - Olio di palmisto": ("$/mt", "1996-2026", "Prezzo olio di palmisto (dal seme di palma)."),
    "Oli e semi - Soia": ("$/mt", "1960-2026", "Prezzo fagioli di soia."),
    "Oli e semi - Olio di soia": ("$/mt", "1960-2026", "Prezzo olio di soia."),
    "Oli e semi - Farina di soia": ("$/mt", "1960-2026", "Prezzo farina di soia, usata come mangime animale."),
    "Oli e semi - Olio di colza": ("$/mt", "2002-2026", "Prezzo olio di colza (canola)."),
    "Oli e semi - Olio di girasole": ("$/mt", "2002-2026", "Prezzo olio di girasole."),
    "Cereali - Orzo*": ("$/mt", "1960-2020", "Prezzo orzo. Discontinuata: dati solo fino ad agosto 2020."),
    "Cereali - Mais": ("$/mt", "1960-2026", "Prezzo mais, benchmark Golfo USA."),
    "Cereali - Sorgo*": ("$/mt", "1960-2020", "Prezzo sorgo. Discontinuata: dati solo fino ad agosto 2020."),
    "Cereali - Riso Thai 5%": ("$/mt", "1960-2026", "Prezzo riso thailandese, 5% di rotture."),
    "Cereali - Riso Thai 25%": ("$/mt", "1986-2026", "Prezzo riso thailandese, 25% di rotture."),
    "Cereali - Riso Thai A.1": ("$/mt", "1986-2026", "Prezzo riso thailandese, grado A.1 (parboiled)."),
    "Cereali - Riso Vietnamita 5%": ("$/mt", "2003-2026", "Prezzo riso vietnamita, 5% di rotture."),
    "Cereali - Grano USA SRW": ("$/mt", "1979-2026", "Prezzo grano USA tenero rosso invernale (Soft Red Winter)."),
    "Cereali - Grano USA HRW": ("$/mt", "1960-2026", "Prezzo grano USA duro rosso invernale (Hard Red Winter)."),
    "Alimentari - Banana Europa": ("$/kg", "1997-2026", "Prezzo banane, import Europa."),
    "Alimentari - Banana USA": ("$/kg", "1960-2026", "Prezzo banane, import USA."),
    "Alimentari - Arancia": ("$/kg", "1960-2026", "Prezzo arance."),
    "Alimentari - Manzo": ("$/kg", "1960-2026", "Prezzo carne bovina."),
    "Alimentari - Pollo": ("$/kg", "1960-2026", "Prezzo carne di pollo."),
    "Alimentari - Agnello": ("$/kg", "1971-2026", "Prezzo carne di agnello."),
    "Alimentari - Gamberetti messicani*": ("$/kg", "1960-2023", "Prezzo gamberetti messicani. Discontinuata: dati solo fino a ottobre 2023."),
    "Alimentari - Zucchero UE": ("$/kg", "1960-2026", "Prezzo zucchero, mercato UE."),
    "Alimentari - Zucchero USA": ("$/kg", "1960-2026", "Prezzo zucchero, mercato USA."),
    "Alimentari - Zucchero mondo": ("$/kg", "1960-2026", "Prezzo zucchero, mercato mondiale."),
    "Alimentari - Tabacco USA": ("$/mt", "1960-2026", "Valore unitario import tabacco USA. Discontinuata: dati solo fino ad aprile 2026."),
    "Legname - Tronchi Camerun": ("$/m3", "1970-2026", "Prezzo tronchi da esportazione, Camerun."),
    "Legname - Tronchi Malesia": ("$/m3", "1960-2026", "Prezzo tronchi da esportazione, Malesia."),
    "Legname - Legname segato Camerun": ("$/m3", "1970-2026", "Prezzo legname segato, Camerun."),
    "Legname - Legname segato Malesia": ("$/m3", "1960-2026", "Prezzo legname segato, Malesia."),
    "Legname - Compensato": ("cents/foglio", "1979-2026", "Prezzo compensato (plywood), per foglio."),
    "Materie prime - Cotone": ("$/kg", "1960-2026", "Prezzo cotone, indice Cotlook A."),
    "Materie prime - Gomma TSR20": ("$/kg", "1999-2026", "Prezzo gomma naturale, grado TSR20."),
    "Materie prime - Gomma RSS3": ("$/kg", "1960-2026", "Prezzo gomma naturale, grado RSS3."),
    "Metalli - Alluminio": ("$/mt", "1960-2026", "Prezzo alluminio, London Metal Exchange."),
    "Metalli - Minerale di ferro": ("$/dmtu", "1960-2026", "Prezzo minerale di ferro, spot CFR Cina."),
    "Metalli - Rame": ("$/mt", "1960-2026", "Prezzo rame, London Metal Exchange."),
    "Metalli - Piombo": ("$/mt", "1960-2026", "Prezzo piombo, London Metal Exchange."),
    "Metalli - Stagno": ("$/mt", "1960-2026", "Prezzo stagno, London Metal Exchange."),
    "Metalli - Nickel": ("$/mt", "1960-2026", "Prezzo nickel, London Metal Exchange."),
    "Metalli - Zinco": ("$/mt", "1960-2026", "Prezzo zinco, London Metal Exchange."),
    "Metalli preziosi - Oro": ("$/oz troy", "1960-2026", "Prezzo oro."),
    "Metalli preziosi - Platino": ("$/oz troy", "1960-2026", "Prezzo platino."),
    "Metalli preziosi - Argento": ("$/oz troy", "1960-2026", "Prezzo argento."),
    "Azoto - PPI Fertilizzanti Azotati": ("indice", "1975-2026", "Indice PPI settore fertilizzanti azotati (NAICS 325311), prodotto finito."),
    "Azoto - PPI Urea*": ("indice", "1959-2014", "Indice PPI produzione urea (dettaglio del settore azotati). Discontinuata: dati solo fino a dic 2014."),
    "Fosforo - PPI Fertilizzanti Fosfatici": ("indice", "1967-2026", "Indice PPI settore fertilizzanti fosfatici (NAICS 325312), prodotto finito."),
    "Potassio - PPI Potassa (mining)*": ("indice", "1984-2022", "Indice PPI estrazione potassa/soda/borati (NAICS 212391). Discontinuata: dati solo fino a dic 2022."),
    "Gas naturale - PPI Gas naturale": ("indice 1982=100", "1967-2026", "Indice PPI gas naturale (tutti gli usi), proxy del costo materia prima per urea/ammoniaca."),
    "Gas naturale - PPI Gas naturale industriale": ("indice", "1991-2026", "Indice PPI gas naturale per uso industriale, piu' vicino al costo reale per un impianto fertilizzanti."),
    "Gas naturale - Prezzo spot Henry Hub": ("$/mmbtu", "1997-2026", "Prezzo spot gas naturale USA, benchmark Henry Hub (fonte EIA, non un indice)."),
    "Azoto - PPI Ammoniaca e Urea (a monte)": ("indice", "2014-2026", "Indice PPI ammoniaca sintetica, acido nitrico, composti d'ammonio e urea — prodotti intermedi a monte del fertilizzante finito."),
    "Azoto - PPI Fertilizzanti organici": ("indice", "2003-2026", "Indice PPI fertilizzanti di origine organica (settore azotati)."),
    "Fosforo - PPI Acido fosforico e superfosfati": ("indice", "2009-2026", "Indice PPI acido fosforico, superfosfati e altri materiali fosfatici — prodotti intermedi a monte del fertilizzante fosfatico finito."),
    "Fosforo - PPI Fosfati (storico dal 1947)": ("indice 1982=100", "1947-2026", "Indice PPI commodity per i fosfati, classificazione alternativa con storico piu' lungo."),
    "Zolfo - PPI Acido solforico": ("indice dic 1982=100", "1973-2026", "Indice PPI acido solforico (NAICS 325180) — materia prima chiave per produrre acido fosforico, quindi DAP/TSP."),
    "Agrochimici - PPI Settore agrochimico (totale)": ("indice", "1984-2026", "Indice PPI dell'intero settore pesticidi+fertilizzanti+agrochimici (NAICS 3253), aggregato."),
    "Agricoltura - PPI Prodotti agricoli (generale)": ("indice 1982=100", "1913-2026", "Indice PPI generale dei prodotti agricoli USA (non solo cereali: anche bestiame, latticini, ecc.) — proxy della salute del settore agricolo/domanda di fertilizzanti."),
    "Cereali - PPI Mais (USA)": ("indice 1982=100", "1971-2026", "Indice PPI del mais USA."),
    "Oli e semi - PPI Soia (USA)": ("indice 1982=100", "1947-2026", "Indice PPI della soia USA."),
    "Cereali - PPI Grano Hard Red Spring (USA)": ("indice 1982=100", "1947-2026", "Indice PPI del grano Hard Red Spring USA."),
    "Cereali - PPI Grano Soft White (USA)": ("indice 1982=100", "1947-2026", "Indice PPI del grano Soft White USA."),
    "Cereali - Prezzo mondiale Mais (IMF)": ("$/mt", "1992-2026", "Prezzo mondiale del mais, fonte FMI (non un indice)."),
    "Oli e semi - Prezzo mondiale Soia (IMF)": ("$/mt", "1992-2026", "Prezzo mondiale della soia, fonte FMI (non un indice)."),
    "Cereali - Prezzo mondiale Grano (IMF)": ("$/mt", "1992-2026", "Prezzo mondiale del grano, fonte FMI (non un indice)."),
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

_fred_cache = {}


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


def pink_sheet_last_updated():
    """Data (locale) in cui il file Pink Sheet e' stato scaricato/aggiornato l'ultima volta
    su questa macchina (mtime del file), non la data dell'ultimo dato contenuto. None se il
    file non esiste ancora."""
    if not PINK_SHEET_PATH.exists():
        return None
    return datetime.datetime.fromtimestamp(PINK_SHEET_PATH.stat().st_mtime).date()


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
    """Scarica una serie FRED via REST API (con cache in memoria per processo — vedi
    _fred_cache). Richiede FRED_API_KEY nell'ambiente."""
    if series_id in _fred_cache:
        return _fred_cache[series_id]

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
    _fred_cache[series_id] = series
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


def get_all_series(source: str, years_back: int, granularity: str, mode: str) -> dict:
    """Carica tutte le serie di 'source' (es. l'intero catalogo World Bank Pink Sheet),
    una per ciascuna etichetta prodotto in SOURCES[source]. Salta silenziosamente i
    prodotti che risultano vuoti dopo il filtro/resample. Ritorna {label: pd.Series}."""
    result = {}
    for label in SOURCES[source]:
        series = get_series(source, label, years_back, granularity, mode)
        if not series.empty:
            result[label] = series
    return result
