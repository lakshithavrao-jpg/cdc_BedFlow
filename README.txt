BEDFLOW
Hospital Bed Allocation and Occupancy Management System

PROJECT OVERVIEW

BedFlow is a hospital bed management application.
It helps manage patient admission, bed availability,
patient records, discharge and waiting lists.

TECHNOLOGIES

1. Python
2. Flask
3. SQLite
4. HTML
5. CSS
6. JavaScript

MODULES

1. Dashboard
2. Patient Admission
3. Bed Allocation
4. Bed Availability
5. Patient Records
6. Patient Discharge
7. Patient Transfer
8. FIFO Waiting List

DEFAULT HOSPITAL CONFIGURATION

General Ward: 5 beds
Private Care Ward: 3 beds
Critical Care Unit: 2 beds

DAILY BED RATES (ILLUSTRATIVE)

General: Rs. 1000
Semi-Private: Rs. 2000
ICU: Rs. 5000

HOW TO RUN

1. Open the BedFlow folder in VS Code.
2. Open the terminal.
3. Create a virtual environment:

   python -m venv .venv

4. Install dependencies:

   .\.venv\Scripts\python.exe -m pip install -r requirements.txt

5. Run the application:

   .\.venv\Scripts\python.exe app.py

6. Open the browser:

   http://127.0.0.1:5000

DATABASE

The SQLite database file bedflow.db is created
automatically when the application starts for
the first time.

NOTE

This is an academic demonstration project.
It is not production-ready healthcare software.
Use fictional patient information.