"""Costruzione delle figure Plotly (grafico serie storiche e scatter di regressione).

Nessuna logica statistica qui: la regressione vive in regression.py, questo modulo si
limita a disegnare dati gia' calcolati. Usiamo Plotly (invece di matplotlib) perche' serve
interattivita' (hover con il valore nel punto) e ridimensionamento responsive del grafico
al contenitore, entrambi impossibili con un'immagine statica.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _ylabel(mode):
    return "Variazione %" if mode == "Variazione %" else "Prezzo / Indice"


def series_title(r):
    return r["formula"] if r["is_pad"] else f"{r['product']} — {r['source']}"


def _line_label(r):
    return f"{r['label']}: {series_title(r)}"


def build_series_figure(results):
    """Grafico delle serie storiche, con asse Y secondario per le serie assegnate a 'R'."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    left = [r for r in results if r["axis"] == "L"]
    right = [r for r in results if r["axis"] == "R"]

    for r in results:
        fig.add_trace(
            go.Scatter(
                x=r["series"].index, y=r["series"].values, mode="lines+markers",
                name=_line_label(r), marker=dict(size=5),
            ),
            secondary_y=(r["axis"] == "R"),
        )

    if left:
        modes = {r["mode"] for r in left}
        ylabel = _ylabel(left[0]["mode"]) if len(modes) == 1 else "Valore"
        fig.update_yaxes(title_text=ylabel, secondary_y=False)
    if right:
        modes = {r["mode"] for r in right}
        ylabel = _ylabel(right[0]["mode"]) if len(modes) == 1 else "Valore"
        fig.update_yaxes(title_text=ylabel, secondary_y=True)

    if len(results) == 1:
        fig.update_layout(title=series_title(results[0]))

    fig.update_layout(
        height=450,
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    return fig


def build_regression_figure(y_label, y_actual, y_fitted, dates):
    """Scatter valore-reale (Y) vs valore-fitted (asse X), con:
    - gradiente colore per recency (blu sbiadito = dati vecchi, rosso intenso = dati recenti);
    - il punto piu' recente evidenziato a parte (verde, marker a diamante);
    - la retta y = x disegnata come "retta di regressione".

    Nota: qui si plotta y_actual contro y_fitted, entrambi dallo stesso fit OLS. Per
    costruzione, i residui (y_actual - y_fitted) hanno covarianza zero con y_fitted; quindi
    la miglior retta di regressione di y_actual su y_fitted, calcolata sugli stessi dati,
    ha esattamente pendenza 1 e intercetta 0 — e' algebricamente la diagonale y = x. Per
    questo si disegna direttamente quella diagonale invece di rifare un secondo fit: sono
    la stessa retta.
    """
    n = len(dates)
    t = np.linspace(0, 1, n) if n > 1 else np.array([1.0])
    labels = [d.strftime("%Y-%m-%d") for d in dates]

    fig = go.Figure()

    if n > 1:
        fig.add_trace(go.Scatter(
            x=y_fitted.values[:-1], y=y_actual.values[:-1], mode="markers",
            marker=dict(
                color=t[:-1],
                colorscale=[[0, "rgba(70,110,230,0.55)"], [1, "rgba(220,40,40,0.95)"]],
                size=8, line=dict(width=0),
            ),
            text=labels[:-1],
            hovertemplate="Data: %{text}<br>Fitted: %{x:.3f}<br>Reale: %{y:.3f}<extra></extra>",
            name="Osservazioni",
            showlegend=False,
        ))

    fig.add_trace(go.Scatter(
        x=[y_fitted.values[-1]], y=[y_actual.values[-1]], mode="markers",
        marker=dict(color="rgb(0,180,60)", size=16, symbol="diamond"),
        text=[labels[-1]],
        hovertemplate="Ultimo dato (%{text})<br>Fitted: %{x:.3f}<br>Reale: %{y:.3f}<extra></extra>",
        name="Dato più recente",
    ))

    lo = min(float(y_actual.min()), float(y_fitted.min()))
    hi = max(float(y_actual.max()), float(y_fitted.max()))
    pad = (hi - lo) * 0.05 if hi > lo else 1.0
    lo, hi = lo - pad, hi + pad

    fig.add_trace(go.Scatter(
        x=[lo, hi], y=[lo, hi], mode="lines",
        line=dict(dash="dash", color="gray"),
        name="Retta di regressione (y = x)",
    ))

    fig.update_layout(
        width=560,
        height=560,
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis_title=f"{y_label} previsto dal modello",
        yaxis_title=f"{y_label} reale",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    # Quadrato vero: stessi limiti [lo, hi] su entrambi gli assi (non solo stessa scala per
    # unita'), cosi' la retta y = x e' davvero la bisettrice del riquadro, non la diagonale
    # di un rettangolo. width/height uguali sopra fanno si' che il riquadro renderizzato sia
    # anch'esso quadrato (altrimenti un contenitore largo "stirerebbe" il quadrato interno).
    # Stesso passo tra le tacche (dtick) su entrambi gli assi, cosi' hanno la stessa densita'
    # e la griglia forma dei quadrati invece che dei rettangoli.
    tick_step = _nice_tick_step(hi - lo)
    grid_style = dict(showgrid=True, gridcolor="rgba(128,128,128,0.25)")
    fig.update_xaxes(range=[lo, hi], dtick=tick_step, constrain="domain", **grid_style)
    fig.update_yaxes(
        range=[lo, hi], dtick=tick_step, scaleanchor="x", scaleratio=1,
        constrain="domain", **grid_style,
    )
    return fig


def _nice_tick_step(span, target_ticks=8):
    """Passo 'tondo' (1/2/5 * potenza di 10) per ottenere circa target_ticks tacche su span."""
    if span <= 0:
        return 1
    raw_step = span / target_ticks
    magnitude = 10 ** np.floor(np.log10(raw_step))
    residual = raw_step / magnitude
    if residual < 1.5:
        nice = 1
    elif residual < 3:
        nice = 2
    elif residual < 7:
        nice = 5
    else:
        nice = 10
    return nice * magnitude


def build_residuals_figure(dates, residuals):
    """Grafico dei residui (reale - fitted) nel tempo, con linea di riferimento a zero."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates, y=residuals.values,
        marker=dict(color="rgba(120,120,120,0.75)"),
        name="Residuo",
        hovertemplate="Data: %{x|%Y-%m-%d}<br>Residuo: %{y:.3f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        height=280,
        margin=dict(l=40, r=40, t=30, b=40),
        xaxis_title="Data",
        yaxis_title="Residuo (reale − fitted)",
        showlegend=False,
    )
    return fig


def build_correlation_heatmap(corr_df):
    """Heatmap Plotly della matrice di correlazione (corr_df: DataFrame quadrata, output
    di stats.correlation_matrix). Scala diverging centrata su 0, valori annotati in cella."""
    fig = go.Figure(data=go.Heatmap(
        z=corr_df.values,
        x=list(corr_df.columns),
        y=list(corr_df.index),
        zmin=-1, zmax=1,
        colorscale="RdBu_r",
        colorbar=dict(title="ρ"),
        text=np.round(corr_df.values, 2),
        texttemplate="%{text}",
        hovertemplate="%{y} vs %{x}: %{z:.3f}<extra></extra>",
    ))
    fig.update_layout(
        height=max(320, 60 * len(corr_df) + 100),
        margin=dict(l=40, r=40, t=30, b=40),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def build_rolling_stats_figure(label, title, series, rolling_df, window):
    """Grafico per una singola serie: valore originale (linea sottile), media mobile
    (linea in evidenza) e banda ±1 std mobile (area ombreggiata) attorno alla media."""
    fig = go.Figure()

    band_upper = rolling_df["mean"] + rolling_df["std"]
    band_lower = rolling_df["mean"] - rolling_df["std"]

    fig.add_trace(go.Scatter(
        x=rolling_df.index, y=band_upper, mode="lines",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=rolling_df.index, y=band_lower, mode="lines",
        line=dict(width=0), fill="tonexty",
        fillcolor="rgba(70,110,230,0.15)",
        name=f"±1 dev. std (finestra {window})", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=series.index, y=series.values, mode="lines",
        line=dict(color="rgba(120,120,120,0.6)", width=1),
        name=f"{label} (valore)",
    ))
    fig.add_trace(go.Scatter(
        x=rolling_df.index, y=rolling_df["mean"], mode="lines",
        line=dict(color="rgb(220,40,40)", width=2),
        name=f"Media mobile ({window})",
    ))

    fig.update_layout(
        title=title,
        height=280,
        margin=dict(l=40, r=40, t=40, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    return fig
