import sqlite3
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

from db import init_db, get_connection


# ==========================================================
# CONFIGURATION
# ==========================================================

RATES = {
    "General": 1000,
    "Semi-Private": 2000,
    "ICU": 5000
}


# ==========================================================
# COMMON FUNCTIONS
# ==========================================================

def heading(title):
    print("\n" + "=" * 60)
    print(title.center(60))
    print("=" * 60)


def get_input(message):
    return input(message).strip()


def get_password(message="Enter password: "):
    # Password is visible while typing.
    return input(message)


def pause():
    input("\nPress Enter to continue...")


def valid_email(email):
    return (
        "@" in email
        and "." in email.split("@")[-1]
        and " " not in email
    )


def current_datetime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def current_date():
    return date.today().isoformat()


def get_days(admission_date):
    if not admission_date:
        return 1

    try:
        admission = datetime.fromisoformat(
            admission_date
        ).date()
    except ValueError:
        try:
            admission = datetime.strptime(
                admission_date, "%Y-%m-%d"
            ).date()
        except ValueError:
            return 1

    return max(1, (date.today() - admission).days)


def get_patient_by_email(email):
    conn = get_connection()

    patient = conn.execute(
        """
        SELECT * FROM patients
        WHERE LOWER(email) = ?
        ORDER BY id
        LIMIT 1
        """,
        (email.lower(),)
    ).fetchone()

    conn.close()
    return patient


# ==========================================================
# MAIN MENU
# ==========================================================

def main_menu():

    while True:

        heading("BEDFLOW - HOSPITAL MANAGEMENT SYSTEM")

        print("1. Admin Login")
        print("2. Patient Login")
        print("3. Patient Registration")
        print("4. Create Admin Account")
        print("0. Exit")

        choice = get_input("\nEnter your choice: ")

        if choice == "1":
            admin_login()

        elif choice == "2":
            patient_login()

        elif choice == "3":
            patient_registration()

        elif choice == "4":
            create_admin()

        elif choice == "0":
            print("\nThank you for using BedFlow!")
            break

        else:
            print("\nInvalid choice.")


# ==========================================================
# CREATE ADMIN ACCOUNT
# ==========================================================

def create_admin():

    heading("CREATE ADMIN ACCOUNT")

    name = get_input("Admin name: ")
    email = get_input("Admin email: ").lower()

    if not name or not email:
        print("\nName and email are required.")
        return

    if not valid_email(email):
        print("\nEnter a valid email address.")
        return

    conn = get_connection()

    existing = conn.execute(
        """
        SELECT id FROM admins
        WHERE LOWER(email) = ?
        """,
        (email,)
    ).fetchone()

    if existing:
        print("\nAn admin account with this email already exists.")
        conn.close()
        return

    password = get_password("Create password: ")
    confirm = get_password("Confirm password: ")

    if not password:
        print("\nPassword cannot be empty.")
        conn.close()
        return

    if password != confirm:
        print("\nPasswords do not match.")
        conn.close()
        return

    # New Admin ID is the same as Admin Email.
    conn.execute(
        """
        INSERT INTO admins
        (name, login_id, email, password_hash)
        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            email,
            email,
            generate_password_hash(password)
        )
    )

    conn.commit()
    conn.close()

    print("\nAdmin account created successfully!")
    print("Admin Name :", name)
    print("Admin ID   :", email)
    print("Admin Email:", email)


# ==========================================================
# ADMIN LOGIN
# ==========================================================

def admin_login():

    heading("ADMIN LOGIN")

    email = get_input("Admin Email / Admin ID: ").lower()
    password = get_password("Enter password: ")

    conn = get_connection()

    # Check all matching email accounts.
    # This supports existing duplicate admin emails.
    admins = conn.execute(
        """
        SELECT * FROM admins
        WHERE LOWER(email) = ?
        ORDER BY id
        """,
        (email,)
    ).fetchall()

    conn.close()

    matched_admin = None

    for admin in admins:

        if admin["password_hash"] and check_password_hash(
            admin["password_hash"], password
        ):
            matched_admin = admin
            break

    if matched_admin:

        print("\nAdmin login successful!")
        print("Welcome,", matched_admin["name"])
        print("Admin ID:", matched_admin["email"])

        admin_menu(matched_admin)

    else:
        print("\nInvalid admin email or password.")


# ==========================================================
# PATIENT REGISTRATION
# ==========================================================

def patient_registration():

    heading("PATIENT REGISTRATION")

    name = get_input("Patient name: ")

    if not name:
        print("\nPatient name is required.")
        return

    try:
        age = int(get_input("Age: "))

        if age < 0:
            print("\nAge cannot be negative.")
            return

    except ValueError:
        print("\nEnter a valid age.")
        return

    gender = get_input("Gender: ")
    phone = get_input("Phone number: ")
    email = get_input("Patient email: ").lower()
    address = get_input("Address: ")
    diagnosis = get_input("Diagnosis: ")

    if not valid_email(email):
        print("\nEnter a valid email address.")
        return

    print("\nRequired Bed Type:")
    print("1. General")
    print("2. Semi-Private")
    print("3. ICU")

    choice = get_input("Select bed type: ")

    bed_types = {
        "1": "General",
        "2": "Semi-Private",
        "3": "ICU"
    }

    if choice not in bed_types:
        print("\nInvalid bed type.")
        return

    bed_type = bed_types[choice]

    conn = get_connection()

    existing = conn.execute(
        """
        SELECT id FROM patients
        WHERE LOWER(email) = ?
        """,
        (email,)
    ).fetchone()

    if existing:
        print("\nA patient account with this email already exists.")
        conn.close()
        return

    password = get_password("Create password: ")
    confirm = get_password("Confirm password: ")

    if not password:
        print("\nPassword cannot be empty.")
        conn.close()
        return

    if password != confirm:
        print("\nPasswords do not match.")
        conn.close()
        return

    # Patient ID is the same as Patient Email.
    patient_id = email

    conn.execute(
        """
        INSERT INTO patients
        (
            name,
            age,
            phone,
            diagnosis,
            required_bed_type,
            admission_date,
            status,
            total_bill,
            login_id,
            password_hash,
            email,
            gender,
            address,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            age,
            phone,
            diagnosis or "Not specified",
            bed_type,
            "",
            "Registered",
            0,
            patient_id,
            generate_password_hash(password),
            email,
            gender,
            address,
            current_datetime()
        )
    )

    conn.commit()
    conn.close()

    print("\nPatient registered successfully!")
    print("Patient Name :", name)
    print("Patient ID   :", patient_id)
    print("Patient Email:", email)
    print("Required Bed :", bed_type)


# ==========================================================
# PATIENT LOGIN
# ==========================================================

def patient_login():

    heading("PATIENT LOGIN")

    email = get_input("Patient Email / Patient ID: ").lower()
    password = get_password("Enter password: ")

    conn = get_connection()

    patients = conn.execute(
        """
        SELECT * FROM patients
        WHERE LOWER(email) = ?
        ORDER BY id
        ORDER BY ID ASC
    
        """,
        (email,)
    ).fetchall()

    conn.close()

    matched_patient = None

    for patient in patients:

        if patient["password_hash"] and check_password_hash(
            patient["password_hash"], password
        ):
            matched_patient = patient
            break

    if matched_patient:

        print("\nPatient login successful!")
        print("Welcome,", matched_patient["name"])
        print("Patient ID:", matched_patient["email"])

        patient_menu(matched_patient)

    else:
        print("\nInvalid patient email or password.")


# ==========================================================
# ADMIN DASHBOARD
# ==========================================================

def admin_dashboard():

    heading("ADMIN DASHBOARD")

    conn = get_connection()

    total_wards = conn.execute(
        "SELECT COUNT(*) FROM wards"
    ).fetchone()[0]

    total_beds = conn.execute(
        "SELECT COUNT(*) FROM beds"
    ).fetchone()[0]

    admitted = conn.execute(
        """
        SELECT COUNT(*) FROM patients
        WHERE status = 'Admitted'
        """
    ).fetchone()[0]

    available = max(0, total_beds - admitted)

    total_patients = conn.execute(
        "SELECT COUNT(*) FROM patients"
    ).fetchone()[0]

    waiting = conn.execute(
        "SELECT COUNT(*) FROM waiting_list"
    ).fetchone()[0]

    revenue = conn.execute(
        """
        SELECT COALESCE(SUM(bill_amount), 0)
        FROM admissions
        """
    ).fetchone()[0]

    conn.close()

    occupancy = (
        admitted / total_beds * 100
        if total_beds > 0 else 0
    )

    print("Total Wards       :", total_wards)
    print("Total Beds        :", total_beds)
    print("Available Beds    :", available)
    print("Occupied Beds     :", admitted)
    print("Total Patients    :", total_patients)
    print("Waiting List      :", waiting)
    print("Occupancy Rate    : {:.2f}%".format(occupancy))
    print("Recorded Revenue  : Rs.", revenue)


# ==========================================================
# VIEW PATIENTS
# ==========================================================

def view_patients():

    heading("ALL REGISTERED PATIENTS")

    conn = get_connection()

    patients = conn.execute(
        """
        SELECT
            p.*,
            w.name AS ward_name,
            b.bed_number
        FROM patients p
        LEFT JOIN wards w ON p.ward_id = w.id
        LEFT JOIN beds b ON p.bed_id = b.id
        ORDER BY p.id ASC
        """
    ).fetchall()

    conn.close()

    if not patients:
        print("\nNo patients found.")
        return

    for p in patients:

        print("\n" + "-" * 50)

        print("Database Record ID:", p["id"])
        print("Patient Name      :", p["name"])
        print("Patient ID        :", p["email"])
        print("Patient Email     :", p["email"])
        print("Age               :", p["age"])
        print("Gender            :", p["gender"])
        print("Phone             :", p["phone"])
        print("Diagnosis         :", p["diagnosis"])
        print("Required Bed      :", p["required_bed_type"])
        print("Status            :", p["status"])
        print("Ward              :", p["ward_name"])
        print("Bed Number        :", p["bed_number"])


# ==========================================================
# ADD WARD
# ==========================================================

def add_ward():

    heading("ADD NEW WARD")

    name = get_input("Enter ward name: ")

    if not name:
        print("\nWard name cannot be empty.")
        return

    conn = get_connection()

    existing = conn.execute(
        """
        SELECT id FROM wards
        WHERE LOWER(name) = LOWER(?)
        """,
        (name,)
    ).fetchone()

    if existing:
        print("\nWard already exists.")
        conn.close()
        return

    conn.execute(
        """
        INSERT INTO wards (name, created_at)
        VALUES (?, ?)
        """,
        (name, current_datetime())
    )

    conn.commit()
    conn.close()

    print("\nWard added successfully!")


# ==========================================================
# ADD BEDS
# ==========================================================

def add_beds():

    heading("ADD BEDS")

    conn = get_connection()

    wards = conn.execute(
        "SELECT * FROM wards ORDER BY id"
    ).fetchall()

    if not wards:
        print("\nCreate a ward first.")
        conn.close()
        return

    print("\nAvailable Wards:")

    for ward in wards:
        print(ward["id"], "-", ward["name"])

    try:
        ward_id = int(get_input("\nEnter Ward ID: "))
        count = int(get_input("Number of beds: "))

    except ValueError:
        print("\nEnter valid numbers.")
        conn.close()
        return

    ward = conn.execute(
        "SELECT * FROM wards WHERE id = ?",
        (ward_id,)
    ).fetchone()

    if not ward or count <= 0:
        print("\nInvalid ward or bed count.")
        conn.close()
        return

    print("\nBed Types:")
    print("1. General")
    print("2. Semi-Private")
    print("3. ICU")

    choice = get_input("Select bed type: ")

    types = {
        "1": "General",
        "2": "Semi-Private",
        "3": "ICU"
    }

    if choice not in types:
        print("\nInvalid bed type.")
        conn.close()
        return

    bed_type = types[choice]

    for i in range(count):

        bed_number = get_input(
            f"Enter bed number {i + 1}: "
        )

        if not bed_number:
            print("Bed number cannot be empty.")
            continue

        duplicate = conn.execute(
            """
            SELECT id FROM beds
            WHERE ward_id = ? AND bed_number = ?
            """,
            (ward_id, bed_number)
        ).fetchone()

        if duplicate:
            print("This bed number already exists.")
            continue

        conn.execute(
            """
            INSERT INTO beds
            (ward_id, bed_number, bed_type, status)
            VALUES (?, ?, ?, 'Available')
            """,
            (ward_id, bed_number, bed_type)
        )

        print("Bed added successfully.")

    conn.commit()
    conn.close()


# ==========================================================
# VIEW BEDS
# ==========================================================

def view_beds():

    heading("BED DETAILS")

    conn = get_connection()

    beds = conn.execute(
        """
        SELECT
            b.*,
            w.name AS ward_name,
            p.name AS patient_name
        FROM beds b
        JOIN wards w ON b.ward_id = w.id
        LEFT JOIN patients p ON p.bed_id = b.id
        ORDER BY w.name, b.bed_number
        """
    ).fetchall()

    conn.close()

    if not beds:
        print("\nNo beds found.")
        return

    for bed in beds:

        print("\nWard       :", bed["ward_name"])
        print("Bed Number :", bed["bed_number"])
        print("Bed Type   :", bed["bed_type"])

        if bed["patient_name"]:
            print("Status     : Occupied")
            print("Patient    :", bed["patient_name"])
        else:
            print("Status     : Available")

        print("-" * 45)


# ==========================================================
# ADMIT PATIENT
# ==========================================================

def admit_patient():

    heading("ADMIT PATIENT")

    email = get_input("Enter Patient Email / ID: ").lower()

    conn = get_connection()

    patient = conn.execute(
        """
        SELECT * FROM patients
        WHERE LOWER(email) = ?
        ORDER BY id
        LIMIT 1
        """,
        (email,)
    ).fetchone()

    if not patient:
        print("\nPatient not found.")
        conn.close()
        return

    if patient["bed_id"] is not None:
        print("\nPatient already has a bed.")
        conn.close()
        return

    if patient["status"] == "Waiting":
        print("\nPatient is already in the waiting list.")
        conn.close()
        return

    bed_type = patient["required_bed_type"]

    bed = conn.execute(
        """
        SELECT b.*, w.name AS ward_name
        FROM beds b
        JOIN wards w ON b.ward_id = w.id
        WHERE b.bed_type = ?
        AND NOT EXISTS (
            SELECT 1
            FROM patients p
            WHERE p.bed_id = b.id
        )
        ORDER BY b.id
        LIMIT 1
        """,
        (bed_type,)
    ).fetchone()

    if not bed:

        conn.execute(
            """
            INSERT INTO waiting_list
            (patient_id, bed_type, requested_at)
            VALUES (?, ?, ?)
            """,
            (
                patient["id"],
                bed_type,
                current_datetime()
            )
        )

        conn.execute(
            """
            UPDATE patients
            SET status = 'Waiting'
            WHERE id = ?
            """,
            (patient["id"],)
        )

        conn.commit()
        conn.close()

        print("\nNo available", bed_type, "bed.")
        print("Patient added to waiting list.")
        return

    admission_date = current_datetime()

    conn.execute(
        """
        UPDATE beds
        SET status = 'Occupied'
        WHERE id = ?
        """,
        (bed["id"],)
    )

    conn.execute(
        """
        UPDATE patients
        SET
            ward_id = ?,
            bed_id = ?,
            admission_date = ?,
            discharge_date = NULL,
            status = 'Admitted'
        WHERE id = ?
        """,
        (
            bed["ward_id"],
            bed["id"],
            admission_date,
            patient["id"]
        )
    )

    conn.execute(
        """
        INSERT INTO admissions
        (
            patient_id,
            bed_id,
            ward_name,
            bed_number,
            bed_type,
            admission_date,
            status,
            rate_per_day,
            bill_amount
        )
        VALUES (?, ?, ?, ?, ?, ?, 'Admitted', ?, 0)
        """,
        (
            patient["id"],
            bed["id"],
            bed["ward_name"],
            bed["bed_number"],
            bed_type,
            admission_date,
            RATES[bed_type]
        )
    )

    conn.commit()
    conn.close()

    print("\nPatient admitted successfully!")
    print("Patient:", patient["name"])
    print("Patient ID:", patient["email"])
    print("Ward:", bed["ward_name"])
    print("Bed Number:", bed["bed_number"])
    print("Bed Type:", bed_type)
    print("Rate per day: Rs.", RATES[bed_type])


# ==========================================================
# DISCHARGE PATIENT
# ==========================================================

def discharge_patient():

    heading("DISCHARGE PATIENT")

    email = get_input("Enter Patient Email / ID: ").lower()

    conn = get_connection()

    patient = conn.execute(
        """
        SELECT * FROM patients
        WHERE LOWER(email) = ?
        ORDER BY id
        LIMIT 1
        """,
        (email,)
    ).fetchone()

    if not patient:
        print("\nPatient not found.")
        conn.close()
        return

    if patient["status"] != "Admitted" or patient["bed_id"] is None:
        print("\nPatient is not currently admitted.")
        conn.close()
        return

    admission = conn.execute(
        """
        SELECT * FROM admissions
        WHERE patient_id = ?
        AND status = 'Admitted'
        ORDER BY id DESC
        LIMIT 1
        """,
        (patient["id"],)
    ).fetchone()

    if not admission:
        print("\nActive admission record not found.")
        conn.close()
        return

    days = get_days(admission["admission_date"])
    bill = days * admission["rate_per_day"]

    discharge_time = current_datetime()

    bed_id = patient["bed_id"]
    bed_type = admission["bed_type"]

    conn.execute(
        """
        UPDATE admissions
        SET
            discharge_date = ?,
            status = 'Discharged',
            bill_amount = ?
        WHERE id = ?
        """,
        (
            discharge_time,
            bill,
            admission["id"]
        )
    )

    conn.execute(
        """
        UPDATE patients
        SET
            status = 'Discharged',
            discharge_date = ?,
            total_bill = COALESCE(total_bill, 0) + ?,
            bed_id = NULL,
            ward_id = NULL
        WHERE id = ?
        """,
        (
            discharge_time,
            bill,
            patient["id"]
        )
    )

    conn.execute(
        """
        UPDATE beds
        SET status = 'Available'
        WHERE id = ?
        """,
        (bed_id,)
    )

    conn.commit()

    print("\nPatient discharged successfully!")
    print("Patient:", patient["name"])
    print("Days:", days)
    print("Rate per day: Rs.", admission["rate_per_day"])
    print("Total bill: Rs.", bill)

    # FIFO waiting-list allocation.

    waiting = conn.execute(
        """
        SELECT
            wl.id AS waiting_id,
            wl.patient_id,
            p.name,
            p.required_bed_type
        FROM waiting_list wl
        JOIN patients p ON p.id = wl.patient_id
        WHERE wl.bed_type = ?
        ORDER BY wl.requested_at ASC, wl.id ASC
        LIMIT 1
        """,
        (bed_type,)
    ).fetchone()

    if waiting:

        freed_bed = conn.execute(
            """
            SELECT b.*, w.name AS ward_name
            FROM beds b
            JOIN wards w ON b.ward_id = w.id
            WHERE b.id = ?
            """,
            (bed_id,)
        ).fetchone()

        if freed_bed:

            new_admission_date = current_datetime()

            conn.execute(
                """
                UPDATE beds
                SET status = 'Occupied'
                WHERE id = ?
                """,
                (bed_id,)
            )

            conn.execute(
                """
                UPDATE patients
                SET
                    status = 'Admitted',
                    ward_id = ?,
                    bed_id = ?,
                    admission_date = ?,
                    discharge_date = NULL
                WHERE id = ?
                """,
                (
                    freed_bed["ward_id"],
                    bed_id,
                    new_admission_date,
                    waiting["patient_id"]
                )
            )

            conn.execute(
                """
                INSERT INTO admissions
                (
                    patient_id,
                    bed_id,
                    ward_name,
                    bed_number,
                    bed_type,
                    admission_date,
                    status,
                    rate_per_day,
                    bill_amount
                )
                VALUES (?, ?, ?, ?, ?, ?, 'Admitted', ?, 0)
                """,
                (
                    waiting["patient_id"],
                    bed_id,
                    freed_bed["ward_name"],
                    freed_bed["bed_number"],
                    freed_bed["bed_type"],
                    new_admission_date,
                    RATES[bed_type]
                )
            )

            conn.execute(
                """
                DELETE FROM waiting_list
                WHERE id = ?
                """,
                (waiting["waiting_id"],)
            )

            print("\nWaiting-list patient automatically admitted!")
            print("Patient:", waiting["name"])
            print("Bed:", freed_bed["bed_number"])

    conn.commit()
    conn.close()


# ==========================================================
# VIEW WAITING LIST
# ==========================================================

def view_waiting_list():

    heading("PATIENT WAITING LIST")

    conn = get_connection()

    waiting = conn.execute(
        """
        SELECT
            wl.*,
            p.name,
            p.email
        FROM waiting_list wl
        JOIN patients p ON p.id = wl.patient_id
        ORDER BY wl.requested_at ASC, wl.id ASC
        """
    ).fetchall()

    conn.close()

    if not waiting:
        print("\nWaiting list is empty.")
        return

    for position, item in enumerate(waiting, start=1):

        print("\nPosition:", position)
        print("Patient Name:", item["name"])
        print("Patient ID:", item["email"])
        print("Required Bed:", item["bed_type"])
        print("Requested At:", item["requested_at"])
        print("-" * 45)


# ==========================================================
# ADD DOCTOR CONSULTATION
# ==========================================================

def add_doctor_consultation():

    heading("ADD DOCTOR CONSULTATION")

    email = get_input("Patient Email / ID: ").lower()

    conn = get_connection()

    patient = conn.execute(
        """
        SELECT * FROM patients
        WHERE LOWER(email) = ?
        ORDER BY id
        LIMIT 1
        """,
        (email,)
    ).fetchone()

    if not patient:
        print("\nPatient not found.")
        conn.close()
        return

    doctor = get_input("Doctor name: ")
    department = get_input("Department: ")
    notes = get_input("Consultation notes: ")

    try:
        fee = float(get_input("Consultation fee: "))

        if fee < 0:
            print("Fee cannot be negative.")
            conn.close()
            return

    except ValueError:
        print("Enter a valid consultation fee.")
        conn.close()
        return

    conn.execute(
        """
        INSERT INTO doctor_consultations
        (
            patient_id,
            doctor_name,
            department,
            consultation_date,
            notes,
            consultation_fee
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            patient["id"],
            doctor,
            department,
            current_datetime(),
            notes,
            fee
        )
    )

    conn.commit()
    conn.close()

    print("\nDoctor consultation added successfully!")


# ==========================================================
# VIEW ALL DOCTOR CONSULTATIONS
# ==========================================================

def view_all_consultations():

    heading("ALL DOCTOR CONSULTATIONS")

    conn = get_connection()

    records = conn.execute(
        """
        SELECT
            dc.*,
            p.name AS patient_name,
            p.email AS patient_email
        FROM doctor_consultations dc
        JOIN patients p ON p.id = dc.patient_id
        ORDER BY dc.id DESC
        """
    ).fetchall()

    conn.close()

    if not records:
        print("\nNo consultations found.")
        return

    for record in records:

        print("\nPatient:", record["patient_name"])
        print("Patient ID:", record["patient_email"])
        print("Doctor:", record["doctor_name"])
        print("Department:", record["department"])
        print("Date:", record["consultation_date"])
        print("Notes:", record["notes"])
        print("Fee: Rs.", record["consultation_fee"])
        print("-" * 45)


# ==========================================================
# PATIENT DASHBOARD
# ==========================================================

def patient_dashboard(patient):

    heading("PATIENT DASHBOARD")

    conn = get_connection()

    current = conn.execute(
        """
        SELECT
            p.*,
            b.bed_number,
            b.bed_type,
            w.name AS ward_name
        FROM patients p
        LEFT JOIN beds b ON p.bed_id = b.id
        LEFT JOIN wards w ON p.ward_id = w.id
        WHERE p.id = ?
        """,
        (patient["id"],)
    ).fetchone()

    conn.close()

    if not current:
        print("\nPatient not found.")
        return

    print("Patient Name :", current["name"])
    print("Patient ID   :", current["email"])
    print("Email        :", current["email"])
    print("Age          :", current["age"])
    print("Gender       :", current["gender"])
    print("Phone        :", current["phone"])
    print("Diagnosis    :", current["diagnosis"])
    print("Status       :", current["status"])

    if current["bed_id"] is not None:

        print("\nCURRENT BED DETAILS")

        print("Ward      :", current["ward_name"])
        print("Bed Number:", current["bed_number"])
        print("Bed Type  :", current["bed_type"])

    else:

        print("\nNo bed currently allocated.")

    print("\nTotal Bill: Rs.", current["total_bill"])


# ==========================================================
# PATIENT ADMISSION HISTORY
# ==========================================================

def patient_admission_history(patient):

    heading("MY ADMISSION HISTORY")

    conn = get_connection()

    records = conn.execute(
        """
        SELECT * FROM admissions
        WHERE patient_id = ?
        ORDER BY id DESC
        """,
        (patient["id"],)
    ).fetchall()

    conn.close()

    if not records:
        print("\nNo admission history found.")
        return

    for record in records:

        print("\nWard:", record["ward_name"])
        print("Bed Number:", record["bed_number"])
        print("Bed Type:", record["bed_type"])
        print("Admission Date:", record["admission_date"])
        print("Discharge Date:", record["discharge_date"] or "Not discharged")
        print("Status:", record["status"])
        print("Rate Per Day: Rs.", record["rate_per_day"])
        print("Bill: Rs.", record["bill_amount"])
        print("-" * 45)


# ==========================================================
# PATIENT DOCTOR CONSULTATIONS
# ==========================================================

def patient_consultations(patient):

    heading("MY DOCTOR CONSULTATIONS")

    conn = get_connection()

    records = conn.execute(
        """
        SELECT * FROM doctor_consultations
        WHERE patient_id = ?
        ORDER BY id DESC
        """,
        (patient["id"],)
    ).fetchall()

    conn.close()

    if not records:
        print("\nNo doctor consultations found.")
        return

    for record in records:

        print("\nDoctor:", record["doctor_name"])
        print("Department:", record["department"])
        print("Date:", record["consultation_date"])
        print("Notes:", record["notes"])
        print("Consultation Fee: Rs.", record["consultation_fee"])
        print("-" * 45)


# ==========================================================
# ADMIN MENU
# ==========================================================

def admin_menu(admin):

    while True:

        heading("ADMIN CONTROL PANEL")

        print("Welcome:", admin["name"])
        print("Admin ID:", admin["email"])

        print("\n1. Dashboard")
        print("2. View All Patients")
        print("3. Add Ward")
        print("4. Add Beds")
        print("5. View Beds")
        print("6. Admit Patient")
        print("7. Discharge Patient")
        print("8. View Waiting List")
        print("9. Add Doctor Consultation")
        print("10. View Doctor Consultations")
        print("0. Logout")

        choice = get_input("\nEnter your choice: ")

        if choice == "1":
            admin_dashboard()
            pause()

        elif choice == "2":
            view_patients()
            pause()

        elif choice == "3":
            add_ward()
            pause()

        elif choice == "4":
            add_beds()
            pause()

        elif choice == "5":
            view_beds()
            pause()

        elif choice == "6":
            admit_patient()
            pause()

        elif choice == "7":
            discharge_patient()
            pause()

        elif choice == "8":
            view_waiting_list()
            pause()

        elif choice == "9":
            add_doctor_consultation()
            pause()

        elif choice == "10":
            view_all_consultations()
            pause()

        elif choice == "0":
            print("\nAdmin logged out successfully.")
            break

        else:
            print("\nInvalid choice.")


# ==========================================================
# PATIENT MENU
# ==========================================================

def patient_menu(patient):

    while True:

        heading("PATIENT PORTAL")

        print("Welcome:", patient["name"])
        print("Patient ID:", patient["email"])

        print("\n1. My Dashboard")
        print("2. My Admission History")
        print("3. My Doctor Consultations")
        print("0. Logout")

        choice = get_input("\nEnter your choice: ")

        if choice == "1":
            patient_dashboard(patient)
            pause()

        elif choice == "2":
            patient_admission_history(patient)
            pause()

        elif choice == "3":
            patient_consultations(patient)
            pause()

        elif choice == "0":
            print("\nPatient logged out successfully.")
            break

        else:
            print("\nInvalid choice.")


# ==========================================================
# MAIN FUNCTION
# ==========================================================

def main():

    init_db()

    # IMPORTANT:
    # Do not automatically update existing login_id values.
    # Existing duplicate admin emails are supported by checking
    # the password against all accounts with that email.
    #
    # Admin ID shown to the user = Admin Email.
    # Patient ID shown to the user = Patient Email.
    #
    # Existing records and passwords remain preserved.

    main_menu()


if __name__ == "__main__":
    main()
