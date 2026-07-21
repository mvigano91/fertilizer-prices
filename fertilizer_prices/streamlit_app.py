"""App web (Streamlit): serie storica prezzi fertilizzanti (Azoto / Fosforo / Potassio)."""

import os

import matplotlib.pyplot as plt
import streamlit as st

import data

st.set_page_config(page_title="Serie storiche prezzi fertilizzanti", layout="wide")

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        font-size: 0.85rem;
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

if "num_series" not in st.session_state:
    st.session_state["num_series"] = 1


def _series_controls(label, first=False):
    if not first:
        st.markdown('<div class="series-gap"></div>', unsafe_allow_html=True)
    col_label, col_axis, col_pad = st.columns([1, 2, 1])
    with col_label:
        st.markdown(f"**{label}**")
    with col_axis:
        axis = st.segmented_control(
            "Asse", options=["L", "R"], default="L", key=f"axis_{label}",
            label_visibility="collapsed",
        )
    with col_pad:
        is_pad = st.checkbox("Pad", key=f"pad_{label}")

    if is_pad:
        formula = st.text_input(
            "Pad", key=f"formula_{label}", placeholder="es. S1 - S2, S1 * 100",
            label_visibility="collapsed",
        )
        return {"label": label, "axis": axis, "is_pad": True, "formula": formula, "mode": None}

    source = st.selectbox("Fonte dati", list(data.SOURCES.keys()), key=f"source_{label}")
    product = st.selectbox("Prodotto", list(data.SOURCES[source].keys()), key=f"product_{label}")
    mode = st.selectbox("Tipo di valore", data.MODES, key=f"mode_{label}")
    return {
        "label": label, "axis": axis, "is_pad": False,
        "source": source, "product": product, "mode": mode,
    }


with st.sidebar:
    years_text = st.text_input("**Anni indietro**", value="10")
    granularity = st.selectbox("**Granularita'**", data.GRANULARITIES)

    st.divider()

    series_list = [
        _series_controls(f"S{i}", first=(i == 1))
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
    refresh = st.button("Aggiorna grafico", type="primary")


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


def _validate_years(years_text, series_list):
    if not years_text.strip().isdigit() or int(years_text) <= 0:
        return None, "Anni indietro deve essere un numero intero positivo."

    years_back = int(years_text)

    for s in series_list:
        if s["is_pad"]:
            if not s["formula"].strip():
                return None, f"Inserisci una formula per {s['label']} (es. S1 - S2)."
            continue
        max_years, error = _validate_series(s["source"], s["product"])
        if error:
            return None, error
        if years_back > max_years:
            return None, f"Storico disponibile per {s['label']}: al massimo {max_years} anni."

    return years_back, None


def _ylabel(mode):
    return "Variazione %" if mode == "Variazione %" else "Prezzo / Indice"


def _series_title(r):
    return r["formula"] if r["is_pad"] else f"{r['product']} — {r['source']}"


def _line_label(r):
    return f"{r['label']}: {_series_title(r)}"


def _plot_results(ax_left, results):
    """Disegna tutte le serie, smistando ciascuna sull'asse sinistro o destro in base a 'axis'."""
    ax_left.grid(True, color="gray", alpha=0.3, linestyle="--", linewidth=0.7, zorder=0)
    ax_left.set_axisbelow(True)

    left = [r for r in results if r["axis"] == "L"]
    right = [r for r in results if r["axis"] == "R"]

    lines, labels = [], []

    for i, r in enumerate(left):
        line, = ax_left.plot(
            r["series"].index, r["series"].values, marker="o", markersize=3, zorder=3,
            color=f"C{i}", label=_line_label(r),
        )
        lines.append(line)
        labels.append(line.get_label())
    if left:
        modes = {r["mode"] for r in left}
        ax_left.set_ylabel(_ylabel(left[0]["mode"]) if len(modes) == 1 else "Valore")

    if right:
        ax_right = ax_left.twinx()
        for i, r in enumerate(right):
            line, = ax_right.plot(
                r["series"].index, r["series"].values, marker="o", markersize=3, zorder=3,
                color=f"C{len(left) + i}", label=_line_label(r),
            )
            lines.append(line)
            labels.append(line.get_label())
        modes = {r["mode"] for r in right}
        ax_right.set_ylabel(_ylabel(right[0]["mode"]) if len(modes) == 1 else "Valore")

    if len(results) == 1:
        ax_left.set_title(_series_title(results[0]))

    ax_left.legend(lines, labels, loc="best")


def _resolve_pad_formulas(pad_series, resolved):
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


if refresh:
    years_back, error = _validate_years(years_text, series_list)
    if error:
        st.session_state["chart_error"] = error
        st.session_state["chart_result"] = None
    else:
        try:
            resolved = {}
            for s in series_list:
                if s["is_pad"]:
                    continue
                resolved[s["label"]] = data.get_series(
                    s["source"], s["product"], years_back, granularity, s["mode"],
                )

            _resolve_pad_formulas([s for s in series_list if s["is_pad"]], resolved)

            results = [{**s, "series": resolved[s["label"]]} for s in series_list]
        except (data.FredApiKeyMissing, data.FredRequestError) as exc:
            st.session_state["chart_error"] = str(exc)
            st.session_state["chart_result"] = None
        except ValueError as exc:
            st.session_state["chart_error"] = str(exc)
            st.session_state["chart_result"] = None
        else:
            st.session_state["chart_error"] = None
            st.session_state["chart_result"] = results

# Il grafico resta visibile (invariato) finche' non si preme di nuovo "Aggiorna grafico",
# anche se nel frattempo si cambia un controllo nella barra laterale.
chart_error = st.session_state.get("chart_error")
chart_result = st.session_state.get("chart_result")

if chart_error:
    st.error(chart_error)
elif chart_result:
    fig, ax1 = plt.subplots(figsize=(10, 5))
    _plot_results(ax1, chart_result)
    fig.autofmt_xdate()
    fig.tight_layout()
    st.pyplot(fig)
else:
    st.info('Imposta i parametri nella barra laterale e premi "Aggiorna grafico".')
