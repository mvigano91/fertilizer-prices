# Catalogo dati disponibili — World Bank Pink Sheet e FRED

Riferimento per capire cosa e' gia' esposto nell'app (`PINK_SHEET_PRODUCTS` / `FRED_PRODUCTS`
in `data.py`) e cosa si potrebbe ancora aggiungere in futuro. Le due fonti sono chiuse
(nessuna terza fonte integrata), ma ciascuna ne offre molto di piu' di quanto usato oggi.

Per aggiungere una nuova voce: World Bank basta aggiungere una riga a `PINK_SHEET_PRODUCTS`
con `"Etichetta": "Nome colonna esatto"` (il nome colonna deve combaciare con quello che
produce `load_pink_sheet_prices()` dopo la pulizia, cioe' senza `*`/`**` finali e senza spazi
in eccesso — la tabella sotto riporta gia' i nomi puliti). FRED richiede invece di verificare
prima che il series ID esista e sia mensile, es.:

```
python -c "import os, requests; r = requests.get('https://api.stlouisfed.org/fred/series', params={'series_id': 'XXXX', 'api_key': os.environ['FRED_API_KEY'], 'file_type': 'json'}); print(r.json())"
```

## World Bank Pink Sheet — tutte le 71 colonne (aggiornato luglio 2026)

Tutte esposte in `PINK_SHEET_PRODUCTS`, raggruppate per categoria come nel file originale.
Date = primo/ultimo mese con dato non nullo, sul file scaricato il 22/07/2026 (dati fino a
2026M06). Le colonne "discontinuate" hanno smesso di essere pubblicate ma restano nel file
con lo storico fino alla data di interruzione.

### Fertilizzanti (5/5 esposte)
| Colonna | Unita' | Range |
|---|---|---|
| Urea | $/mt | 1960-01 – 2026-06 |
| DAP | $/mt | 1967-01 – 2026-06 |
| TSP | $/mt | 1960-01 – 2026-06 |
| Phosphate rock | $/mt | 1960-01 – 2026-06 |
| Potassium chloride | $/mt | 1960-01 – 2026-06 |

### Energia (10/10 esposte)
| Colonna | Unita' | Range |
|---|---|---|
| Crude oil, average | $/bbl | 1960-01 – 2026-06 |
| Crude oil, Brent | $/bbl | 1960-01 – 2026-06 |
| Crude oil, Dubai | $/bbl | 1960-01 – 2026-06 |
| Crude oil, WTI | $/bbl | 1982-01 – 2026-06 |
| Coal, Australian | $/mt | 1970-01 – 2026-06 |
| Coal, South African | $/mt | 1984-01 – 2026-06 |
| Natural gas, US (Henry Hub) | $/mmbtu | 1960-01 – 2026-06 |
| Natural gas, Europe (TTF dal 2015) | $/mmbtu | 1960-01 – 2026-06 |
| Liquefied natural gas, Japan | $/mmbtu | 1977-01 – 2026-06 |
| Natural gas index | 2010=100 | 1977-01 – 2026-06 |

### Bevande (7/7 esposte)
| Colonna | Unita' | Range |
|---|---|---|
| Cocoa | $/kg | 1960-01 – 2026-06 |
| Coffee, Arabica | $/kg | 1960-01 – 2026-06 |
| Coffee, Robusta | $/kg | 1960-01 – 2026-06 |
| Tea, avg 3 auctions | $/kg | 1960-01 – 2026-06 |
| Tea, Colombo | $/kg | 1960-01 – 2026-06 |
| Tea, Kolkata | $/kg | 1960-01 – 2026-06 |
| Tea, Mombasa | $/kg | 1960-01 – 2026-06 |

### Oli e semi oleosi (11/11 esposte)
| Colonna | Unita' | Range |
|---|---|---|
| Coconut oil | $/mt | 1960-01 – 2026-06 |
| Groundnuts | $/mt | 1980-01 – 2026-06 |
| Fish meal | $/mt | 1979-01 – 2026-06 |
| Groundnut oil | $/mt | 1960-01 – 2026-06 |
| Palm oil | $/mt | 1960-01 – 2026-06 |
| Palm kernel oil | $/mt | 1996-01 – 2026-06 |
| Soybeans | $/mt | 1960-01 – 2026-06 |
| Soybean oil | $/mt | 1960-01 – 2026-06 |
| Soybean meal | $/mt | 1960-01 – 2026-06 |
| Rapeseed oil | $/mt | 2002-02 – 2026-06 |
| Sunflower oil | $/mt | 2002-02 – 2026-06 |

### Cereali (9/9 esposte)
| Colonna | Unita' | Range |
|---|---|---|
| Barley | $/mt | 1960-01 – 2020-08 (discontinuata) |
| Maize | $/mt | 1960-01 – 2026-06 |
| Sorghum | $/mt | 1960-01 – 2020-08 (discontinuata) |
| Rice, Thai 5% | $/mt | 1960-01 – 2026-06 |
| Rice, Thai 25% | $/mt | 1986-01 – 2026-06 |
| Rice, Thai A.1 | $/mt | 1986-01 – 2026-06 |
| Rice, Viet Namese 5% | $/mt | 2003-12 – 2026-06 |
| Wheat, US SRW | $/mt | 1979-01 – 2026-06 |
| Wheat, US HRW | $/mt | 1960-01 – 2026-06 |

### Alimentari (11/11 esposte)
| Colonna | Unita' | Range |
|---|---|---|
| Banana, Europe | $/kg | 1997-01 – 2026-06 |
| Banana, US | $/kg | 1960-01 – 2026-06 |
| Orange | $/kg | 1960-01 – 2026-06 |
| Beef | $/kg | 1960-01 – 2026-06 |
| Chicken | $/kg | 1960-01 – 2026-06 |
| Lamb | $/kg | 1971-01 – 2026-06 |
| Shrimps, Mexican | $/kg | 1960-01 – 2023-10 (discontinuata) |
| Sugar, EU | $/kg | 1960-01 – 2026-06 |
| Sugar, US | $/kg | 1960-01 – 2026-06 |
| Sugar, world | $/kg | 1960-01 – 2026-06 |
| Tobacco, US import u.v. | $/mt | 1960-01 – 2026-04 (discontinuata) |

### Legname (5/5 esposte)
| Colonna | Unita' | Range |
|---|---|---|
| Logs, Cameroon | $/m3 | 1970-01 – 2026-06 |
| Logs, Malaysian | $/m3 | 1960-01 – 2026-06 |
| Sawnwood, Cameroon | $/m3 | 1970-01 – 2026-06 |
| Sawnwood, Malaysian | $/m3 | 1960-01 – 2026-06 |
| Plywood | cents/sheet | 1979-01 – 2026-06 |

### Materie prime (3/3 esposte)
| Colonna | Unita' | Range |
|---|---|---|
| Cotton, A Index | $/kg | 1960-01 – 2026-06 |
| Rubber, TSR20 | $/kg | 1999-01 – 2026-06 |
| Rubber, RSS3 | $/kg | 1960-01 – 2026-06 |

### Metalli (7/7 esposte)
| Colonna | Unita' | Range |
|---|---|---|
| Aluminum | $/mt | 1960-01 – 2026-06 |
| Iron ore, cfr spot | $/dmtu | 1960-01 – 2026-06 |
| Copper | $/mt | 1960-01 – 2026-06 |
| Lead | $/mt | 1960-01 – 2026-06 |
| Tin | $/mt | 1960-01 – 2026-06 |
| Nickel | $/mt | 1960-01 – 2026-06 |
| Zinc | $/mt | 1960-01 – 2026-06 |

### Metalli preziosi (3/3 esposte)
| Colonna | Unita' | Range |
|---|---|---|
| Gold | $/troy oz | 1960-01 – 2026-06 |
| Platinum | $/troy oz | 1960-01 – 2026-06 |
| Silver | $/troy oz | 1960-01 – 2026-06 |

## FRED — serie verificate contro l'API reale

### Esposte in FRED_PRODUCTS

| Series ID | Titolo | Range | Categoria app |
|---|---|---|---|
| PCU325311325311 | Nitrogenous Fertilizer Manufacturing PPI | – 2026-06 | Azoto (gia' presente) |
| PCU325311325311A4 | Urea Manufacturing PPI | – 2026-06 | Azoto (gia' presente) |
| PCU325312325312 | Phosphatic Fertilizer Manufacturing PPI | – 2026-06 | Fosforo (gia' presente) |
| PCU212391212391 | Potash, Soda, and Borate Mineral Mining PPI | – 2026-06 | Potassio (gia' presente) |
| WPU0531 | PPI Commodity: Natural Gas | 1967 – 2026-06 | Gas naturale |
| WPU05532101 | PPI Commodity: Industrial Natural Gas | 1991 – 2026-06 | Gas naturale |
| MHHNGSP | Henry Hub Natural Gas Spot Price | 1997 – 2026-06 | Gas naturale |
| PCU32533253 | Pesticide, Fertilizer, and Other Agricultural Chemical Mfg PPI | 1984 – 2026-06 | Settore |
| PCU325311325311A | Nitrogenous Fert. Mfg: Ammonia, Nitric Acid, Ammonium Compounds, Urea | 2014 – 2026-06 | Settore |
| PCU3253113253117 | Nitrogenous Fert. Mfg: Fertilizer Materials of Organic Origin | 2003 – 2026-06 | Settore |
| PCU325312325312A | Phosphatic Fert. Mfg: Phosphoric Acid, Superphosphates | 2009 – 2026-06 | Settore |
| WPU065202 | PPI Commodity: Chemicals: Phosphates | 1947 – 2026-06 | Settore |
| WPU01 | PPI Commodity: Farm Products | 1913 – 2026-06 | Domanda |
| WPU012202 | PPI Commodity: Farm Products: Corn | 1971 – 2026-06 | Domanda |
| WPU01830131 | PPI Commodity: Farm Products: Soybeans | 1947 – 2026-06 | Domanda |
| WPU01210102 | PPI Commodity: Farm Products: Hard Red Spring Wheat | 1947 – 2026-06 | Domanda |
| WPU01210103 | PPI Commodity: Farm Products: Soft White Wheat | 1947 – 2026-06 | Domanda |
| PMAIZMTUSDM | Global price of Corn (IMF, $/mt) | 1992 – 2026-06 | Domanda |
| PSOYBUSDM | Global price of Soybeans (IMF, $/mt) | 1992 – 2026-06 | Domanda |
| PWHEAMTUSDM | Global price of Wheat (IMF, $/mt) | 1992 – 2026-06 | Domanda |

### Trovate ma NON aggiunte (disponibili in futuro se servono)

| Series ID | Titolo | Perche' scartata |
|---|---|---|
| WPU0652013A | Ammonia/Urea, "by Commodity" invece che "by Industry" | Duplicato di PCU325311325311A, stesso range |
| WPU0652026A | Acido fosforico, "by Commodity" | Duplicato di PCU325312325312A |
| WPU06520137 | Fertilizer Materials of Organic Origin, "by Commodity" | Duplicato di PCU3253113253117 |
| WPU061 | PPI Industrial Chemicals (troppo generico) | Fuori tema, copre tutta la chimica industriale |
| PCU325320325320 / PCU3253232532 | Pesticide and Other Agricultural Chemical Mfg | Pesticidi, non fertilizzanti |
| PCU3253203253201 | dettaglio pesticidi | Idem |
| PCU0183 | Farm Products: Oilseeds (aggregato) | Ridondante con WPU01830131 (Soybeans) gia' incluso |
| PCU212391212391P | Potash mining: Primary Products | **Discontinuata** (dati fino a 2022-12) |
| PCU212391212391S1 | Potash mining: Secondary Products | **Discontinuata**, storico brevissimo (2014-06 – 2016-02) |
| PCU2123912123913 | Other Nonmetallic Mineral Mining: Sodium Carbonates/Sulfates | **Discontinuata** (fino a 2022-03), fuori tema |
| PCU325311325311A1 | Ammonia/Nitric Acid/Ammonium Compounds (senza urea) | **Discontinuata** 2014-12, sostituita da PCU325311325311A |
| PCU3253113253111 | stessa serie, nome alternativo | **Discontinuata** 2014-12 |
| PCU3251803251803 | Other Basic Inorganic Chemical Mfg: Inorganic Acids | Fuori tema (chimica generica, non fertilizzanti) |
| PCU3251803251804 | Other Basic Inorganic Chemical Mfg: Sodium Hydroxide | Fuori tema |
| PCU325180325180811 | Sulfuric Acid | **Discontinuata** (fino a 2017-12) |
| PCU32518032518081 | Sulfuric and Other Inorganic Acids | **Discontinuata** (fino a 2017-12) |
| WPU0551 / WPU05512101 | Residential Natural Gas | Prezzo al consumatore residenziale, non industriale — meno rilevante come costo materia prima |

Nota granularita': ogni serie qui sopra e' stata verificata come mensile (`frequency_short: "M"`)
via `GET /fred/series`. FRED ospita anche serie giornaliere/settimanali/trimestrali (es. tassi
di interesse, indici di borsa), ma nessuna di quelle rilevanti per fertilizzanti/materie prime
agricole lo e' — la granularita' Mensile/Trimestrale/Annuale dell'app resta quindi valida anche
dopo questa espansione.
