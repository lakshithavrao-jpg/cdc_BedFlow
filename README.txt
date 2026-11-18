BEDFLOW
Hospital Bed Allocation and Patient Management System


PROJECT REQUIREMENTS

Python 3
Flask
SQLite


PROJECT FEATURES

1. Separate patient and admin registration.
2. Separate patient and admin login.
3. Automatic login ID generation.
4. Patient dashboard.
5. Admin dashboard.
6. Patient information management.
7. Bed and ward management.
8. Patient admission.
9. Patient discharge.
10. Admission history.
11. Billing calculation.
12. Password change functionality.


HOW TO RUN THE PROJECT

STEP 1:

Open the BedFlow project folder in VS Code.


STEP 2:

Open the VS Code terminal.


STEP 3:

Create a virtual environment:

python -m venv .venv


STEP 4:

Install the requirements:

.\.venv\Scripts\python.exe -m pip install -r requirements.txt


STEP 5:

Run the application:

.\.venv\Scripts\python.exe app.py


STEP 6:

Open the browser and visit:

http://127.0.0.1:5000


DEFAULT ADMIN LOGIN

Login ID: ADMIN001

Password: Admin@123


PATIENT REGISTRATION

Patients can register through the Create Account page.

A unique Patient ID is automatically generated.

Example:

PT000001


ADMIN REGISTRATION

Administrators can register through the same registration page.

A unique Admin ID is automatically generated.

Example:

ADMIN000002


DATABASE

The SQLite database is automatically created as:

bedflow.db

It is stored inside the main project folder.


BED TYPES AND DAILY RATES

General: Rs. 1000 per day

Semi-Private: Rs. 2000 per day

ICU: Rs. 5000 per day


DEFAULT BED INVENTORY

General Ward: 5 beds

Private Care Ward: 3 beds

Critical Care Unit: 2 beds


NOTE

This is an educational academic project.

It is not intended for production hospital use.