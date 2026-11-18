import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "bedflow.db")


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def add_missing_columns(conn, table, columns):
    existing = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }

    for column_name, column_type in columns.items():
        if column_name not in existing:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"
            )


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # WARDS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT
        )
    """)

    # BEDS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS beds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_id INTEGER NOT NULL,
            bed_number TEXT NOT NULL,
            bed_type TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            FOREIGN KEY (ward_id) REFERENCES wards(id)
        )
    """)

    # PATIENTS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL DEFAULT 0,
            phone TEXT,
            diagnosis TEXT NOT NULL DEFAULT 'Not specified',
            required_bed_type TEXT NOT NULL DEFAULT 'General',
            ward_id INTEGER,
            bed_id INTEGER,
            admission_date TEXT NOT NULL DEFAULT '',
            discharge_date TEXT,
            status TEXT NOT NULL DEFAULT 'Registered',
            total_bill REAL DEFAULT 0,
            login_id TEXT,
            password_hash TEXT,
            email TEXT,
            gender TEXT,
            address TEXT,
            created_at TEXT
        )
    """)

    # ADMINS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            login_id TEXT UNIQUE,
            email TEXT,
            password_hash TEXT
        )
    """)

    # ADMISSIONS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            bed_id INTEGER,
            ward_name TEXT NOT NULL,
            bed_number TEXT NOT NULL,
            bed_type TEXT NOT NULL,
            admission_date TEXT NOT NULL,
            discharge_date TEXT,
            status TEXT NOT NULL DEFAULT 'Admitted',
            rate_per_day INTEGER NOT NULL DEFAULT 1000,
            bill_amount INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)

    # WAITING LIST
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS waiting_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            bed_type TEXT NOT NULL,
            requested_at TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)

    # DOCTOR CONSULTATIONS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctor_consultations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_name TEXT NOT NULL,
            department TEXT,
            consultation_date TEXT NOT NULL,
            notes TEXT,
            consultation_fee REAL DEFAULT 0,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)

    # Migrate older database versions without deleting records.
    add_missing_columns(conn, "patients", {
        "age": "INTEGER DEFAULT 0",
        "phone": "TEXT",
        "diagnosis": "TEXT DEFAULT 'Not specified'",
        "required_bed_type": "TEXT DEFAULT 'General'",
        "ward_id": "INTEGER",
        "bed_id": "INTEGER",
        "admission_date": "TEXT",
        "discharge_date": "TEXT",
        "status": "TEXT DEFAULT 'Registered'",
        "total_bill": "REAL DEFAULT 0",
        "login_id": "TEXT",
        "password_hash": "TEXT",
        "email": "TEXT",
        "gender": "TEXT",
        "address": "TEXT",
        "created_at": "TEXT"
    })

    add_missing_columns(conn, "admins", {
        "name": "TEXT",
        "login_id": "TEXT",
        "email": "TEXT",
        "password_hash": "TEXT"
    })

    add_missing_columns(conn, "beds", {
        "status": "TEXT DEFAULT 'Available'"
    })

    add_missing_columns(conn, "admissions", {
        "discharge_date": "TEXT",
        "status": "TEXT DEFAULT 'Admitted'",
        "rate_per_day": "INTEGER DEFAULT 1000",
        "bill_amount": "INTEGER DEFAULT 0"
    })

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("BedFlow database initialized successfully.")