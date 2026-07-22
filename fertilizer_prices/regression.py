"""Regressione lineare multipla (OLS) tra serie storiche gia' risolte.

Nessuna dipendenza da Streamlit o da Plotly: puro calcolo con numpy/pandas, cosi' e'
riusabile e testabile indipendentemente dalla UI.
"""

import numpy as np
import pandas as pd


def fit_multilinear_ols(y, x_list):
    """Stima Y = a1*X1 + a2*X2 + ... + c via minimi quadrati (numpy.linalg.lstsq).

    Allinea Y e tutte le X sulle date in comune (join 'inner'), scartando eventuali NaN
    residui. Ritorna (coeffs, y_actual, y_fitted, r_squared):
    - coeffs: array numpy, un valore per ciascuna X (nello stesso ordine di x_list) seguito
      dall'intercetta come ultimo elemento.
    - y_actual / y_fitted: pd.Series allineate sullo stesso DatetimeIndex (le date comuni).
    """
    columns = {"y": y}
    x_names = [f"x{i}" for i in range(1, len(x_list) + 1)]
    for name, series in zip(x_names, x_list):
        columns[name] = series

    df = pd.concat(columns, axis=1, join="inner").dropna().sort_index()

    n_params = len(x_list) + 1  # + intercetta
    if len(df) < n_params + 1:
        raise ValueError(
            f"Dati insufficienti per la regressione dopo l'allineamento delle date: "
            f"solo {len(df)} punti in comune."
        )

    design = np.column_stack([df[x_names].values, np.ones(len(df))])
    target = df["y"].values

    coeffs, *_ = np.linalg.lstsq(design, target, rcond=None)
    fitted = design @ coeffs

    residuals = target - fitted
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((target - target.mean()) ** 2))
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    y_actual = pd.Series(target, index=df.index, name="y_actual")
    y_fitted = pd.Series(fitted, index=df.index, name="y_fitted")

    return coeffs, y_actual, y_fitted, r_squared


def format_equation(y_label, x_labels, coeffs):
    """Es. 'S1 = 0.83*S2 + -12.10*S3 + 45.20'."""
    terms = [f"{coeff:.3g}*{label}" for label, coeff in zip(x_labels, coeffs[:-1])]
    intercept = coeffs[-1]
    return f"{y_label} = " + " + ".join(terms) + f" + {intercept:.3g}"
