from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_file
import sqlite3, os, csv, io
from datetime import date, datetime, timedelta
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'attendance.db')
START_DATE = date(2026, 7, 1)
END_DATE = date(2026, 9, 30)

app = Flask(__name__)
app.secret_key = 'attendance-business-analysis-2026'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        attendance_date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('PRESENT','ABSENT','HOLIDAY')),
        holiday_type TEXT DEFAULT '',
        UNIQUE(student_id, attendance_date),
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_att_student_date ON attendance(student_id, attendance_date);
    ''')
    conn.commit(); conn.close()


def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


def parse_date(s):
    return datetime.strptime(s, '%Y-%m-%d').date()


def default_status(d):
    return ('HOLIDAY', 'Sunday') if d.weekday() == 6 else ('PRESENT', '')


def ensure_period(student_id, start, end):
    conn = get_db()
    for d in daterange(start, end):
        status, htype = default_status(d)
        conn.execute('''INSERT OR IGNORE INTO attendance
            (student_id, attendance_date, status, holiday_type) VALUES (?, ?, ?, ?)''',
            (student_id, d.isoformat(), status, htype))
    conn.commit(); conn.close()


def find_student(roll_no, name):
    conn = get_db()
    row = conn.execute('SELECT * FROM students WHERE roll_no=?', (roll_no.strip(),)).fetchone()
    if row and row['name'].strip().lower() != name.strip().lower():
        conn.close(); return None, 'Roll number exists with a different name.'
    if not row:
        try:
            cur = conn.execute('INSERT INTO students(roll_no,name,created_at) VALUES(?,?,?)',
                               (roll_no.strip(), name.strip(), datetime.now().isoformat(timespec='seconds')))
            conn.commit()
            row = conn.execute('SELECT * FROM students WHERE id=?', (cur.lastrowid,)).fetchone()
        except sqlite3.IntegrityError:
            row = conn.execute('SELECT * FROM students WHERE roll_no=?', (roll_no.strip(),)).fetchone()
    conn.close()
    return row, None


def analyze(student_id, start, end):
    conn = get_db()
    rows = conn.execute('''SELECT attendance_date,status,holiday_type FROM attendance
                           WHERE student_id=? AND attendance_date BETWEEN ? AND ?
                           ORDER BY attendance_date''', (student_id, start.isoformat(), end.isoformat())).fetchall()
    conn.close()
    working = [r for r in rows if r['status'] != 'HOLIDAY']
    present = sum(r['status'] == 'PRESENT' for r in working)
    absent = sum(r['status'] == 'ABSENT' for r in working)
    holidays = [r for r in rows if r['status'] == 'HOLIDAY']
    total = len(working)
    pct = round((present / total * 100), 2) if total else 0
    weekday_abs = Counter()
    weekday_total = Counter()
    for r in working:
        d = parse_date(r['attendance_date'])
        weekday_total[d.strftime('%A')] += 1
        if r['status'] == 'ABSENT': weekday_abs[d.strftime('%A')] += 1
    weekday_data = []
    for day in ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']:
        t = weekday_total[day]; a = weekday_abs[day]
        weekday_data.append({'day': day, 'total': t, 'absent': a, 'rate': round(a/t*100,2) if t else 0})
    top_day = max(weekday_data, key=lambda x: (x['absent'], x['rate'])) if weekday_data else None
    holiday_counts = Counter(r['holiday_type'] or 'Other' for r in holidays)
    # Projection: if the same absence rate continues for the next 30 working days.
    absence_rate = absent / total if total else 0
    future_working = 30
    projected_additional_absent = round(future_working * absence_rate)
    projected_present = present + (future_working - projected_additional_absent)
    projected_total = total + future_working
    projected_pct = round(projected_present / projected_total * 100, 2) if projected_total else 0
    target = 75
    needed = max(0, int(__import__('math').ceil((target/100*total - present) / (1-target/100)))) if total else 0
    return {
        'total_days': total, 'present': present, 'absent': absent, 'holidays': len(holidays),
        'percentage': pct, 'weekday_data': weekday_data, 'top_day': top_day,
        'holiday_counts': dict(holiday_counts), 'projection_days': future_working,
        'projected_absent': projected_additional_absent, 'projected_percentage': projected_pct,
        'needed_present_for_75': needed, 'start': start.isoformat(), 'end': end.isoformat()
    }


@app.route('/')
def index():
    return render_template('index.html', min_date=START_DATE.isoformat(), max_date=END_DATE.isoformat())


@app.route('/setup', methods=['POST'])
def setup():
    name = request.form.get('name','').strip(); roll = request.form.get('roll_no','').strip()
    start = parse_date(request.form['start_date']); end = parse_date(request.form['end_date'])
    if not name or not roll or start < START_DATE or end > END_DATE or start > end:
        flash('Enter valid student details and a date range between 1 July and 30 September 2026.')
        return redirect(url_for('index'))
    student, err = find_student(roll, name)
    if err: flash(err); return redirect(url_for('index'))
    ensure_period(student['id'], start, end)
    return redirect(url_for('calendar', student_id=student['id'], start=start.isoformat(), end=end.isoformat()))


@app.route('/calendar')
def calendar():
    student_id = int(request.args['student_id']); start=request.args['start']; end=request.args['end']
    conn=get_db(); student=conn.execute('SELECT * FROM students WHERE id=?',(student_id,)).fetchone(); conn.close()
    if not student: return redirect(url_for('index'))
    return render_template('calendar.html', student=student, start=start, end=end,
                           min_date=START_DATE.isoformat(), max_date=END_DATE.isoformat())


@app.route('/api/attendance', methods=['GET','POST'])
def attendance_api():
    if request.method == 'POST':
        data=request.get_json(force=True)
        student_id=int(data['student_id']); d=data['date']; status=data['status']; htype=data.get('holiday_type','')
        if parse_date(d) < START_DATE or parse_date(d) > END_DATE:
            return jsonify({'error':'Date outside project calendar'}), 400
        if status not in ('PRESENT','ABSENT','HOLIDAY'):
            return jsonify({'error':'Invalid status'}),400
        if status == 'HOLIDAY' and not htype: htype='Local/Festival Holiday'
        if status != 'HOLIDAY': htype=''
        conn=get_db(); conn.execute('''INSERT INTO attendance(student_id,attendance_date,status,holiday_type)
            VALUES(?,?,?,?) ON CONFLICT(student_id,attendance_date) DO UPDATE SET status=excluded.status, holiday_type=excluded.holiday_type''',
            (student_id,d,status,htype)); conn.commit(); conn.close()
        return jsonify({'ok':True})
    student_id=int(request.args['student_id']); start=parse_date(request.args['start']); end=parse_date(request.args['end'])
    conn=get_db(); rows=conn.execute('SELECT attendance_date,status,holiday_type FROM attendance WHERE student_id=? AND attendance_date BETWEEN ? AND ?',
        (student_id,start.isoformat(),end.isoformat())).fetchall(); conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/analyze')
def results():
    student_id=int(request.args['student_id']); start=parse_date(request.args['start']); end=parse_date(request.args['end'])
    conn=get_db(); student=conn.execute('SELECT * FROM students WHERE id=?',(student_id,)).fetchone(); conn.close()
    if not student: return redirect(url_for('index'))
    ensure_period(student_id,start,end)
    data=analyze(student_id,start,end)
    return render_template('results.html', student=student, data=data)


@app.route('/upload-csv', methods=['POST'])
def upload_csv():
    f=request.files.get('file')
    if not f: flash('Choose a CSV file.'); return redirect(url_for('index'))
    text=f.stream.read().decode('utf-8-sig')
    reader=csv.DictReader(io.StringIO(text))
    required={'roll_no','name','date','status'}
    if not required.issubset(set(reader.fieldnames or [])):
        flash('CSV must contain: roll_no,name,date,status, and optional holiday_type.')
        return redirect(url_for('index'))
    count=0
    for r in reader:
        try:
            student,_=find_student(r['roll_no'],r['name'])
            d=parse_date(r['date']); status=r['status'].strip().upper(); h=r.get('holiday_type','')
            if d<START_DATE or d>END_DATE or status not in ('PRESENT','ABSENT','HOLIDAY'): continue
            conn=get_db(); conn.execute('''INSERT INTO attendance(student_id,attendance_date,status,holiday_type)
                VALUES(?,?,?,?) ON CONFLICT(student_id,attendance_date) DO UPDATE SET status=excluded.status, holiday_type=excluded.holiday_type''',
                (student['id'],d.isoformat(),status,h if status=='HOLIDAY' else '')); conn.commit(); conn.close(); count+=1
        except Exception: pass
    flash(f'Imported {count} attendance records.')
    return redirect(url_for('index'))


@app.route('/download-template')
def download_template():
    content='roll_no,name,date,status,holiday_type\n23CSE001,Example Student,2026-07-01,PRESENT,\n23CSE001,Example Student,2026-07-05,HOLIDAY,Sunday\n'
    return send_file(io.BytesIO(content.encode()), mimetype='text/csv', as_attachment=True, download_name='attendance_template.csv')


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
