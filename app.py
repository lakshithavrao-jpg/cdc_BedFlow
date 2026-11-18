import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from db import init_db


# =====================================================
# APPLICATION CONFIGURATION
# =====================================================

app = Flask(__name__)

app.secret_key = "BedFlow_Project_Secret_Key_2026"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "bedflow.db")

RATES = {
    "General": 1000,
    "Semi-Private": 2000,
    "ICU": 5000
}

init_db()


# =====================================================
# DATABASE FUNCTIONS
# =====================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_columns(conn, table):
    return {
        row["name"]
        for row in conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    }


def current_datetime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_login_id(role, conn):
    if role == "patient":
        prefix = "PT"
        table = "patients"
    else:
        prefix = "ADMIN"
        table = "admins"

    row = conn.execute(
        f"SELECT MAX(id) AS max_id FROM {table}"
    ).fetchone()

    next_id = (row["max_id"] or 0) + 1

    return f"{prefix}{next_id:06d}"


def calculate_bill(admission_date, discharge_date, rate):
    try:
        start = datetime.strptime(
            admission_date, "%Y-%m-%d %H:%M:%S"
        )

        end = datetime.strptime(
            discharge_date, "%Y-%m-%d %H:%M:%S"
        )

        days = max(1, (end.date() - start.date()).days + 1)

        return days * rate

    except (ValueError, TypeError):
        return rate


# =====================================================
# LOGIN PROTECTION
# =====================================================

def login_required(role=None):

    def decorator(function):

        @wraps(function)
        def wrapper(*args, **kwargs):

            if not session.get("user_id"):
                flash("Please log in first.", "warning")
                return redirect(
                    url_for("login", role=role or "patient")
                )

            if role and session.get("role") != role:
                flash(
                    "You do not have permission to access this page.",
                    "danger"
                )

                if session.get("role") == "admin":
                    return redirect(url_for("admin_dashboard"))

                return redirect(url_for("patient_dashboard"))

            return function(*args, **kwargs)

        return wrapper

    return decorator


# =====================================================
# HOME
# =====================================================

@app.route("/")
def index():

    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))

    if session.get("role") == "patient":
        return redirect(url_for("patient_dashboard"))

    return render_template("base.html")


# =====================================================
# REGISTRATION
# =====================================================

@app.route("/register", methods=["GET", "POST"])
@app.route("/register/<role>", methods=["GET", "POST"])
def register(role=None):

    role = (
        role or request.args.get("role") or "patient"
    ).lower()

    if role not in ["admin", "patient"]:
        role = "patient"

    if request.method == "POST":

        role = request.form.get("role", role).lower()

        if role not in ["admin", "patient"]:
            flash("Invalid registration type.", "danger")
            return redirect(
                url_for("register", role="patient")
            )

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password", ""
        )

        if not name or not password:
            flash(
                "Please enter all required details.",
                "danger"
            )
            return redirect(url_for("register", role=role))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register", role=role))

        if len(password) < 6:
            flash(
                "Password must contain at least 6 characters.",
                "danger"
            )
            return redirect(url_for("register", role=role))

        conn = get_db()

        table = "admins" if role == "admin" else "patients"

        if email:
            existing = conn.execute(
                f"""
                SELECT id FROM {table}
                WHERE LOWER(email) = ?
                """,
                (email,)
            ).fetchone()

            if existing:
                conn.close()
                flash(
                    "An account with this email already exists.",
                    "danger"
                )
                return redirect(
                    url_for("register", role=role)
                )

        login_id = generate_login_id(role, conn)
        password_hash = generate_password_hash(password)

        if role == "admin":

            conn.execute("""
                INSERT INTO admins
                (name, login_id, email, password_hash)
                VALUES (?, ?, ?, ?)
            """, (
                name,
                login_id,
                email or None,
                password_hash
            ))

        else:

            try:
                age = int(request.form.get("age") or 0)
            except ValueError:
                age = 0

            phone = request.form.get("phone", "").strip()
            gender = request.form.get("gender", "").strip()
            address = request.form.get("address", "").strip()
            diagnosis = request.form.get("diagnosis", "").strip()

            bed_type = request.form.get(
                "required_bed_type", "General"
            )

            if bed_type not in RATES:
                bed_type = "General"

            conn.execute("""
                INSERT INTO patients (
                    name, age, phone, diagnosis,
                    required_bed_type, admission_date,
                    status, total_bill, login_id,
                    password_hash, email, gender,
                    address, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                age,
                phone,
                diagnosis or "Not specified",
                bed_type,
                "",
                "Registered",
                0,
                login_id,
                password_hash,
                email or None,
                gender,
                address,
                current_datetime()
            ))

        conn.commit()
        conn.close()

        flash(
            f"Registration successful! Your Login ID is {login_id}. "
            "Please save it.",
            "success"
        )

        return redirect(url_for("login", role=role))

    return render_template("register.html", role=role)


# =====================================================
# LOGIN
# =====================================================

@app.route("/login", methods=["GET", "POST"])
@app.route("/login/", methods=["GET", "POST"])
@app.route("/login/<role>", methods=["GET", "POST"])
def login(role=None):

    role = (
        role or request.args.get("role") or "patient"
    ).lower()

    if role not in ["admin", "patient"]:
        role = "patient"

    if request.method == "GET" and session.get("user_id"):

        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))

        if session.get("role") == "patient":
            return redirect(url_for("patient_dashboard"))

    if request.method == "POST":

        selected_role = request.form.get(
            "role", role
        ).lower()

        if selected_role not in ["admin", "patient"]:
            flash("Invalid login type.", "danger")
            return redirect(url_for("login", role=role))

        login_id = request.form.get("login_id", "").strip()
        password = request.form.get("password", "")

        if not login_id or not password:
            flash(
                "Enter your Login ID/email and password.",
                "danger"
            )
            return redirect(
                url_for("login", role=selected_role)
            )

        table = (
            "admins" if selected_role == "admin"
            else "patients"
        )

        conn = get_db()

        columns = get_columns(conn, table)

        conditions = []
        values = []

        if "login_id" in columns:
            conditions.append(
                "LOWER(login_id) = LOWER(?)"
            )
            values.append(login_id)

        if "email" in columns:
            conditions.append(
                "LOWER(email) = LOWER(?)"
            )
            values.append(login_id)

        if not conditions:
            conn.close()
            flash(
                "Login is not configured correctly.",
                "danger"
            )
            return redirect(
                url_for("login", role=selected_role)
            )

        query = f"""
            SELECT * FROM {table}
            WHERE {" OR ".join(conditions)}
            LIMIT 1
        """

        user = conn.execute(query, values).fetchone()

        conn.close()

        if not user:
            flash(
                f"No {selected_role} account found with these details.",
                "danger"
            )
            return redirect(
                url_for("login", role=selected_role)
            )

        stored_hash = user["password_hash"]

        if not stored_hash or not check_password_hash(
            stored_hash, password
        ):
            flash("Incorrect password.", "danger")
            return redirect(
                url_for("login", role=selected_role)
            )

        session.clear()

        session["user_id"] = user["id"]
        session["role"] = selected_role
        session["login_id"] = user["login_id"]
        session["name"] = user["name"]

        flash("Login successful!", "success")

        if selected_role == "admin":
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("patient_dashboard"))

    return render_template("login.html", role=role)


# =====================================================
# LOGOUT
# =====================================================

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.", "info")

    return redirect(url_for("login", role="patient"))


# =====================================================
# ADMIN DASHBOARD
# =====================================================

@app.route("/admin")
@app.route("/admin/dashboard")
@login_required("admin")
def admin_dashboard():

    conn = get_db()

    total_beds = conn.execute(
        "SELECT COUNT(*) AS count FROM beds"
    ).fetchone()["count"]

    available_beds = conn.execute("""
        SELECT COUNT(*) AS count
        FROM beds
        WHERE LOWER(status) = 'available'
    """).fetchone()["count"]

    occupied_beds = conn.execute("""
        SELECT COUNT(*) AS count
        FROM beds
        WHERE LOWER(status) = 'occupied'
    """).fetchone()["count"]

    total_patients = conn.execute(
        "SELECT COUNT(*) AS count FROM patients"
    ).fetchone()["count"]

    admitted_patients = conn.execute("""
        SELECT COUNT(*) AS count
        FROM patients
        WHERE LOWER(status) = 'admitted'
    """).fetchone()["count"]

    total_wards = conn.execute(
        "SELECT COUNT(*) AS count FROM wards"
    ).fetchone()["count"]

    waiting_count = conn.execute(
        "SELECT COUNT(*) AS count FROM waiting_list"
    ).fetchone()["count"]

    occupancy = (
        round((occupied_beds / total_beds) * 100, 2)
        if total_beds else 0
    )

    wards = conn.execute("""
        SELECT
            w.id,
            w.name,
            COUNT(b.id) AS total_beds,
            SUM(
                CASE WHEN LOWER(b.status) = 'available'
                THEN 1 ELSE 0 END
            ) AS available_beds,
            SUM(
                CASE WHEN LOWER(b.status) = 'occupied'
                THEN 1 ELSE 0 END
            ) AS occupied_beds
        FROM wards w
        LEFT JOIN beds b ON w.id = b.ward_id
        GROUP BY w.id, w.name
        ORDER BY w.name
    """).fetchall()

    recent_patients = conn.execute("""
        SELECT p.*, w.name AS ward_name, b.bed_number
        FROM patients p
        LEFT JOIN wards w ON p.ward_id = w.id
        LEFT JOIN beds b ON p.bed_id = b.id
        ORDER BY p.id DESC
        LIMIT 10
    """).fetchall()

    waiting_patients = conn.execute("""
        SELECT
            wl.id AS waiting_id,
            wl.bed_type,
            wl.requested_at,
            p.id AS patient_id,
            p.name,
            p.phone,
            p.login_id
        FROM waiting_list wl
        JOIN patients p ON wl.patient_id = p.id
        ORDER BY wl.requested_at ASC, wl.id ASC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_beds=total_beds,
        available_beds=available_beds,
        occupied_beds=occupied_beds,
        total_patients=total_patients,
        admitted_patients=admitted_patients,
        total_wards=total_wards,
        waiting_count=waiting_count,
        occupancy=occupancy,
        wards=wards,
        recent_patients=recent_patients,
        waiting_patients=waiting_patients
    )


# =====================================================
# PATIENT DASHBOARD
# =====================================================

@app.route("/patient")
@app.route("/patient/dashboard")
@login_required("patient")
def patient_dashboard():

    conn = get_db()

    patient = conn.execute("""
        SELECT
            p.*,
            w.name AS ward_name,
            b.bed_number
        FROM patients p
        LEFT JOIN wards w ON p.ward_id = w.id
        LEFT JOIN beds b ON p.bed_id = b.id
        WHERE p.id = ?
    """, (session["user_id"],)).fetchone()

    if not patient:
        conn.close()
        session.clear()
        flash("Patient account not found.", "danger")
        return redirect(url_for("login", role="patient"))

    admissions = conn.execute("""
        SELECT *
        FROM admissions
        WHERE patient_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    consultations = conn.execute("""
        SELECT *
        FROM doctor_consultations
        WHERE patient_id = ?
        ORDER BY consultation_date DESC
    """, (session["user_id"],)).fetchall()

    waiting = conn.execute("""
        SELECT *
        FROM waiting_list
        WHERE patient_id = ?
        ORDER BY requested_at ASC
        LIMIT 1
    """, (session["user_id"],)).fetchone()

    total_bill = sum(
        admission["bill_amount"] or 0
        for admission in admissions
    )

    current_admission = conn.execute("""
        SELECT *
        FROM admissions
        WHERE patient_id = ?
        AND LOWER(status) = 'admitted'
        ORDER BY id DESC
        LIMIT 1
    """, (session["user_id"],)).fetchone()

    conn.close()

    return render_template(
        "patient_dashboard.html",
        patient=patient,
        admissions=admissions,
        consultations=consultations,
        waiting=waiting,
        total_bill=total_bill,
        current_admission=current_admission
    )


# =====================================================
# PATIENT LIST
# =====================================================

@app.route("/patients")
@app.route("/admin/patients")
@login_required("admin")
def patients():

    conn = get_db()

    patient_list = conn.execute("""
        SELECT
            p.*,
            w.name AS ward_name,
            b.bed_number
        FROM patients p
        LEFT JOIN wards w ON p.ward_id = w.id
        LEFT JOIN beds b ON p.bed_id = b.id
        ORDER BY p.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "patients.html",
        patients=patient_list
    )


# =====================================================
# BED MANAGEMENT
# =====================================================

@app.route("/beds", methods=["GET", "POST"])
@app.route("/admin/beds", methods=["GET", "POST"])
@login_required("admin")
def beds():

    conn = get_db()

    if request.method == "POST":

        action = request.form.get("action", "add_bed")

        if action == "add_ward":

            ward_name = request.form.get(
                "ward_name", ""
            ).strip()

            if ward_name:
                conn.execute("""
                    INSERT INTO wards (name, created_at)
                    VALUES (?, ?)
                """, (
                    ward_name,
                    current_datetime()
                ))

                conn.commit()
                flash("Ward added successfully.", "success")

        else:

            ward_id = request.form.get("ward_id")
            bed_number = request.form.get(
                "bed_number", ""
            ).strip()

            bed_type = request.form.get(
                "bed_type", "General"
            )

            if ward_id and bed_number and bed_type in RATES:

                existing = conn.execute("""
                    SELECT id FROM beds
                    WHERE bed_number = ? AND ward_id = ?
                """, (
                    bed_number,
                    ward_id
                )).fetchone()

                if existing:
                    flash(
                        "This bed number already exists in the ward.",
                        "warning"
                    )
                else:
                    conn.execute("""
                        INSERT INTO beds
                        (ward_id, bed_number, bed_type, status)
                        VALUES (?, ?, ?, 'Available')
                    """, (
                        ward_id,
                        bed_number,
                        bed_type
                    ))

                    conn.commit()
                    flash("Bed added successfully.", "success")

        conn.close()
        return redirect(url_for("beds"))

    ward_list = conn.execute(
        "SELECT * FROM wards ORDER BY name"
    ).fetchall()

    bed_list = conn.execute("""
        SELECT
            b.*,
            w.name AS ward_name,
            p.name AS patient_name
        FROM beds b
        LEFT JOIN wards w ON b.ward_id = w.id
        LEFT JOIN patients p ON p.bed_id = b.id
        ORDER BY w.name, b.bed_number
    """).fetchall()

    conn.close()

    return render_template(
        "beds.html",
        wards=ward_list,
        beds=bed_list
    )


# =====================================================
# ADMISSION
# =====================================================

@app.route("/admit", methods=["GET", "POST"])
@app.route("/admin/admit", methods=["GET", "POST"])
@login_required("admin")
def admit():

    conn = get_db()

    if request.method == "POST":

        patient_id = request.form.get("patient_id")
        bed_id = request.form.get("bed_id")

        patient = conn.execute("""
            SELECT * FROM patients WHERE id = ?
        """, (patient_id,)).fetchone()

        if not patient:
            conn.close()
            flash("Patient not found.", "danger")
            return redirect(url_for("admit"))

        if (patient["status"] or "").strip().lower() == "admitted":
            conn.close()
            flash(
                "This patient is already admitted.",
                "warning"
            )
            return redirect(url_for("admit"))

        # Clear stale bed references from non-admitted patients.
        # This helps older databases with a UNIQUE constraint on bed_id.

        conn.execute("""
            UPDATE patients
            SET bed_id = NULL, ward_id = NULL
            WHERE LOWER(TRIM(COALESCE(status, ''))) != 'admitted'
              AND bed_id IN (
                  SELECT id FROM beds
                  WHERE LOWER(TRIM(COALESCE(status, ''))) = 'available'
              )
        """)

        # A bed must be Available and must not already be assigned
        # to another patient.

        if bed_id:

            bed = conn.execute("""
                SELECT b.*, w.name AS ward_name
                FROM beds b
                JOIN wards w ON b.ward_id = w.id
                WHERE b.id = ?
                  AND LOWER(TRIM(b.status)) = 'available'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM patients p
                      WHERE p.bed_id = b.id
                  )
            """, (bed_id,)).fetchone()

        else:

            bed = conn.execute("""
                SELECT b.*, w.name AS ward_name
                FROM beds b
                JOIN wards w ON b.ward_id = w.id
                WHERE LOWER(TRIM(b.bed_type)) = LOWER(TRIM(?))
                  AND LOWER(TRIM(b.status)) = 'available'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM patients p
                      WHERE p.bed_id = b.id
                  )
                ORDER BY b.id
                LIMIT 1
            """, (
                patient["required_bed_type"],
            )).fetchone()

        if not bed:

            already_waiting = conn.execute("""
                SELECT id FROM waiting_list
                WHERE patient_id = ?
            """, (patient_id,)).fetchone()

            if not already_waiting:
                conn.execute("""
                    INSERT INTO waiting_list
                    (patient_id, bed_type, requested_at)
                    VALUES (?, ?, ?)
                """, (
                    patient_id,
                    patient["required_bed_type"],
                    current_datetime()
                ))

            conn.execute("""
                UPDATE patients
                SET status = 'Waiting'
                WHERE id = ?
            """, (patient_id,))

            conn.commit()
            conn.close()

            flash(
                "No suitable bed available. Patient added to waiting list.",
                "warning"
            )

            return redirect(url_for("waiting_list"))

        if bed["bed_type"] != patient["required_bed_type"]:
            conn.close()
            flash(
                "Selected bed type does not match the patient's requirement.",
                "danger"
            )
            return redirect(url_for("admit"))

        now = current_datetime()
        rate = RATES.get(bed["bed_type"], 1000)

        conn.execute("""
            UPDATE beds
            SET status = 'Occupied'
            WHERE id = ?
        """, (bed["id"],))

        conn.execute("""
            UPDATE patients
            SET
                bed_id = ?,
                ward_id = ?,
                admission_date = ?,
                discharge_date = NULL,
                status = 'Admitted'
            WHERE id = ?
        """, (
            bed["id"],
            bed["ward_id"],
            now,
            patient_id
        ))

        conn.execute("""
            DELETE FROM waiting_list
            WHERE patient_id = ?
        """, (patient_id,))

        conn.execute("""
            INSERT INTO admissions (
                patient_id, bed_id, ward_name,
                bed_number, bed_type, admission_date,
                discharge_date, status, rate_per_day, bill_amount
            )
            VALUES (?, ?, ?, ?, ?, ?, NULL, 'Admitted', ?, 0)
        """, (
            patient_id,
            bed["id"],
            bed["ward_name"],
            bed["bed_number"],
            bed["bed_type"],
            now,
            rate
        ))

        conn.commit()
        conn.close()

        flash("Patient admitted successfully.", "success")

        return redirect(url_for("admin_dashboard"))

    patient_list = conn.execute("""
        SELECT * FROM patients
        WHERE LOWER(status) != 'admitted'
        ORDER BY name
    """).fetchall()

    available_beds = conn.execute("""
        SELECT
            b.*,
            w.name AS ward_name
        FROM beds b
        JOIN wards w ON b.ward_id = w.id
        WHERE LOWER(b.status) = 'available'
        ORDER BY w.name, b.bed_number
    """).fetchall()

    conn.close()

    return render_template(
        "admit.html",
        patients=patient_list,
        beds=available_beds
    )


# =====================================================
# WAITING LIST
# =====================================================

@app.route("/waiting-list")
@app.route("/admin/waiting-list")
@login_required("admin")
def waiting_list():

    conn = get_db()

    waiting_patients = conn.execute("""
        SELECT
            wl.id AS waiting_id,
            wl.bed_type,
            wl.requested_at,
            p.id AS patient_id,
            p.name,
            p.age,
            p.phone,
            p.login_id,
            p.diagnosis
        FROM waiting_list wl
        JOIN patients p ON wl.patient_id = p.id
        ORDER BY wl.requested_at ASC, wl.id ASC
    """).fetchall()

    conn.close()

    return render_template(
        "waiting_list.html",
        waiting_list=waiting_patients,
        patients=waiting_patients
    )


# =====================================================
# DISCHARGE PATIENT
# =====================================================

@app.route("/discharge/<int:patient_id>", methods=["POST"])
@login_required("admin")
def discharge(patient_id):

    conn = get_db()

    try:

        patient = conn.execute("""
            SELECT *
            FROM patients
            WHERE id = ?
        """, (patient_id,)).fetchone()

        if not patient:
            flash("Patient not found.", "danger")
            return redirect(url_for("patients"))

        patient_status = (
            patient["status"] or ""
        ).strip().lower()

        if patient_status != "admitted":
            flash(
                "This patient is not currently admitted.",
                "warning"
            )
            return redirect(url_for("admin_dashboard"))

        admission = conn.execute("""
            SELECT *
            FROM admissions
            WHERE patient_id = ?
            AND LOWER(TRIM(COALESCE(status, ''))) = 'admitted'
            ORDER BY id DESC
            LIMIT 1
        """, (patient_id,)).fetchone()

        if not admission:
            flash(
                "Active admission record was not found. "
                "Please check the patient's admission history.",
                "danger"
            )
            return redirect(url_for("admin_dashboard"))

        discharge_time = current_datetime()

        admission_date = admission["admission_date"]
        rate = admission["rate_per_day"] or 1000

        bill = calculate_bill(
            admission_date,
            discharge_time,
            rate
        )

        bed_id = admission["bed_id"] or patient["bed_id"]

        # Release the bed.

        if bed_id:
            conn.execute("""
                UPDATE beds
                SET status = 'Available'
                WHERE id = ?
            """, (bed_id,))

        # Update admission history.

        conn.execute("""
            UPDATE admissions
            SET
                discharge_date = ?,
                status = 'Discharged',
                bill_amount = ?
            WHERE id = ?
        """, (
            discharge_time,
            bill,
            admission["id"]
        ))

        # Clear the patient's bed assignment.

        conn.execute("""
            UPDATE patients
            SET
                status = 'Discharged',
                discharge_date = ?,
                total_bill = COALESCE(total_bill, 0) + ?,
                bed_id = NULL,
                ward_id = NULL
            WHERE id = ?
        """, (
            discharge_time,
            bill,
            patient_id
        ))

        conn.commit()

        # Automatically assign the released bed to the
        # oldest matching patient in the waiting list.

        if bed_id:

            waiting_patient = conn.execute("""
                SELECT
                    wl.id AS waiting_id,
                    wl.patient_id
                FROM waiting_list wl
                JOIN patients p
                    ON p.id = wl.patient_id
                WHERE LOWER(TRIM(wl.bed_type)) =
                      LOWER(TRIM(?))
                ORDER BY wl.requested_at ASC, wl.id ASC
                LIMIT 1
            """, (admission["bed_type"],)).fetchone()

            if waiting_patient:

                bed = conn.execute("""
                    SELECT
                        b.*,
                        w.name AS ward_name
                    FROM beds b
                    JOIN wards w
                        ON w.id = b.ward_id
                    WHERE b.id = ?
                    AND LOWER(TRIM(b.status)) = 'available'
                """, (bed_id,)).fetchone()

                if bed:

                    new_admission_time = current_datetime()

                    new_rate = RATES.get(
                        bed["bed_type"],
                        1000
                    )

                    conn.execute("""
                        UPDATE beds
                        SET status = 'Occupied'
                        WHERE id = ?
                    """, (bed["id"],))

                    # Clear stale references from non-admitted
                    # patients before assigning the released bed.

                    conn.execute("""
                        UPDATE patients
                        SET bed_id = NULL, ward_id = NULL
                        WHERE bed_id = ?
                          AND LOWER(TRIM(COALESCE(status, ''))) != 'admitted'
                    """, (bed["id"],))

                    conn.execute("""
                        UPDATE patients
                        SET
                            status = 'Admitted',
                            bed_id = ?,
                            ward_id = ?,
                            admission_date = ?,
                            discharge_date = NULL
                        WHERE id = ?
                    """, (
                        bed["id"],
                        bed["ward_id"],
                        new_admission_time,
                        waiting_patient["patient_id"]
                    ))

                    conn.execute("""
                        INSERT INTO admissions (
                            patient_id,
                            bed_id,
                            ward_name,
                            bed_number,
                            bed_type,
                            admission_date,
                            discharge_date,
                            status,
                            rate_per_day,
                            bill_amount
                        )
                        VALUES (?, ?, ?, ?, ?, ?, NULL, 'Admitted', ?, 0)
                    """, (
                        waiting_patient["patient_id"],
                        bed["id"],
                        bed["ward_name"],
                        bed["bed_number"],
                        bed["bed_type"],
                        new_admission_time,
                        new_rate
                    ))

                    conn.execute("""
                        DELETE FROM waiting_list
                        WHERE id = ?
                    """, (waiting_patient["waiting_id"],))

                    conn.commit()

                    flash(
                        "The next waiting patient has automatically "
                        "been allocated the released bed.",
                        "info"
                    )

        conn.commit()

        flash(
            f"Patient discharged successfully! Final bill: ₹{bill}",
            "success"
        )

    except Exception as error:

        conn.rollback()

        print("DISCHARGE ERROR:", error)

        flash(
            f"Unable to discharge patient: {error}",
            "danger"
        )

    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))


# =====================================================
# DOCTOR CONSULTATIONS
# =====================================================

@app.route("/admin/consultation", methods=["GET", "POST"])
@login_required("admin")
def add_consultation():

    conn = get_db()

    if request.method == "POST":

        patient_id = request.form.get("patient_id")
        doctor_name = request.form.get(
            "doctor_name", ""
        ).strip()

        department = request.form.get(
            "department", ""
        ).strip()

        notes = request.form.get("notes", "").strip()
        fee = request.form.get("consultation_fee", 0)

        try:
            fee = float(fee or 0)
        except ValueError:
            fee = 0

        patient = conn.execute(
            "SELECT id FROM patients WHERE id = ?",
            (patient_id,)
        ).fetchone()

        if patient and doctor_name:

            conn.execute("""
                INSERT INTO doctor_consultations (
                    patient_id, doctor_name, department,
                    consultation_date, notes, consultation_fee
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                doctor_name,
                department,
                current_datetime(),
                notes,
                fee
            ))

            conn.commit()

            flash(
                "Doctor consultation added successfully.",
                "success"
            )

        else:
            flash(
                "Select a patient and enter the doctor's name.",
                "danger"
            )

        conn.close()

        return redirect(url_for("add_consultation"))

    patient_list = conn.execute("""
        SELECT id, name, login_id
        FROM patients
        ORDER BY name
    """).fetchall()

    consultations = conn.execute("""
        SELECT
            dc.*,
            p.name AS patient_name,
            p.login_id
        FROM doctor_consultations dc
        JOIN patients p ON dc.patient_id = p.id
        ORDER BY dc.consultation_date DESC
    """).fetchall()

    conn.close()

    return render_template(
        "consultations.html",
        patients=patient_list,
        consultations=consultations
    )


# =====================================================
# CHANGE PASSWORD
# =====================================================

@app.route("/change-password", methods=["GET", "POST"])
@app.route(
    "/patient/change-password",
    methods=["GET", "POST"],
    endpoint="patient_change_password"
)
@login_required()
def change_password():

    if request.method == "POST":

        old_password = request.form.get("old_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get(
            "confirm_password", ""
        )

        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return redirect(
                request.referrer or url_for("patient_dashboard")
            )

        if len(new_password) < 6:
            flash(
                "New password must contain at least 6 characters.",
                "danger"
            )
            return redirect(
                request.referrer or url_for("patient_dashboard")
            )

        table = (
            "admins" if session["role"] == "admin"
            else "patients"
        )

        conn = get_db()

        user = conn.execute(
            f"SELECT * FROM {table} WHERE id = ?",
            (session["user_id"],)
        ).fetchone()

        if not user or not check_password_hash(
            user["password_hash"], old_password
        ):
            conn.close()

            flash(
                "Your current password is incorrect.",
                "danger"
            )

            return redirect(
                request.referrer or url_for("patient_dashboard")
            )

        new_hash = generate_password_hash(new_password)

        conn.execute(
            f"UPDATE {table} SET password_hash = ? WHERE id = ?",
            (new_hash, session["user_id"])
        )

        conn.commit()
        conn.close()

        flash("Password changed successfully.", "success")

        if session["role"] == "admin":
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("patient_dashboard"))

    return render_template("change_password.html")


# =====================================================
# ERROR HANDLERS
# =====================================================

@app.errorhandler(404)
def page_not_found(error):
    return "Page not found. Please check the URL.", 404


@app.errorhandler(500)
def internal_error(error):
    return (
        "An internal error occurred. Check the terminal for details.",
        500
    )


# =====================================================
# RUN APPLICATION
# =====================================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )