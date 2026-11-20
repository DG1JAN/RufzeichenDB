
!!! Dieses Projekt ist stark „Vibe Coded“ mit GitHub Copilot !!! Es kommt ohne jegliche Garantien und befindet sich in Arbeit (Work in Progress)!!

# Lokales Amateurfunk-Rufzeichenregister

`index.html` im Browser öffnen. Die Suche funktioniert ohne Installation,
Internetverbindung und lokalen Webserver. `rufzeichen-daten.js` muss neben der
HTML-Datei liegen. Ein Klick auf ein Rufzeichen öffnet die entsprechende Seite
der Original-PDF, sofern diese ebenfalls im Ordner liegt.

Die Suche akzeptiert Teilbegriffe, kombiniert mehrere Wörter und findet etwa
`Köln`, `Koln` und `Koeln`. Unter `Alle Felder` lassen sich auch Rufzeichen und
Ort in einer Abfrage kombinieren. Fehlt im Ergebnis ein Ort, ist im Datenexport
kein Ort zu diesem Eintrag hinterlegt. Die Anwendung zeigt keine Straßen oder
Hausnummern an.

## Dateien und Aktualisierung

- `rufzeichen.sqlite3`: lokale SQLite-Datenbank mit den Tabellen `eintrag`,
  `ort` und `metadaten`. Ein Eintrag kann mehrere Ortsangaben haben.
- `rufzeichen-daten.js`: aus demselben Import erzeugter Datenexport für den
  direkten Browserstart ohne Server.
- `rufzeichenliste_afu.pdf`: Originalquelle der Bundesnetzagentur.

Für eine neue Ausgabe im selben PDF-Layout die PDF im Ordner ersetzen und dort
mit Python 3.12 oder neuer ausführen:

```powershell
python -m pip install pdfplumber
python import_rufzeichen.py
```

Der Import überschreibt beide Datenexporte. Mit `python import_rufzeichen.py
--pruefen` lässt sich die PDF auswerten, ohne Datenexporte zu ändern. Nach einer
Aktualisierung die HTML-Seite neu laden. Bei abweichendem PDF-Layout können
Anpassungen am Import nötig sein; im Zweifel gilt die Original-PDF.
