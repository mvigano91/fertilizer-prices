"""Statistiche descrittive, correlazione e volatilita' mobile tra serie storiche gia'
risolte. Nessuna dipendenza da Streamlit o da Plotly: puro calcolo con numpy/pandas, cosi'
e' riusabile e testabile indipendentemente dalla UI."""

import pandas as pd


def build_aligned_frame(series_result):
    """Allinea tutte le serie attive su un'unica DataFrame (join 'outer' sulle date),
    una colonna per serie, indicizzata per 'label' (S1, S2, ...).

    Usiamo 'outer' (non 'inner' come in regression.fit_multilinear_ols) perche'
    DataFrame.corr() gestisce gia' da sola i NaN a coppie: un inner join eager su tutte
    le serie insieme restringerebbe inutilmente il campione ogni volta che le serie hanno
    storici diversi (es. una serie discontinued '*' che finisce anni prima delle altre).
    """
    columns = {r["label"]: r["series"] for r in series_result}
    return pd.concat(columns, axis=1, join="outer").sort_index()


def correlation_matrix(frame):
    """Matrice di correlazione di Pearson tra le colonne di 'frame' (una per serie).
    pandas.DataFrame.corr() calcola pairwise, usando per ogni coppia (i, j) solo le date
    in cui entrambe le serie hanno un valore non-NaN."""
    return frame.corr(method="pearson")


def rolling_stats(series, window):
    """Media mobile e deviazione standard mobile di 'series' su una finestra di 'window'
    periodi. Ritorna una DataFrame con colonne ['mean', 'std'], stesso indice di 'series'
    (i primi window-1 punti sono NaN, comportamento standard di pandas .rolling())."""
    return pd.DataFrame({
        "mean": series.rolling(window).mean(),
        "std": series.rolling(window).std(),
    })


def percentile_of_last(series):
    """Percentile (0-100) dell'ultimo valore di 'series' rispetto all'intero storico
    della stessa serie. Equivalente a scipy.stats.percentileofscore(kind='mean') ma
    pandas-puro, per non aggiungere scipy come dipendenza. Se la serie e' costante
    (std == 0), il percentile e' per definizione 50."""
    if series.std() == 0:
        return 50.0
    return float(series.rank(pct=True, method="average").iloc[-1] * 100)


def descriptive_stats(series_result):
    """Tabella riassuntiva, una riga per serie: Media, Dev. std, Min, Max, Valore
    attuale, Percentile attuale (rispetto al proprio storico). Ogni serie usa il proprio
    storico completo, senza allineamento con le altre."""
    rows = []
    for r in series_result:
        s = r["series"].dropna()
        if s.empty:
            continue
        rows.append({
            "Serie": r["label"],
            "Descrizione": r["formula"] if r["is_pad"] else f"{r['product']} — {r['source']}",
            "Media": s.mean(),
            "Dev. std": s.std(),
            "Min": s.min(),
            "Max": s.max(),
            "Valore attuale": s.iloc[-1],
            "Percentile attuale": percentile_of_last(s),
        })
    return pd.DataFrame(rows).set_index("Serie")
