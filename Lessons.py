import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date


DB_FILE = "lezioni.db"
DATE_FMT = "%Y-%m-%d"


def today_iso() -> str:
    return date.today().strftime(DATE_FMT)


def validate_iso_date(s: str) -> bool:
    try:
        datetime.strptime(s.strip(), DATE_FMT)
        return True
    except Exception:
        return False


class LessonsDB:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                course TEXT NOT NULL,
                day TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_lessons_day ON lessons(day)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_lessons_course ON lessons(course)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_lessons_done ON lessons(done)")
        self.conn.commit()

    def add_lesson(self, title: str, course: str, day: str, done: int = 0):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO lessons(title, course, day, done) VALUES(?,?,?,?)",
            (title.strip(), course.strip(), day.strip(), int(done)),
        )
        self.conn.commit()

    def update_lesson(self, lesson_id: int, title: str, course: str, day: str, done: int):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE lessons SET title=?, course=?, day=?, done=? WHERE id=?",
            (title.strip(), course.strip(), day.strip(), int(done), int(lesson_id)),
        )
        self.conn.commit()

    def delete_lesson(self, lesson_id: int):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM lessons WHERE id=?", (int(lesson_id),))
        self.conn.commit()

    def toggle_done(self, lesson_id: int):
        cur = self.conn.cursor()
        cur.execute("UPDATE lessons SET done = CASE done WHEN 0 THEN 1 ELSE 0 END WHERE id=?", (int(lesson_id),))
        self.conn.commit()

    def list_courses(self):
        cur = self.conn.cursor()
        cur.execute("SELECT DISTINCT course FROM lessons ORDER BY course COLLATE NOCASE")
        return [r["course"] for r in cur.fetchall()]

    def query(self, day: str | None, course: str | None, only_undone: bool):
        sql = "SELECT id, title, course, day, done FROM lessons"
        where = []
        params = []

        if day and day != "TUTTE":
            where.append("day = ?")
            params.append(day)

        if course and course != "TUTTI":
            where.append("course = ?")
            params.append(course)

        if only_undone:
            where.append("done = 0")

        if where:
            sql += " WHERE " + " AND ".join(where)

        sql += " ORDER BY day ASC, course COLLATE NOCASE ASC, done ASC, id ASC"

        cur = self.conn.cursor()
        cur.execute(sql, tuple(params))
        return cur.fetchall()

    def close(self):
        self.conn.close()


class LessonDialog(tk.Toplevel):
    def __init__(self, parent, title="Lezione", initial=None):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        self.initial = initial or {}

        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        pad = {"padx": 10, "pady": 6}
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frm, text="Lezione:").grid(row=0, column=0, sticky="w", **pad)
        self.e_title = ttk.Entry(frm, width=42)
        self.e_title.grid(row=0, column=1, **pad)

        ttk.Label(frm, text="Corso/Categoria:").grid(row=1, column=0, sticky="w", **pad)
        self.e_course = ttk.Entry(frm, width=42)
        self.e_course.grid(row=1, column=1, **pad)

        ttk.Label(frm, text="Giorno (YYYY-MM-DD):").grid(row=2, column=0, sticky="w", **pad)
        day_frame = ttk.Frame(frm)
        day_frame.grid(row=2, column=1, sticky="w", **pad)
        self.e_day = ttk.Entry(day_frame, width=24)
        self.e_day.pack(side="left")
        ttk.Button(day_frame, text="Oggi", command=self._set_today).pack(side="left", padx=(8, 0))

        self.var_done = tk.IntVar(value=int(self.initial.get("done", 0)))
        ttk.Checkbutton(frm, text="Segna come fatta", variable=self.var_done).grid(
            row=3, column=1, sticky="w", **pad
        )

        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="Annulla", command=self._cancel).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Salva", command=self._save).pack(side="right")

        # Pre-fill
        self.e_title.insert(0, self.initial.get("title", ""))
        self.e_course.insert(0, self.initial.get("course", ""))
        self.e_day.insert(0, self.initial.get("day", today_iso()))

        self.e_title.focus_set()
        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self._cancel())

        self._center_on_parent()

    def _center_on_parent(self):
        self.update_idletasks()
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")

    def _set_today(self):
        self.e_day.delete(0, tk.END)
        self.e_day.insert(0, today_iso())

    def _cancel(self):
        self.result = None
        self.destroy()

    def _save(self):
        title = self.e_title.get().strip()
        course = self.e_course.get().strip()
        day = self.e_day.get().strip()
        done = int(self.var_done.get())

        if not title:
            messagebox.showerror("Errore", "Inserisci il nome della lezione.")
            return
        if not course:
            messagebox.showerror("Errore", "Inserisci il corso/categoria.")
            return
        if not validate_iso_date(day):
            messagebox.showerror("Errore", "La data deve essere nel formato YYYY-MM-DD (es. 2025-11-25).")
            return

        self.result = {"title": title, "course": course, "day": day, "done": done}
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Recupero Lezioni")
        self.minsize(860, 520)

        self.db = LessonsDB(DB_FILE)

        self._build_ui()
        self._refresh_courses()
        self._load_table()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # Top filters
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Data:").pack(side="left")
        self.var_day = tk.StringVar(value="TUTTE")
        self.e_day_filter = ttk.Entry(top, width=12, textvariable=self.var_day)
        self.e_day_filter.pack(side="left", padx=(6, 10))

        ttk.Button(top, text="Oggi", command=self._filter_today).pack(side="left")
        ttk.Button(top, text="Tutte", command=self._filter_all).pack(side="left", padx=(6, 18))

        ttk.Label(top, text="Corso:").pack(side="left")
        self.var_course = tk.StringVar(value="TUTTI")
        self.cb_course = ttk.Combobox(top, width=24, state="readonly", textvariable=self.var_course, values=["TUTTI"])
        self.cb_course.pack(side="left", padx=(6, 12))
        self.cb_course.bind("<<ComboboxSelected>>", lambda e: self._load_table())

        self.var_only_undone = tk.IntVar(value=0)
        ttk.Checkbutton(top, text="Solo non fatte", variable=self.var_only_undone, command=self._load_table).pack(
            side="left", padx=(6, 0)
        )

        ttk.Button(top, text="Applica filtri", command=self._apply_filters).pack(side="right")

        # Table
        mid = ttk.Frame(self, padding=(10, 0, 10, 10))
        mid.pack(fill="both", expand=True)

        columns = ("day", "course", "title", "done")
        self.tree = ttk.Treeview(mid, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("day", text="Giorno")
        self.tree.heading("course", text="Corso")
        self.tree.heading("title", text="Lezione")
        self.tree.heading("done", text="Stato")

        self.tree.column("day", width=110, anchor="center")
        self.tree.column("course", width=180, anchor="w")
        self.tree.column("title", width=420, anchor="w")
        self.tree.column("done", width=90, anchor="center")

        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(mid, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        mid.rowconfigure(0, weight=1)
        mid.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", lambda e: self._edit_selected())
        self.tree.bind("<space>", lambda e: self._toggle_done_selected())

        # Bottom actions
        bot = ttk.Frame(self, padding=10)
        bot.pack(fill="x")

        ttk.Button(bot, text="Aggiungi", command=self._add).pack(side="left")
        ttk.Button(bot, text="Modifica", command=self._edit_selected).pack(side="left", padx=(8, 0))
        ttk.Button(bot, text="Elimina", command=self._delete_selected).pack(side="left", padx=(8, 0))
        ttk.Button(bot, text="Fatta / Non fatta", command=self._toggle_done_selected).pack(side="left", padx=(8, 0))

        ttk.Separator(bot, orient="vertical").pack(side="left", fill="y", padx=12)

        ttk.Button(bot, text="Ricarica", command=self._reload_all).pack(side="left")

        self.status = tk.StringVar(value="")
        ttk.Label(bot, textvariable=self.status).pack(side="right")

    def _set_status(self, msg: str):
        self.status.set(msg)

    def _apply_filters(self):
        day = self.var_day.get().strip()
        if day != "TUTTE" and day and not validate_iso_date(day):
            messagebox.showerror("Errore", "Filtro data non valido. Usa YYYY-MM-DD oppure 'TUTTE'.")
            return
        self._load_table()

    def _filter_today(self):
        self.var_day.set(today_iso())
        self._load_table()

    def _filter_all(self):
        self.var_day.set("TUTTE")
        self.var_course.set("TUTTI")
        self.var_only_undone.set(0)
        self._load_table()

    def _refresh_courses(self):
        courses = self.db.list_courses()
        values = ["TUTTI"] + courses
        self.cb_course.configure(values=values)
        if self.var_course.get() not in values:
            self.var_course.set("TUTTI")

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        item_id = sel[0]
        return int(self.tree.item(item_id, "values")[0])  # hidden id in first value? (we'll store it separately)

    def _get_selected_row(self):
        sel = self.tree.selection()
        if not sel:
            return None
        item = self.tree.item(sel[0])
        # We store id in tags to avoid showing it: tags=("id:123",)
        tags = item.get("tags", [])
        if not tags:
            return None
        tag0 = tags[0]
        if not tag0.startswith("id:"):
            return None
        lesson_id = int(tag0.split(":", 1)[1])
        vals = item.get("values", [])
        # values are: day, course, title, done_str
        return {"id": lesson_id, "day": vals[0], "course": vals[1], "title": vals[2], "done": 1 if vals[3] == "Fatta" else 0}

    def _load_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        day_filter = self.var_day.get().strip()
        if not day_filter:
            day_filter = "TUTTE"

        course_filter = self.var_course.get().strip() or "TUTTI"
        only_undone = bool(self.var_only_undone.get())

        rows = self.db.query(day_filter, course_filter, only_undone)

        for r in rows:
            done_str = "Fatta" if r["done"] else "Da fare"
            item = self.tree.insert(
                "",
                "end",
                values=(r["day"], r["course"], r["title"], done_str),
                tags=(f"id:{r['id']}", "done" if r["done"] else "todo"),
            )

        # Optional: slightly differentiate done rows
        self.tree.tag_configure("done", foreground="#6b7280")  # grey-ish
        self.tree.tag_configure("todo", foreground="#111827")  # dark

        self._set_status(f"Totale visibili: {len(rows)}")
        self._refresh_courses()

    def _reload_all(self):
        self._refresh_courses()
        self._load_table()

    def _add(self):
        dlg = LessonDialog(self, title="Aggiungi lezione", initial={"day": self.var_day.get() if validate_iso_date(self.var_day.get()) else today_iso()})
        self.wait_window(dlg)
        if not dlg.result:
            return

        self.db.add_lesson(**dlg.result)
        self._reload_all()

    def _edit_selected(self):
        row = self._get_selected_row()
        if not row:
            messagebox.showinfo("Info", "Seleziona una lezione dalla tabella.")
            return

        dlg = LessonDialog(self, title="Modifica lezione", initial=row)
        self.wait_window(dlg)
        if not dlg.result:
            return

        self.db.update_lesson(row["id"], **dlg.result)
        self._reload_all()

    def _delete_selected(self):
        row = self._get_selected_row()
        if not row:
            messagebox.showinfo("Info", "Seleziona una lezione dalla tabella.")
            return

        if not messagebox.askyesno("Conferma", f"Eliminare la lezione?\n\n{row['title']} ({row['course']})"):
            return

        self.db.delete_lesson(row["id"])
        self._reload_all()

    def _toggle_done_selected(self):
        row = self._get_selected_row()
        if not row:
            messagebox.showinfo("Info", "Seleziona una lezione dalla tabella.")
            return
        self.db.toggle_done(row["id"])
        self._reload_all()

    def _on_close(self):
        try:
            self.db.close()
        finally:
            self.destroy()


if __name__ == "__main__":
    # A little nicer default styling on some systems
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = App()
    app.mainloop()
