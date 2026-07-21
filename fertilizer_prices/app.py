"""GUI Tkinter: serie storica prezzi fertilizzanti (Azoto / Fosforo / Potassio)."""

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import data


class SeriesControls:
    """Un set di controlli (fonte dati, prodotto, tipo di valore) per una serie storica."""

    def __init__(self, parent, title):
        self.frame = ttk.LabelFrame(parent, text=title, padding=8)

        ttk.Label(self.frame, text="Fonte dati").pack(anchor="w")
        self.source_var = tk.StringVar(value=list(data.SOURCES.keys())[0])
        self.source_combo = ttk.Combobox(
            self.frame, textvariable=self.source_var, values=list(data.SOURCES.keys()),
            state="readonly",
        )
        self.source_combo.pack(fill=tk.X, pady=(0, 8))
        self.source_combo.bind("<<ComboboxSelected>>", self._on_source_change)

        ttk.Label(self.frame, text="Prodotto").pack(anchor="w")
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(self.frame, textvariable=self.product_var, state="readonly")
        self.product_combo.pack(fill=tk.X, pady=(0, 8))
        self._refresh_product_options()

        ttk.Label(self.frame, text="Tipo di valore").pack(anchor="w")
        self.mode_var = tk.StringVar(value=data.MODES[0])
        ttk.Combobox(
            self.frame, textvariable=self.mode_var, values=data.MODES, state="readonly",
        ).pack(fill=tk.X)

    def _on_source_change(self, _event=None):
        self._refresh_product_options()

    def _refresh_product_options(self):
        products = list(data.SOURCES[self.source_var.get()].keys())
        self.product_combo["values"] = products
        if self.product_var.get() not in products:
            self.product_var.set(products[0])

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def pack_forget(self):
        self.frame.pack_forget()


class FertilizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Serie storiche prezzi fertilizzanti")
        self.root.geometry("1100x700")

        controls = ttk.Frame(root, padding=12)
        controls.pack(side=tk.LEFT, fill=tk.Y)

        chart_frame = ttk.Frame(root, padding=12)
        chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Serie 1 (sempre presente) ---
        self.series1 = SeriesControls(controls, "Serie 1")
        self.series1.pack(fill=tk.X, pady=(0, 10))

        # --- Attivazione Serie 2 (opzionale) ---
        self.second_series_var = tk.BooleanVar(value=False)
        self.second_series_check = ttk.Checkbutton(
            controls, text="Aggiungi seconda serie storica",
            variable=self.second_series_var, command=self._on_toggle_second_series,
        )
        self.second_series_check.pack(anchor="w", pady=(0, 10))

        self.series2 = SeriesControls(controls, "Serie 2")
        # self.series2 non viene "pack"-ata finche' non abilitata dal checkbox

        # --- Anni indietro (condiviso) ---
        ttk.Label(controls, text="Anni indietro").pack(anchor="w")
        self.years_var = tk.StringVar(value="10")
        self.years_entry = ttk.Entry(controls, textvariable=self.years_var)
        self.years_entry.pack(fill=tk.X, pady=(0, 10))

        # --- Granularita' (condivisa) ---
        ttk.Label(controls, text="Granularita'").pack(anchor="w")
        self.granularity_var = tk.StringVar(value=data.GRANULARITIES[0])
        ttk.Combobox(
            controls, textvariable=self.granularity_var, values=data.GRANULARITIES,
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
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _on_toggle_second_series(self):
        if self.second_series_var.get():
            self.series2.pack(fill=tk.X, pady=(0, 10), after=self.second_series_check)
        else:
            self.series2.pack_forget()

    def _validate_series(self, series_controls):
        try:
            min_date, max_date = data.get_available_range(
                series_controls.source_var.get(), series_controls.product_var.get(),
            )
        except data.FredApiKeyMissing as exc:
            return None, str(exc)
        except data.FredRequestError as exc:
            return None, str(exc)
        except FileNotFoundError:
            return None, "File dati World Bank Pink Sheet non trovato in fertilizer_prices/data/."

        max_years = (max_date - min_date).days // 365 + 1
        return max_years, None

    def _validate_inputs(self):
        years_text = self.years_var.get().strip()
        if not years_text.isdigit() or int(years_text) <= 0:
            return None, "Anni indietro deve essere un numero intero positivo."

        years_back = int(years_text)

        max_years1, error = self._validate_series(self.series1)
        if error:
            return None, error
        if years_back > max_years1:
            return None, f"Storico disponibile per Serie 1: al massimo {max_years1} anni."

        if self.second_series_var.get():
            max_years2, error = self._validate_series(self.series2)
            if error:
                return None, error
            if years_back > max_years2:
                return None, f"Storico disponibile per Serie 2: al massimo {max_years2} anni."

        return years_back, None

    def _on_refresh(self):
        years_back, error = self._validate_inputs()
        if error:
            self.error_var.set(error)
            return

        try:
            series1 = data.get_series(
                self.series1.source_var.get(),
                self.series1.product_var.get(),
                years_back,
                self.granularity_var.get(),
                self.series1.mode_var.get(),
            )
            series2 = None
            if self.second_series_var.get():
                series2 = data.get_series(
                    self.series2.source_var.get(),
                    self.series2.product_var.get(),
                    years_back,
                    self.granularity_var.get(),
                    self.series2.mode_var.get(),
                )
        except (data.FredApiKeyMissing, data.FredRequestError) as exc:
            self.error_var.set(str(exc))
            return

        self.error_var.set("")
        self._plot(series1, series2)

    @staticmethod
    def _plot_one(ax, series, series_controls):
        ax.grid(True, color="gray", alpha=0.3, linestyle="--", linewidth=0.7, zorder=0)
        ax.set_axisbelow(True)
        ax.plot(series.index, series.values, marker="o", markersize=3, zorder=3)
        ax.set_title(f"{series_controls.product_var.get()} — {series_controls.source_var.get()}")
        ylabel = "Variazione %" if series_controls.mode_var.get() == "Variazione %" else "Prezzo / Indice"
        ax.set_ylabel(ylabel)

    def _plot(self, series1, series2):
        self.figure.clear()
        if series2 is not None:
            ax1 = self.figure.add_subplot(211)
            ax2 = self.figure.add_subplot(212)
            self._plot_one(ax1, series1, self.series1)
            self._plot_one(ax2, series2, self.series2)
        else:
            ax1 = self.figure.add_subplot(111)
            self._plot_one(ax1, series1, self.series1)

        self.figure.autofmt_xdate()
        self.figure.tight_layout()
        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    FertilizerApp(root)
    root.mainloop()
