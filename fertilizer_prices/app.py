"""GUI Tkinter: serie storica prezzi fertilizzanti (Azoto / Fosforo / Potassio)."""

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import data


class FertilizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Serie storiche prezzi fertilizzanti")
        self.root.geometry("1000x600")

        controls = ttk.Frame(root, padding=12)
        controls.pack(side=tk.LEFT, fill=tk.Y)

        chart_frame = ttk.Frame(root, padding=12)
        chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Fonte dati ---
        ttk.Label(controls, text="Fonte dati").pack(anchor="w")
        self.source_var = tk.StringVar(value=list(data.SOURCES.keys())[0])
        self.source_combo = ttk.Combobox(
            controls, textvariable=self.source_var, values=list(data.SOURCES.keys()),
            state="readonly",
        )
        self.source_combo.pack(fill=tk.X, pady=(0, 10))
        self.source_combo.bind("<<ComboboxSelected>>", self._on_source_change)

        # --- Prodotto ---
        ttk.Label(controls, text="Prodotto").pack(anchor="w")
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(
            controls, textvariable=self.product_var, state="readonly",
        )
        self.product_combo.pack(fill=tk.X, pady=(0, 10))
        self._refresh_product_options()

        # --- Anni indietro ---
        ttk.Label(controls, text="Anni indietro").pack(anchor="w")
        self.years_var = tk.StringVar(value="10")
        self.years_entry = ttk.Entry(controls, textvariable=self.years_var)
        self.years_entry.pack(fill=tk.X, pady=(0, 10))

        # --- Granularita' ---
        ttk.Label(controls, text="Granularita'").pack(anchor="w")
        self.granularity_var = tk.StringVar(value=data.GRANULARITIES[0])
        ttk.Combobox(
            controls, textvariable=self.granularity_var, values=data.GRANULARITIES,
            state="readonly",
        ).pack(fill=tk.X, pady=(0, 10))

        # --- Tipo di valore ---
        ttk.Label(controls, text="Tipo di valore").pack(anchor="w")
        self.mode_var = tk.StringVar(value=data.MODES[0])
        ttk.Combobox(
            controls, textvariable=self.mode_var, values=data.MODES,
            state="readonly",
        ).pack(fill=tk.X, pady=(0, 10))

        # --- Bottone ---
        self.refresh_button = ttk.Button(
            controls, text="Aggiorna grafico", command=self._on_refresh,
        )
        self.refresh_button.pack(fill=tk.X, pady=(10, 0))

        # --- Messaggio di errore ---
        self.error_var = tk.StringVar(value="")
        ttk.Label(
            controls, textvariable=self.error_var, foreground="red", wraplength=200,
        ).pack(fill=tk.X, pady=(10, 0))

        # --- Grafico ---
        self.figure = Figure(figsize=(6, 5))
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _on_source_change(self, _event=None):
        self._refresh_product_options()

    def _refresh_product_options(self):
        products = list(data.SOURCES[self.source_var.get()].keys())
        self.product_combo["values"] = products
        if self.product_var.get() not in products:
            self.product_var.set(products[0])

    def _validate_inputs(self):
        years_text = self.years_var.get().strip()
        if not years_text.isdigit() or int(years_text) <= 0:
            return None, "Anni indietro deve essere un numero intero positivo."

        years_back = int(years_text)

        try:
            min_date, max_date = data.get_available_range(
                self.source_var.get(), self.product_var.get(),
            )
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

    def _on_refresh(self):
        years_back, error = self._validate_inputs()
        if error:
            self.error_var.set(error)
            return

        try:
            series = data.get_series(
                self.source_var.get(),
                self.product_var.get(),
                years_back,
                self.granularity_var.get(),
                self.mode_var.get(),
            )
        except (data.FredApiKeyMissing, data.FredRequestError) as exc:
            self.error_var.set(str(exc))
            return

        self.error_var.set("")
        self._plot(series)

    def _plot(self, series):
        self.ax.clear()
        self.ax.plot(series.index, series.values, marker="o", markersize=3)
        self.ax.set_title(f"{self.product_var.get()} — {self.source_var.get()}")
        ylabel = "Variazione %" if self.mode_var.get() == "Variazione %" else "Prezzo / Indice"
        self.ax.set_ylabel(ylabel)
        self.figure.autofmt_xdate()
        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    FertilizerApp(root)
    root.mainloop()
