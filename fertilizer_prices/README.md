# Serie storiche prezzi fertilizzanti

GUI Tkinter per visualizzare la serie storica del prezzo di Azoto, Fosforo e Potassio
(via i loro principali fertilizzanti quotati: Urea, DAP/TSP, cloruro di potassio),
da due fonti a scelta:

- **World Bank Pink Sheet** — prezzi di mercato reali in $/mt, letti da un file Excel
  incluso in `data/CMO-Historical-Data-Monthly.xlsx`.
- **FRED (PPI)** — indici di prezzo alla produzione USA, letti in tempo reale dalla
  API di FRED.

Entrambe le fonti forniscono dati **mensili**: la granularità selezionabile in GUI
(Mensile / Trimestrale / Annuale) è un aggregato di questi dati mensili, non un dato
realmente più fitto.

## Setup

```
pip install -r requirements.txt
```

Per usare la fonte FRED serve una API key gratuita:

1. Registrati su https://fred.stlouisfed.org/docs/api/api_key.html
2. Imposta la variabile d'ambiente `FRED_API_KEY` prima di avviare l'app.

## Avvio

```
python app.py
```
