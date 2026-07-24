"""Sidebar UI, validazione e risoluzione delle serie storiche configurate dall'utente (S1..Sn).

Ogni serie e' o una serie "normale" (fonte dati + prodotto + tipo di valore, risolta via
data.get_series) o una serie "Pad" (una formula testuale, es. "S1 - S2", valutata usando le
altre serie gia' risolte come variabili). Questo modulo e' condiviso dalle diverse tab della
UI: risolve le serie una sola volta, il risultato viene riusato ovunque serva (grafico delle
serie storiche, tab di regressione, ecc.) senza rifare fetch dei dati.
"""

import streamlit as st

import data

# Numero massimo di variabili indipendenti X selezionabili per la tab di regressione.
# Fisso (non dipendente dal numero attuale di serie) cosi' le opzioni della select non
# cambiano quando si aggiungono/rimuovono serie, evitando che un valore gia' scelto (es.
# "X3") diventi non piu' valido tra le opzioni disponibili in un rerun successivo.
MAX_REGRESSION_X_SLOTS = 9

REGRESSION_ROLE_OPTIONS = ["—", "Y"] + [f"X{i}" for i in range(1, MAX_REGRESSION_X_SLOTS + 1)]

# Combina le due fonti in un unico catalogo per il dropdown "Prodotto", cosi' non serve
# piu' scegliere prima la fonte: la sigla nel nome (" - WBPS" / " - FRED") la rende comunque
# esplicita, e la ricerca testuale della selectbox trova tutto in un colpo solo.
_SOURCE_ABBREV = {"World Bank Pink Sheet": "WBPS", "FRED (PPI)": "FRED"}


def _build_product_catalog():
    catalog = {}
    for source, abbrev in _SOURCE_ABBREV.items():
        for label in data.SOURCES[source]:
            catalog[f"{label} - {abbrev}"] = (source, label)
    return dict(sorted(catalog.items()))


PRODUCT_CATALOG = _build_product_catalog()


def _default_regression_role(label):
    """S1 -> 'Y', S2 -> 'X1', S3 -> 'X2', ... (solo il default iniziale: se l'utente lo
    cambia in seguito, quella scelta resta perche' e' legata alla chiave del widget)."""
    n = int(label[1:])
    if n == 1:
        return "Y"
    x_index = n - 1
    if x_index <= MAX_REGRESSION_X_SLOTS:
        return f"X{x_index}"
    return "—"


def render_series_controls(label, first=False):
    """Disegna i controlli di una singola serie e ritorna il suo dict di definizione."""
    if not first:
        st.markdown('<div class="series-gap"></div>', unsafe_allow_html=True)
    col_label, col_axis, col_pad, col_role = st.columns([0.8, 1.3, 0.9, 1.3])
    with col_label:
        st.markdown(f"**{label}**")
    with col_axis:
        axis = st.segmented_control(
            "Asse", options=["L", "R"], default="L", key=f"axis_{label}",
            label_visibility="collapsed",
        )
    with col_pad:
        is_pad = st.checkbox("Pad", key=f"pad_{label}")
    with col_role:
        default_role_index = REGRESSION_ROLE_OPTIONS.index(_default_regression_role(label))
        regression_role = st.selectbox(
            "Ruolo regressione", REGRESSION_ROLE_OPTIONS, index=default_role_index,
            key=f"role_{label}", label_visibility="collapsed",
        )

    if is_pad:
        st.markdown('<div class="pad-formula-gap"></div>', unsafe_allow_html=True)
        formula = st.text_input(
            "Pad", key=f"formula_{label}", placeholder="es. S1 - S2, S1 * 100",
            label_visibility="collapsed",
        )
        return {
            "label": label, "axis": axis, "is_pad": True, "formula": formula, "mode": None,
            "regression_role": regression_role,
        }

    combined_label = st.selectbox(
        "Prodotto", list(PRODUCT_CATALOG.keys()),
        index=None, placeholder="Cerca un prodotto...", key=f"product_{label}",
    )
    source, product = PRODUCT_CATALOG[combined_label] if combined_label else (None, None)
    mode = st.selectbox("Tipo di valore", data.MODES, key=f"mode_{label}")
    return {
        "label": label, "axis": axis, "is_pad": False,
        "source": source, "product": product, "mode": mode,
        "regression_role": regression_role,
    }


def render_sidebar():
    """Disegna l'intera sidebar: parametri condivisi, lista serie, bottoni +/- e 'Aggiorna grafico'.

    Ritorna (years_text, granularity, series_list, refresh_clicked).
    """
    if "num_series" not in st.session_state:
        st.session_state["num_series"] = 1

    with st.sidebar:
        col_refresh_wb, col_last_updated = st.columns([1, 1])
        with col_refresh_wb:
            with st.container(key="pink_sheet_refresh_container"):
                if st.button(
                    "Aggiorna dati WBPS", key="refresh_pink_sheet", use_container_width=True,
                ):
                    with st.spinner("Scarico l'ultimo file Pink Sheet dal sito World Bank..."):
                        try:
                            data.refresh_pink_sheet_file()
                        except data.PinkSheetRefreshError as exc:
                            st.session_state["pink_sheet_refresh_error"] = str(exc)
                        else:
                            st.session_state["pink_sheet_refresh_error"] = None
                            st.session_state["pink_sheet_refresh_done"] = True
        with col_last_updated:
            with st.container(key="pink_sheet_date_container"):
                last_updated = data.pink_sheet_last_updated()
                if last_updated:
                    st.caption(f"Ultimo agg.: {last_updated:%d/%m/%Y}")

        if st.session_state.get("pink_sheet_refresh_error"):
            st.error(st.session_state["pink_sheet_refresh_error"])
        elif st.session_state.pop("pink_sheet_refresh_done", False):
            st.success("File Pink Sheet aggiornato.")

        refresh_top = st.button("Aggiorna grafico", type="primary", key="refresh_top", use_container_width=True)

        years_text = st.text_input("**Anni indietro**", value="10")
        granularity = st.selectbox("**Granularita'**", data.GRANULARITIES)

        st.divider()

        series_list = [
            render_series_controls(f"S{i}", first=(i == 1))
            for i in range(1, st.session_state["num_series"] + 1)
        ]

        st.markdown('<div class="series-gap"></div>', unsafe_allow_html=True)
        add_col, remove_col = st.columns(2)
        with add_col:
            if st.button("+ Aggiungi serie", use_container_width=True):
                st.session_state["num_series"] += 1
                st.rerun()
        with remove_col:
            if st.session_state["num_series"] > 1:
                if st.button("- Rimuovi ultima", use_container_width=True):
                    st.session_state["num_series"] -= 1
                    st.rerun()

        st.divider()
        refresh_bottom = st.button("Aggiorna grafico", type="primary", key="refresh_bottom")

        compiled = [s for s in series_list if not s["is_pad"] and s["product"]]
        if compiled:
            st.markdown('<div class="legend-gap"></div>', unsafe_allow_html=True)
            for s in compiled:
                abbrev = _SOURCE_ABBREV[s["source"]]
                unit, date_range, description = data.PRODUCT_INFO[s["product"]]
                st.markdown(
                    f'<div class="series-info"><b>{s["label"]}</b> — {s["product"]} ({abbrev}), '
                    f'{unit}, {date_range}<br>{description}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown('<div class="legend-gap"></div>', unsafe_allow_html=True)
        st.caption("Pad = operazione tra le serie. Es: S1-S2")
        st.caption("WBPS = World Bank Pink Sheet")
        st.caption("FRED = FRED (Federal Reserve Economic Data)")
        st.caption('Le voci con "PPI" sono indici di prezzo (base 100), non prezzi di mercato in $.')
        st.caption("\\* = serie storica non recente")

        st.markdown('<div class="legend-gap"></div>', unsafe_allow_html=True)
        st.caption("Categorie: " + ", ".join(_all_categories()))

    return years_text, granularity, series_list, refresh_top or refresh_bottom


def _all_categories():
    """Nomi di categoria (prefisso prima di ' - ' in ogni etichetta prodotto), uniti dalle
    due fonti e ordinati alfabeticamente. Derivato dai dizionari invece che scritto a mano
    cosi' resta corretto se in futuro si aggiungono o rimuovono prodotti/categorie."""
    labels = list(data.PINK_SHEET_PRODUCTS) + list(data.FRED_PRODUCTS)
    categories = {label.split(" - ", 1)[0] for label in labels}
    return sorted(categories)


def _validate_series(source, product):
    try:
        min_date, max_date = data.get_available_range(source, product)
    except data.FredApiKeyMissing as exc:
        return None, str(exc)
    except data.FredRequestError as exc:
        return None, str(exc)
    except FileNotFoundError:
        return None, "File dati World Bank Pink Sheet non trovato in fertilizer_prices/data/."

    max_years = (max_date - min_date).days // 365 + 1
    return max_years, None


def validate_years(years_text, series_list):
    if not years_text.strip().isdigit() or int(years_text) <= 0:
        return None, "Anni indietro deve essere un numero intero positivo."

    years_back = int(years_text)

    for s in series_list:
        if s["is_pad"]:
            if not s["formula"].strip():
                return None, f"Inserisci una formula per {s['label']} (es. S1 - S2)."
            continue
        if not s["product"]:
            return None, f"Seleziona un prodotto per {s['label']}."
        max_years, error = _validate_series(s["source"], s["product"])
        if error:
            return None, error
        if years_back > max_years:
            return None, f"Storico disponibile per {s['label']}: al massimo {max_years} anni."

    return years_back, None


def resolve_pad_formulas(pad_series, resolved):
    """Valuta le formule Pad (es. 'S1 - S2') usando le serie gia' risolte come variabili.

    Supporta anche formule Pad che si riferiscono ad altre serie Pad, risolvendole
    per iterazioni successive finche' non c'e' piu' progresso.
    """
    pending = list(pad_series)
    while pending:
        still_pending = []
        progressed = False
        for s in pending:
            try:
                value = eval(s["formula"], {"__builtins__": {}}, dict(resolved))
            except NameError:
                still_pending.append(s)
                continue
            except Exception as exc:
                raise ValueError(f"Errore nella formula di {s['label']}: {exc}") from exc
            if hasattr(value, "dropna"):
                value = value.dropna()
            resolved[s["label"]] = value
            progressed = True
        if not progressed:
            labels = ", ".join(s["label"] for s in still_pending)
            raise ValueError(
                f"Impossibile calcolare {labels}: la formula fa riferimento a una serie "
                "inesistente o c'e' un riferimento circolare."
            )
        pending = still_pending


def resolve_series(years_back, granularity, series_list):
    """Calcola tutte le serie (fetch dati per le normali, poi valuta le formule Pad).

    Puo' sollevare data.FredApiKeyMissing / data.FredRequestError / ValueError.
    """
    resolved = {}
    for s in series_list:
        if s["is_pad"]:
            continue
        resolved[s["label"]] = data.get_series(
            s["source"], s["product"], years_back, granularity, s["mode"],
        )

    resolve_pad_formulas([s for s in series_list if s["is_pad"]], resolved)

    return [{**s, "series": resolved[s["label"]]} for s in series_list]


def resolve_catalog_labels(years_back, granularity, combined_labels):
    """Risolve una lista di etichette combinate di PRODUCT_CATALOG in
    {etichetta_combinata: pd.Series}, usando data.get_series con mode="Valore assoluto".
    Salta silenziosamente le etichette vuote dopo fetch/resample. Puo' sollevare
    data.FredApiKeyMissing / data.FredRequestError / ValueError (non catturati qui)."""
    result = {}
    for combined_label in combined_labels:
        source, product = PRODUCT_CATALOG[combined_label]
        series = data.get_series(source, product, years_back, granularity, "Valore assoluto")
        if not series.empty:
            result[combined_label] = series
    return result


def parse_regression_roles(series_result):
    """Legge il campo 'regression_role' di ciascuna serie gia' risolta e determina Y/X.

    Ritorna (y_entry|None, x_entries, errors):
    - y_entry: il dict della serie con ruolo "Y" (None se nessuna o piu' di una).
    - x_entries: le serie con ruolo "X1"/"X2"/..., ordinate per numero crescente.
    - errors: lista di messaggi (Y duplicata, stesso slot X assegnato a piu' serie).
    """
    y_entries = [r for r in series_result if r["regression_role"] == "Y"]
    x_entries = [r for r in series_result if r["regression_role"].startswith("X")]

    errors = []
    if len(y_entries) > 1:
        dup = ", ".join(r["label"] for r in y_entries)
        errors.append(f"Più serie assegnate come Y: {dup}. Scegli una sola Y nella barra laterale.")

    slots = {}
    for r in x_entries:
        slots.setdefault(r["regression_role"], []).append(r["label"])
    for role, labels in slots.items():
        if len(labels) > 1:
            errors.append(f"Ruolo {role} assegnato a più serie: {', '.join(labels)}.")

    x_entries_sorted = sorted(x_entries, key=lambda r: int(r["regression_role"][1:]))
    y_entry = y_entries[0] if len(y_entries) == 1 else None

    return y_entry, x_entries_sorted, errors
