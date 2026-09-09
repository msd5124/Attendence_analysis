# Student Attendance Business Analysis

A Flask + SQLite web application for a Business Analytics attendance project.

## Features
- Student name and roll number registration
- Analysis period selection
- Calendar covering **1 July 2026 – 30 September 2026**
- Sundays automatically marked as holidays
- Mark Saturday, local, festival and other holidays
- Mark present/absent dates
- Attendance percentage and summary
- Weekday absence pattern analysis
- 30-working-day attendance projection
- Practical recommendations
- CSV import for the **real attendance database** when it becomes available
- SQLite database created automatically
- Responsive mobile-friendly interface

## Run on Windows
1. Install Python 3.10+.
2. Open this project folder in VS Code.
3. Create a virtual environment:
   `py -m venv .venv`
4. Activate it:
   `.venv\\Scripts\\activate`
5. Install:
   `py -m pip install -r requirements.txt`
6. Run:
   `py app.py`
7. Open: http://127.0.0.1:5000

## Real data format
CSV columns:
`roll_no,name,date,status,holiday_type`

Status must be `PRESENT`, `ABSENT`, or `HOLIDAY`.

**Important:** Until the official class attendance data is available, entered calendar data is user-provided working data and should not be presented as official college attendance.
