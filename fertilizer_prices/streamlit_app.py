"""App web (Streamlit): serie storica prezzi fertilizzanti (Azoto / Fosforo / Potassio)."""

import os

import streamlit as st

import charting
import data
import regression
import series_config

st.set_page_config(page_title="Serie storiche prezzi fertilizzanti", layout="wide")

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        font-size: 0.85rem;
    }
    section[data-testid="stSidebar"] > div:first-child {
        width: 380px;
    }
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
        gap: 0.05rem;
    }
    .series-gap {
        margin-top: 1.6rem;
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

tab_series, tab_regression = st.tabs(["Serie storiche", "Regressione"])

with tab_series:
    if chart_error:
        st.error(chart_error)
    elif series_result:
        st.plotly_chart(charting.build_series_figure(series_result), use_container_width=True)
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
