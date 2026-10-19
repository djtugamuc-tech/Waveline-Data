# Waveline-Data

Öffentlicher Senderkatalog für die [Waveline](https://github.com/djtugamuc-tech/Waveline)-Radio-App. Dieses Repository ist die **kanonische Datenquelle**: Es erzeugt täglich einen validierten Snapshot aus [Radio Browser](https://www.radio-browser.info/) und liefert ihn über GitHub Pages aus.

## Auslieferung

GitHub Pages: `https://djtugamuc-tech.github.io/Waveline-Data/`

- `index.json` — `updatedAt` und je Land `file`, `count`, `sha256`
- `stations_PT.json`, `stations_ES.json`, `stations_FR.json`, `stations_NL.json`, `stations_CH.json`, `stations_DE.json`

Nur Sender-Metadaten und Logo-URLs. Keine Logo- oder Audiodateien werden gespeichert oder weiterverteilt.

## Pipeline

`scripts/fetch_stations.py` nutzt ausschließlich die Python-Standardbibliothek. Es löst `all.api.radio-browser.info` auf, mischt die Server, fragt pro Land bis zu 500 Sender nach Klickzahl ab und behält nur funktionierende Einträge (`lastcheckok == 1`) mit eindeutiger Stream-URL. Bei einem Teilfehler wird nichts geschrieben; unveränderte Daten behalten Zeitstempel und Hashes.

Der Workflow `.github/workflows/update-stations.yml` läuft täglich (04:23 UTC) sowie manuell, committet geänderte Daten und veröffentlicht sie auf Pages.

## Test

```bash
python -m unittest discover -s scripts -v
```

## Lizenz

MIT, siehe `LICENSE`.
