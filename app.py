from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = "bedflow-demo-secret-key"

DB = Path(__file__).with_name("bedflow.db")

RATES = {
    "General": 1000,
    "Semi-Private": 2000,
    "ICU": 5000
}


# DATABASE CONNECTION
def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


# CREATE DATABASE TABLES
def init_db():
    with connect() as con:

        con.executescript("""
        CREATE TABLE IF NOT EXISTS wards(
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS beds(
            id INTEGER PRIMARY KEY,
            ward_id INTEGER NOT NULL,
            bed_number TEXT UNIQUE NOT NULL,
            bed_type TEXT NOT NULL,
            FOREIGN KEY(ward_id) REFERENCES wards(id)
        );

        CREATE TABLE IF NOT EXISTS patients(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            phone TEXT,
            diagnosis TEXT NOT NULL,
            required_bed_type TEXT NOT NULL,
            ward_id INTEGER,
            bed_id INTEGER,
            admission_date TEXT NOT NULL,
            discharge_date TEXT,
            status TEXT NOT NULL DEFAULT 'Waiting',
            total_bill REAL DEFAULT 0,
            FOREIGN KEY(ward_id) REFERENCES wards(id),
            FOREIGN KEY(bed_id) REFERENCES beds(id)
        );

        CREATE TABLE IF NOT EXISTS waiting_list(
            id INTEGER PRIMARY KEY,
            patient_id INTEGER UNIQUE NOT NULL,
            bed_type TEXT NOT NULL,
            requested_at TEXT NOT NULL,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS one_patient_per_bed
        ON patients(bed_id)
        WHERE bed_id IS NOT NULL AND status='Admitted';
        """)

        # CREATE DEFAULT WARDS AND BEDS
        if con.execute("SELECT COUNT(*) FROM wards").fetchone()[0] == 0:

            ward_data = [
                ("General Ward", "General", 5, "G"),
                ("Private Care Ward", "Semi-Private", 3, "P"),
                ("Critical Care Unit", "ICU", 2, "I")
            ]

            for ward, kind, count, prefix in ward_data:

                ward_id = con.execute(
                    "INSERT INTO wards(name) VALUES(?)",
                    (ward,)
                ).lastrowid

                for n in range(1, count + 1):

                    con.execute("""
                        INSERT INTO beds(
                            ward_id, bed_number, bed_type
                        )
                        VALUES(?,?,?)
                    """, (
                        ward_id,
                        f"{prefix}-{n:02d}",
                        kind
                    ))


# FIND AVAILABLE BED
def free_bed(con, kind):

    return con.execute("""
        SELECT b.id, b.ward_id
        FROM beds b

        WHERE b.bed_type=?

        AND NOT EXISTS (
            SELECT 1
            FROM patients p
            WHERE p.bed_id=b.id
            AND p.status='Admitted'
        )

        ORDER BY b.id
        LIMIT 1

    """, (kind,)).fetchone()


# AUTOMATIC FIFO ALLOCATION
def fill_queue(con, kind):

    queue = con.execute("""
        SELECT id, patient_id
        FROM waiting_list
        WHERE bed_type=?
        ORDER BY requested_at, id
    """, (kind,)).fetchall()

    for item in queue:

        bed = free_bed(con, kind)

        if not bed:
            break

        con.execute("""
            UPDATE patients
            SET bed_id=?,
                ward_id=?,
                status='Admitted'
            WHERE id=?
        """, (
            bed["id"],
            bed["ward_id"],
            item["patient_id"]
        ))

        con.execute("""
            DELETE FROM waiting_list
            WHERE id=?
        """, (item["id"],))


# CURRENT DATE FOR ALL PAGES
@app.context_processor
def inject_date():
    return {
        "current_date": date.today().strftime("%d %b %Y")
    }


# DASHBOARD
@app.route("/")
def dashboard():

    with connect() as con:

        total = con.execute(
            "SELECT COUNT(*) FROM beds"
        ).fetchone()[0]

        occupied = con.execute("""
            SELECT COUNT(*)
            FROM patients
            WHERE status='Admitted'
        """).fetchone()[0]

        waiting = con.execute(
            "SELECT COUNT(*) FROM waiting_list"
        ).fetchone()[0]

        wards = con.execute("""
            SELECT
                w.name,
                COUNT(DISTINCT b.id) total,
                COUNT(DISTINCT CASE
                    WHEN p.status='Admitted'
                    THEN b.id
                END) occupied

            FROM wards w

            LEFT JOIN beds b
            ON b.ward_id=w.id

            LEFT JOIN patients p
            ON p.bed_id=b.id

            GROUP BY w.id
            ORDER BY w.id
        """).fetchall()

        recent = con.execute("""
            SELECT *
            FROM patients
            ORDER BY id DESC
            LIMIT 5
        """).fetchall()

    return render_template(
        "dashboard.html",
        total=total,
        occupied=occupied,
        available=total-occupied,
        waiting=waiting,
        occupancy=round(occupied*100/total, 1) if total else 0,
        wards=wards,
        recent=recent
    )


# PATIENT ADMISSION
@app.route("/admit", methods=["GET", "POST"])
def admit():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        age = request.form.get("age", "")
        phone = request.form.get("phone", "").strip()
        diagnosis = request.form.get("diagnosis", "").strip()
        kind = request.form.get("bed_type", "")

        try:
            age = int(age)

            if (
                not name
                or not diagnosis
                or not 1 <= age <= 120
                or kind not in RATES
            ):
                raise ValueError

        except ValueError:

            flash(
                "Enter valid patient details and select a bed type.",
                "error"
            )

            return redirect(url_for("admit"))

        with connect() as con:

            bed = free_bed(con, kind)

            if bed:

                cur = con.execute("""
                    INSERT INTO patients(
                        name, age, phone, diagnosis,
                        required_bed_type, ward_id,
                        bed_id, admission_date, status
                    )
                    VALUES(?,?,?,?,?,?,?,?, 'Admitted')
                """, (
                    name,
                    age,
                    phone,
                    diagnosis,
                    kind,
                    bed["ward_id"],
                    bed["id"],
                    date.today().isoformat()
                ))

                flash(
                    f"Patient admitted successfully. Patient ID: {cur.lastrowid}",
                    "success"
                )

            else:

                cur = con.execute("""
                    INSERT INTO patients(
                        name, age, phone, diagnosis,
                        required_bed_type,
                        admission_date, status
                    )
                    VALUES(?,?,?,?,?,?,'Waiting')
                """, (
                    name,
                    age,
                    phone,
                    diagnosis,
                    kind,
                    date.today().isoformat()
                ))

                con.execute("""
                    INSERT INTO waiting_list(
                        patient_id, bed_type, requested_at
                    )
                    VALUES(?,?,?)
                """, (
                    cur.lastrowid,
                    kind,
                    datetime.now().isoformat(timespec="seconds")
                ))

                flash(
                    "No matching bed is free. Patient added to the FIFO waiting list.",
                    "warning"
                )

        return redirect(url_for("patients"))

    return render_template(
        "admit.html",
        rates=RATES
    )


# BED AVAILABILITY
@app.route("/beds")
def beds():

    with connect() as con:

        rows = con.execute("""
            SELECT
                b.*,
                w.name ward_name,
                p.name patient_name,
                p.id patient_id

            FROM beds b

            JOIN wards w
            ON w.id=b.ward_id

            LEFT JOIN patients p
            ON p.bed_id=b.id
            AND p.status='Admitted'

            ORDER BY b.id
        """).fetchall()

    return render_template(
        "beds.html",
        beds=rows
    )


# PATIENT RECORDS
@app.route("/patients")
def patients():

    with connect() as con:

        rows = con.execute("""
            SELECT
                p.*,
                w.name ward_name,
                b.bed_number

            FROM patients p

            LEFT JOIN wards w
            ON w.id=p.ward_id

            LEFT JOIN beds b
            ON b.id=p.bed_id

            ORDER BY p.id DESC
        """).fetchall()

    return render_template(
        "patients.html",
        patients=rows,
        rates=RATES
    )


# WAITING LIST
@app.route("/waiting-list")
def waiting_list():

    with connect() as con:

        rows = con.execute("""
            SELECT
                q.*,
                p.name,
                p.age,
                p.diagnosis

            FROM waiting_list q

            JOIN patients p
            ON p.id=q.patient_id

            ORDER BY q.requested_at, q.id
        """).fetchall()

    return render_template(
        "waiting_list.html",
        queue=rows
    )


# PATIENT DISCHARGE
@app.route("/discharge/<int:pid>", methods=["POST"])
def discharge(pid):

    with connect() as con:

        p = con.execute("""
            SELECT *
            FROM patients
            WHERE id=? AND status='Admitted'
        """, (pid,)).fetchone()

        if not p:

            flash(
                "Admitted patient not found.",
                "error"
            )

            return redirect(url_for("patients"))

        today = date.today()

        days = max(
            1,
            (today - date.fromisoformat(
                p["admission_date"]
            )).days + 1
        )

        bill = days * RATES.get(
            p["required_bed_type"],
            1000
        )

        con.execute("""
            UPDATE patients
            SET status='Discharged',
                discharge_date=?,
                total_bill=?
            WHERE id=?
        """, (
            today.isoformat(),
            bill,
            pid
        ))

        # Allocate freed bed to oldest waiting patient
        fill_queue(
            con,
            p["required_bed_type"]
        )

    flash(
        f"Patient discharged. Illustrative bed charge: ₹{bill:,.2f}",
        "success"
    )

    return redirect(url_for("patients"))


# PATIENT TRANSFER
@app.route("/transfer/<int:pid>", methods=["POST"])
def transfer(pid):

    kind = request.form.get("bed_type", "")

    if kind not in RATES:

        flash(
            "Select a valid bed category.",
            "error"
        )

        return redirect(url_for("patients"))

    with connect() as con:

        p = con.execute("""
            SELECT *
            FROM patients
            WHERE id=? AND status='Admitted'
        """, (pid,)).fetchone()

        if not p:

            flash(
                "Admitted patient not found.",
                "error"
            )

            return redirect(url_for("patients"))

        if kind == p["required_bed_type"]:

            flash(
                "Patient already has this bed category.",
                "warning"
            )

            return redirect(url_for("patients"))

        bed = free_bed(con, kind)

        if not bed:

            flash(
                f"No available {kind} bed. Transfer not completed.",
                "error"
            )

            return redirect(url_for("patients"))

        old = p["required_bed_type"]

        con.execute("""
            UPDATE patients
            SET bed_id=?,
                ward_id=?,
                required_bed_type=?
            WHERE id=?
        """, (
            bed["id"],
            bed["ward_id"],
            kind,
            pid
        ))

        # Fill the old bed category from its waiting queue
        fill_queue(con, old)

    flash(
        "Patient transferred successfully.",
        "success"
    )

    return redirect(url_for("patients"))


if __name__ == "__main__":

    init_db()

    app.run(debug=True)