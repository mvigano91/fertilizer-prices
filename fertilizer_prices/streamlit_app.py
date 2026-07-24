"""App web (Streamlit): serie storica prezzi fertilizzanti (Azoto / Fosforo / Potassio)."""

import os

import streamlit as st

import charting
import data
import regression
import series_config
import stats

st.set_page_config(page_title="Serie storiche prezzi fertilizzanti", layout="wide")


def _style_descriptive_stats(desc_df):
    """Formattazione condivisa per le tabelle di statistiche descrittive: una cifra
    decimale per i valori in unita' originale, due per lo z-score, valori centrati, e un
    gradiente di colore sullo z-score (blu = storicamente economico, rosso =
    storicamente caro) — stessa scala RdBu gia' usata per la matrice di correlazione.
    vmin/vmax=-3/3 coprono la stragrande maggioranza dei casi (±3 deviazioni standard);
    valori piu' estremi restano semplicemente al colore massimo della scala."""
    return desc_df.style.format({
        "Media": "{:.1f}", "Dev. std": "{:.1f}", "Min": "{:.1f}",
        "Max": "{:.1f}", "Valore attuale": "{:.1f}",
        "Percentile attuale": "{:.1f}", "Z-score attuale": "{:.2f}",
    }).set_properties(**{"text-align": "center"}).background_gradient(
        cmap="RdBu_r", subset=["Z-score attuale"], vmin=-3, vmax=3,
    )


def _toggle_custom_item(label, checkbox_key):
    working = st.session_state.setdefault("stats_custom_working", set())
    if st.session_state[checkbox_key]:
        working.add(label)
    else:
        working.discard(label)


def _apply_select_all(filtered_labels, checkbox_key):
    """on_change della checkbox 'Seleziona tutto': propaga il suo nuovo stato a tutte le
    voci attualmente filtrate nell'insieme canonico stats_custom_working, prima che le
    singole checkbox vengano ridisegnate in questo stesso rerun."""
    working = st.session_state.setdefault("stats_custom_working", set())
    value = st.session_state[checkbox_key]
    for lbl in filtered_labels:
        if value:
            working.add(lbl)
        else:
            working.discard(lbl)


def _remove_custom_item(label):
    st.session_state.setdefault("stats_custom_working", set()).discard(label)


@st.dialog("Selezione personalizzata", width="large")
def _custom_data_dialog():
    """Checklist in stile filtro Excel: a sinistra i prodotti filtrabili per testo con
    una checkbox ciascuna, a destra l'elenco di quanto attualmente selezionato con una
    "x" per rimuovere singolarmente. La selezione "vera" e' un unico insieme esplicito
    (st.session_state["stats_custom_working"], un set), non lo stato delle singole
    checkbox: cosi' resta corretta anche quando il filtro cambia e nasconde/rimostra
    voci gia' scelte in una ricerca precedente. Ogni checkbox viene forzata a riflettere
    "stats_custom_working" ad ogni rerun (invece di fidarsi del suo stato residuo), e le
    interazioni dell'utente (tick singolo, "Seleziona tutto", "x") modificano solo
    quell'insieme tramite callback. "OK" copia la selezione corrente in
    st.session_state["stats_custom_selection"], che e' quanto legge il resto della tab."""
    working = st.session_state.setdefault(
        "stats_custom_working", set(st.session_state.get("stats_custom_selection", [])),
    )

    filter_text = st.text_input(
        "Cerca prodotto", key="stats_custom_filter", placeholder="es. fosforo, cereali...",
    )
    all_labels = list(series_config.PRODUCT_CATALOG.keys())
    needle = filter_text.strip().lower()
    filtered_labels = [lbl for lbl in all_labels if needle in lbl.lower()] if needle else all_labels

    select_all_key = "stats_custom_select_all"
    filtered_all_selected = bool(filtered_labels) and all(lbl in working for lbl in filtered_labels)
    st.session_state[select_all_key] = filtered_all_selected

    col_list, col_selected = st.columns([3, 2])

    with col_list:
        st.caption(f"{len(filtered_labels)} prodotti trovati")
        st.checkbox(
            f"Seleziona tutto ({len(filtered_labels)})",
            key=select_all_key,
            disabled=not filtered_labels,
            on_change=_apply_select_all,
            args=(filtered_labels, select_all_key),
        )
        with st.container(height=350, border=True):
            for lbl in filtered_labels:
                chk_key = f"stats_custom_chk__{lbl}"
                st.session_state[chk_key] = lbl in working
                st.checkbox(lbl, key=chk_key, on_change=_toggle_custom_item, args=(lbl, chk_key))

    selected = [lbl for lbl in all_labels if lbl in working]

    with col_selected:
        st.caption(f"Selezionati: {len(selected)}")
        with st.container(height=350, border=True):
            for lbl in selected:
                col_lbl, col_x = st.columns([5, 1])
                with col_lbl:
                    st.write(lbl)
                with col_x:
                    st.button(
                        "✕", key=f"stats_custom_remove__{lbl}",
                        on_click=_remove_custom_item, args=(lbl,),
                    )

    st.divider()
    col_ok, col_clear = st.columns(2)
    with col_ok:
        if st.button("OK", type="primary", use_container_width=True):
            st.session_state["stats_custom_selection"] = selected
            st.rerun()
    with col_clear:
        if st.button("Svuota selezione", use_container_width=True):
            working.clear()
            st.session_state["stats_custom_selection"] = []
            st.rerun()

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        font-size: 0.85rem;
    }
    section[data-testid="stSidebar"] > div:first-child {
        width: 380px !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
        gap: 0.05rem;
    }
    .series-gap {
        margin-top: 1.6rem;
    }
    .pad-formula-gap {
        margin-top: 1rem;
    }
    .legend-gap {
        margin-top: 1.8rem;
    }
    div.block-container {
        padding-top: 1.2rem;
    }
    h1 {
        font-size: 1.3rem;
        margin-bottom: 0.3rem;
    }
    .st-key-pink_sheet_refresh_container {
        margin-bottom: 0.8rem;
    }
    .st-key-pink_sheet_date_container {
        margin-top: 0.4rem;
    }
    .series-info {
        font-size: 0.8rem;
        margin-bottom: 0.6rem;
    }
    .st-key-pink_sheet_refresh_container button {
        background-color: #ffb3b3;
        border-color: #ffb3b3;
        color: #3a0000;
        font-size: 0.78rem;
        padding: 0.15rem 0.5rem;
        min-height: 0;
    }
    .st-key-pink_sheet_refresh_container button:hover {
        background-color: #ff9999;
        border-color: #ff9999;
        color: #3a0000;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    _fred_secret = st.secrets.get("FRED_API_KEY")
except Exception:
    _fred_secret = None
if _fred_secret and not os.environ.get("FRED_API_KEY"):
    os.environ["FRED_API_KEY"] = _fred_secret

st.title("Serie storiche prezzi fertilizzanti")

years_text, granularity, series_list, refresh = series_config.render_sidebar()

if refresh:
    years_back, error = series_config.validate_years(years_text, series_list)
    if error:
        st.session_state["chart_error"] = error
        st.session_state["series_result"] = None
    else:
        try:
            results = series_config.resolve_series(years_back, granularity, series_list)
        except (data.FredApiKeyMissing, data.FredRequestError, ValueError) as exc:
            st.session_state["chart_error"] = str(exc)
            st.session_state["series_result"] = None
        else:
            st.session_state["chart_error"] = None
            st.session_state["series_result"] = results

# Il grafico resta visibile (invariato) finche' non si preme di nuovo "Aggiorna grafico",
# anche se nel frattempo si cambia un controllo nella barra laterale.
chart_error = st.session_state.get("chart_error")
series_result = st.session_state.get("series_result")

tab_series, tab_regression, tab_stats = st.tabs(["Serie storiche", "Regressione", "Statistiche"])

with tab_series:
    if chart_error:
        st.error(chart_error)
    elif series_result:
        st.plotly_chart(charting.build_series_figure(series_result), use_container_width=True)

        st.divider()

        st.subheader("Statistiche mobili / volatilità")
        window = st.slider(
            "Finestra (numero di periodi)", min_value=3, max_value=36, value=12,
            key="rolling_window",
        )
        for r in series_result:
            s = r["series"].dropna()
            if len(s) < window:
                st.info(
                    f"{r['label']} ({charting.series_title(r)}): solo {len(s)} punti, "
                    f"insufficienti per una finestra di {window} periodi."
                )
                continue
            rolling_df = stats.rolling_stats(s, window)
            title = f"{r['label']}: {charting.series_title(r)}"
            st.plotly_chart(
                charting.build_rolling_stats_figure(r["label"], title, s, rolling_df, window),
                use_container_width=True,
            )

        st.divider()

        st.subheader("Statistiche descrittive")
        desc_df = stats.descriptive_stats(series_result)
        if desc_df.empty:
            st.info("Nessuna serie con dati disponibili.")
        else:
            st.dataframe(_style_descriptive_stats(desc_df), use_container_width=True)
            st.caption("Colore dello Z-score: 🔵 economico rispetto allo storico — 🔴 caro rispetto allo storico")
    else:
        st.info('Imposta i parametri nella barra laterale e premi "Aggiorna grafico".')

with tab_regression:
    if not series_result:
        st.info("Calcola prima le serie nella tab \"Serie storiche\".")
    else:
        y_entry, x_entries, role_errors = series_config.parse_regression_roles(series_result)

        if role_errors:
            for err in role_errors:
                st.error(err)
        elif y_entry is None:
            st.info(
                "Nella barra laterale, assegna il ruolo di regressione ad almeno due serie: "
                "una come \"Y\" e una o più come \"X1\", \"X2\", ..."
            )
        elif not x_entries:
            st.info(
                "Assegna almeno una serie come \"X1\", \"X2\", ... nella barra laterale "
                "(campo \"Ruolo regressione\" accanto a Pad)."
            )
        else:
            summary_parts = [f"**Y = {y_entry['label']}** ({charting.series_title(y_entry)})"]
            summary_parts += [
                f"**{r['regression_role']} = {r['label']}** ({charting.series_title(r)})"
                for r in x_entries
            ]
            st.markdown("  ·  ".join(summary_parts))

            try:
                coeffs, y_actual, y_fitted, r_squared = regression.fit_multilinear_ols(
                    y_entry["series"], [r["series"] for r in x_entries],
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                fig = charting.build_regression_figure(
                    y_entry["label"], y_actual, y_fitted, y_actual.index,
                )
                st.plotly_chart(fig, use_container_width=False)
                st.caption(
                    regression.format_equation(
                        y_entry["label"], [r["label"] for r in x_entries], coeffs,
                    )
                    + f"  —  R² = {r_squared:.3f}"
                )
                st.caption(
                    "La retta tratteggiata è y = x: coincide con la retta di regressione di "
                    "\"valore reale\" su \"valore fitted\" per costruzione OLS."
                )

                residuals = y_actual - y_fitted
                st.plotly_chart(
                    charting.build_residuals_figure(y_actual.index, residuals),
                    use_container_width=True,
                )

with tab_stats:
    st.subheader("Impostazioni")
    col_years, col_gran, col_btn = st.columns([1, 1, 1])
    with col_years:
        stats_years = st.number_input(
            "Anni indietro", min_value=1, value=10, step=1, key="stats_years",
        )
    with col_gran:
        stats_granularity = st.selectbox(
            "Granularità", data.GRANULARITIES, key="stats_granularity",
        )
    with col_btn:
        st.markdown("<div style='margin-top: 1.6rem'></div>", unsafe_allow_html=True)
        calc_clicked = st.button("Calcola", type="primary", key="stats_calc")

    col_source, col_custom, _col_spacer = st.columns([1, 1, 1])
    with col_source:
        stats_source = st.selectbox(
            "Fonte", list(data.SOURCES.keys()), key="stats_source",
        )
    with col_custom:
        st.markdown("<div style='margin-top: 1.6rem'></div>", unsafe_allow_html=True)
        custom_selection = st.session_state.get("stats_custom_selection", [])
        custom_button_label = (
            f"Custom data ({len(custom_selection)})" if custom_selection else "Custom data"
        )
        if st.button(custom_button_label, key="stats_custom_open", use_container_width=True):
            _custom_data_dialog()

    if custom_selection:
        fred_involved = any(
            series_config.PRODUCT_CATALOG[lbl][0] == "FRED (PPI)" for lbl in custom_selection
        )
        st.caption(
            f"Selezione personalizzata attiva: {len(custom_selection)} prodotti "
            "(ha priorità sulla Fonte selezionata sopra)."
        )
    else:
        fred_involved = stats_source == "FRED (PPI)"
        st.caption(
            f"Calcola su tutto il catalogo {stats_source} "
            f"({len(data.SOURCES[stats_source])} prodotti), indipendentemente dalle serie "
            "configurate nella barra laterale. Solo \"Valore assoluto\"."
        )

    if fred_involved:
        st.warning(
            "FRED richiede una chiamata HTTP live per ogni serie (nessuna cache): con molte "
            "serie FRED il calcolo può richiedere diversi secondi."
        )

    if calc_clicked:
        with st.spinner("Calcolo le serie..."):
            try:
                if custom_selection:
                    series_by_label = series_config.resolve_catalog_labels(
                        int(stats_years), stats_granularity, custom_selection,
                    )
                else:
                    series_by_label = data.get_all_series(
                        stats_source, int(stats_years), stats_granularity, "Valore assoluto",
                    )
            except (data.FredApiKeyMissing, data.FredRequestError, ValueError) as exc:
                st.session_state["stats_tab_error"] = str(exc)
                st.session_state["stats_tab_result"] = None
            else:
                st.session_state["stats_tab_error"] = None
                st.session_state["stats_tab_result"] = series_by_label

    # Il risultato resta visibile finche' non si preme di nuovo "Calcola", anche se nel
    # frattempo si cambiano i controlli sopra o quelli della barra laterale.
    stats_error = st.session_state.get("stats_tab_error")
    stats_result = st.session_state.get("stats_tab_result")

    st.divider()

    if stats_error:
        st.error(stats_error)
    elif stats_result is None:
        st.info('Imposta anni/granularità sopra e premi "Calcola".')
    elif len(stats_result) < 2:
        st.info("Dati insufficienti per calcolare una matrice di correlazione (servono almeno 2 serie con dati).")
    else:
        st.subheader("Matrice di correlazione")
        frame = stats.build_aligned_frame(stats_result)
        corr_df = stats.correlation_matrix(frame)
        if corr_df.isna().all().all():
            st.warning("Nessuna data in comune tra i prodotti: correlazione non calcolabile.")
        else:
            st.plotly_chart(charting.build_correlation_heatmap(corr_df), use_container_width=True)
            if corr_df.isna().any().any():
                st.caption(
                    "Nota: alcune coppie di prodotti non hanno date in comune sufficienti "
                    "(cella vuota/NaN)."
                )

        st.divider()

        st.subheader("Statistiche descrittive")
        desc_df = stats.descriptive_stats_by_label(stats_result)
        if desc_df.empty:
            st.info("Nessun prodotto con dati disponibili.")
        else:
            st.dataframe(
                _style_descriptive_stats(desc_df), use_container_width=True, height=600,
            )
            st.caption("Colore dello Z-score: 🔵 economico rispetto allo storico — 🔴 caro rispetto allo storico")
