import csv
import sqlite3
import re

DB_FILE = "lezioni.db"

def validate_iso_date(s: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", (s or "").strip()))

def ddmmyyyy_to_iso(s: str) -> str:
    s = (s or "").strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
    if not m:
        return ""
    dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
    return f"{yyyy}-{mm}-{dd}"

def lesson_exists(cur, title: str, course: str, day: str) -> bool:
    cur.execute(
        "SELECT 1 FROM lessons WHERE title=? AND course=? AND day=? LIMIT 1",
        (title.strip(), course.strip(), day.strip())
    )
    return cur.fetchone() is not None

def get_col(row: dict, *names):
    for n in names:
        if n in row and row[n] is not None:
            return row[n]
        ln = n.lower()
        for k in row.keys():
            if k.lower() == ln:
                return row[k]
    return ""

def main():
    csv_path = input('Percorso CSV (es. "lezioni_ingegneria_del_software.csv"): ').strip().strip('"')
    if not csv_path:
        print("Nessun CSV.")
        return

    course = input("Nome corso/categoria da assegnare: ").strip()
    if not course:
        print("Corso vuoto.")
        return

    fallback_day = input("Giorno fallback (YYYY-MM-DD) se manca la data [invio=2025-01-01]: ").strip()
    if not fallback_day:
        fallback_day = "2025-01-01"
    if not validate_iso_date(fallback_day):
        print("Fallback day non valido. Usa YYYY-MM-DD.")
        return

    skip = input("Saltare duplicati (y/n) [y]? ").strip().lower()
    skip_dupes = (skip == "" or skip in ("y", "yes"))

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    imported = 0
    skipped = 0
    errors = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("CSV vuoto o non valido.")
            return

        for row in reader:
            try:
                numero = str(get_col(row, "numero")).strip()
                titolo = str(get_col(row, "titolo", "title")).strip()
                dayISO = str(get_col(row, "dayISO", "day", "giorno")).strip()
                data = str(get_col(row, "data")).strip()
                bbb_id = str(get_col(row, "bbb_id", "bbb-id")).strip()

                if not titolo:
                    skipped += 1
                    continue

                # Se vuoi mantenere la numerazione visibile nel titolo:
                title_final = f"{numero}-{titolo}" if numero and not titolo.startswith(f"{numero}-") else titolo

                # Se nel CSV non hai già reso univoco il titolo, puoi rafforzarlo col bbb_id:
                # (nel nostro exporter JS l'ha già fatto, ma così sei a prova di errore)
                if bbb_id and bbb_id not in title_final:
                    tail = bbb_id[-10:] if len(bbb_id) > 16 else bbb_id
                    title_final = f"{title_final} [{tail}]"

                if validate_iso_date(dayISO):
                    day = dayISO
                else:
                    iso = ddmmyyyy_to_iso(data)
                    day = iso if validate_iso_date(iso) else fallback_day

                if not validate_iso_date(day):
                    errors += 1
                    continue

                if skip_dupes and lesson_exists(cur, title_final, course, day):
                    skipped += 1
                    continue

                cur.execute(
                    "INSERT INTO lessons(title, course, day, done) VALUES(?,?,?,0)",
                    (title_final, course, day),
                )
                imported += 1
            except Exception:
                errors += 1

    conn.commit()
    conn.close()
    print(f"Import completato! Importate={imported}, Saltate={skipped}, Errori={errors}")

if __name__ == "__main__":
    main()
