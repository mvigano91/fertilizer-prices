"""App web (Streamlit): serie storica prezzi fertilizzanti (Azoto / Fosforo / Potassio)."""

import os

import matplotlib.pyplot as plt
import streamlit as st

import data

st.set_page_config(page_title="Serie storiche prezzi fertilizzanti", layout="wide")

try:
    _fred_secret = st.secrets.get("FRED_API_KEY")
except Exception:
    _fred_secret = None
if _fred_secret and not os.environ.get("FRED_API_KEY"):
    os.environ["FRED_API_KEY"] = _fred_secret

st.title("Serie storiche prezzi fertilizzanti")

with st.sidebar:
    source = st.selectbox("Fonte dati", list(data.SOURCES.keys()))
    product = st.selectbox("Prodotto", list(data.SOURCES[source].keys()))
    years_text = st.text_input("Anni indietro", value="10")
    granularity = st.selectbox("Granularita'", data.GRANULARITIES)
    mode = st.selectbox("Tipo di valore", data.MODES)
    refresh = st.button("Aggiorna grafico", type="primary")


def _validate_years(years_text):
    if not years_text.strip().isdigit() or int(years_text) <= 0:
        return None, "Anni indietro deve essere un numero intero positivo."

    years_back = int(years_text)
    try:
        min_date, max_date = data.get_available_range(source, product)
    except data.FredApiKeyMissing as exc:
        return None, str(exc)
    except data.FredRequestError as exc:
        return None, str(exc)
    except FileNotFoundError:
        return None, "File dati World Bank Pink Sheet non trovato in fertilizer_prices/data/."

    max_years = (max_date - min_date).days // 365 + 1
    if years_back > max_years:
        return None, f"Storico disponibile per questo prodotto: al massimo {max_years} anni."

    return years_back, None


if refresh:
    years_back, error = _validate_years(years_text)
    if error:
        st.error(error)
    else:
        try:
            series = data.get_series(source, product, years_back, granularity, mode)
        except (data.FredApiKeyMissing, data.FredRequestError) as exc:
            st.error(str(exc))
        else:
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.grid(True, color="gray", alpha=0.3, linestyle="--", linewidth=0.7, zorder=0)
            ax.set_axisbelow(True)
            ax.plot(series.index, series.values, marker="o", markersize=3, zorder=3)
            ax.set_title(f"{product} — {source}")
            ylabel = "Variazione %" if mode == "Variazione %" else "Prezzo / Indice"
            ax.set_ylabel(ylabel)
            fig.autofmt_xdate()
            st.pyplot(fig)
else:
    st.info('Imposta i parametri nella barra laterale e premi "Aggiorna grafico".')
