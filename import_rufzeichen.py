import argparse
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

import pdfplumber


ENTRY = re.compile(r"^([A-Z]{1,3}\d[A-Z0-9]{1,12}(?:/[A-Z0-9]+)?),\s*([AEN]),\s*(.*)$")
POSTAL_PLACE = re.compile(r"(?:^|,\s*)(?:[A-Z]{1,3}[- ]?)?(\d{4,5})\s+([^,;]+)")
SECTION = re.compile(r"^[1-9]\s+Liste der Rufzeichen|^1\s+Liste der personengebundenen")
FOOTER = re.compile(r"Seite\s+\d+$")
SITE_DETAIL = re.compile(r"^\s*(?:Flur\b|(?:ESA\s+)?Satellit(?:e)?\b)", re.IGNORECASE)
COLUMN_STARTS = (70.9, 226.8, 382.8)


def page_lines(page):
    columns = [{}, {}, {}]
    for word in page.extract_words():
        left, top = word["x0"], word["top"]
        if not (45 <= top < 800 and left >= 68):
            continue
        column = sum(left >= start - 1 for start in COLUMN_STARTS[1:])
        columns[column].setdefault(round(top, 1), []).append((left, word["text"]))
    for lines in columns:
        for top, words in sorted(lines.items()):
            words.sort()
            text = " ".join(word for _, word in words)
            if not (top >= 790 and FOOTER.fullmatch(text)):
                yield top, words[0][0], text


def record(callsign, licence, lines, page_number):
    text = " ".join(lines).replace("\u00ad", "")
    text = re.sub(r"- (?=\w)", "-", text)
    name, _, address = text.partition(";")
    first, comma, rest = name.partition(",")
    if comma and (POSTAL_PLACE.search(rest.strip()) or SITE_DETAIL.match(rest)):
        name, _, address = first, comma, text.split(",", 1)[1]
    places = []
    for match in POSTAL_PLACE.finditer(address.strip()):
        place = (match[1], match[2].strip())
        if place not in places:
            places.append(place)
    return callsign, licence, name.strip(" ,"), places, page_number


def extract(source):
    rows = []
    current = None
    unexpected = Counter()
    with pdfplumber.open(source) as pdf:
        cover = pdf.pages[0].extract_text() or ""
        date = re.search(r"\bvom\s+(\d{1,2}\.\s+\w+\s+\d{4})", cover)
        for page in pdf.pages[5:]:
            lines = list(page_lines(page))
            page_number = page.page_number
            page.close()
            if not any(ENTRY.match(text) for _, _, text in lines):
                if current:
                    rows.append(record(*current))
                    current = None
                continue
            for _, left, text in lines:
                at_start = any(abs(left - start) < 1 for start in COLUMN_STARTS)
                match = ENTRY.match(text) if at_start else None
                if match or SECTION.match(text):
                    if current:
                        rows.append(record(*current))
                    current = (match[1], match[2], [match[3]], page_number) if match else None
                elif current:
                    current[2].append(text)
                    if at_start and re.match(r"^[A-Z]{1,3}\d[A-Z0-9/]*[A-Z][A-Z0-9/]*,", text):
                        unexpected[text.split(",", 2)[1].strip()] += 1
        if current:
            rows.append(record(*current))
    if not rows or not date:
        raise ValueError("Keine Rufzeichen oder kein Listenstand im erwarteten PDF-Format gefunden.")
    return rows, date[1], unexpected


def write_exports(source, rows, date):
    folder = source.parent
    database = folder / "rufzeichen.sqlite3"
    temporary = database.with_suffix(".tmp")
    temporary.unlink(missing_ok=True)
    with sqlite3.connect(temporary, autocommit=False) as connection:
        connection.executescript("""
            CREATE TABLE eintrag (
                id INTEGER PRIMARY KEY, rufzeichen TEXT NOT NULL, klasse TEXT NOT NULL,
                name TEXT NOT NULL, pdf_seite INTEGER NOT NULL
            );
            CREATE TABLE ort (
                eintrag_id INTEGER NOT NULL REFERENCES eintrag(id),
                plz TEXT NOT NULL, name TEXT NOT NULL,
                PRIMARY KEY (eintrag_id, plz, name)
            );
            CREATE TABLE metadaten (schluessel TEXT PRIMARY KEY, wert TEXT NOT NULL);
            CREATE INDEX nach_rufzeichen ON eintrag(rufzeichen);
            CREATE INDEX nach_name ON eintrag(name);
            CREATE INDEX nach_ort ON ort(name);
        """)
        connection.executemany("INSERT INTO eintrag VALUES (?, ?, ?, ?, ?)", (
            (index, call, licence, name, page) for index, (call, licence, name, _, page) in enumerate(rows, 1)
        ))
        connection.executemany("INSERT INTO ort VALUES (?, ?, ?)", (
            (index, postal, place) for index, (_, _, _, places, _) in enumerate(rows, 1)
            for postal, place in places
        ))
        connection.executemany("INSERT INTO metadaten VALUES (?, ?)", [("quelle", source.name), ("stand", date)])
    connection.close()
    temporary.replace(database)
    payload = json.dumps({"stand": date, "quelle": source.name, "eintraege": rows}, ensure_ascii=False, separators=(",", ":"))
    (folder / "rufzeichen-daten.js").write_text(f"const rufzeichenDaten = {payload};\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Importiert die Rufzeichenliste der Bundesnetzagentur.")
    parser.add_argument("pdf", nargs="?", type=Path, default=Path(__file__).with_name("rufzeichenliste_afu.pdf"))
    parser.add_argument("--pruefen", action="store_true", help="PDF auswerten, ohne Datenexporte zu schreiben")
    args = parser.parse_args()
    rows, date, unexpected = extract(args.pdf)
    print(f"Stand {date}: {len(rows):,} Eintraege, {sum(bool(row[3]) for row in rows):,} mit Ort.")
    print(f"Erste/letzte PDF-Seite mit Eintraegen: {rows[0][4]}/{rows[-1][4]}")
    print(f"Klassen: {dict(Counter(row[1] for row in rows))}; auffaellige Zeilen: {dict(unexpected)}")
    if not args.pruefen:
        write_exports(args.pdf, rows, date)


if __name__ == "__main__":
    main()