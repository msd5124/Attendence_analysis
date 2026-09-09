const cal = document.getElementById('calendar');
let records = {};

let currentStart = new Date(START + 'T00:00:00');
let currentEnd = new Date(END + 'T00:00:00');

async function load() {
    const r = await fetch(
        `/api/attendance?student_id=${STUDENT_ID}&start=${START}&end=${END}`
    );

    (await r.json()).forEach(x => {
        records[x.attendance_date] = x;
    });

    render();
}

function iso(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');

    return `${y}-${m}-${day}`;
}

function render() {
    cal.innerHTML = '';

    let d = new Date(
        currentStart.getFullYear(),
        currentStart.getMonth(),
        1
    );

    while (d <= currentEnd) {

        const month = document.createElement('div');
        month.className = 'month';

        const title = document.createElement('h3');
        title.textContent = d.toLocaleString('en', {
            month: 'long',
            year: 'numeric'
        });

        month.appendChild(title);

        const ws = document.createElement('div');
        ws.className = 'weekdays';

        ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
            .forEach(x => {
                let e = document.createElement('div');
                e.textContent = x;
                ws.appendChild(e);
            });

        month.appendChild(ws);

        const days = document.createElement('div');
        days.className = 'days';

        // Get the correct weekday of the 1st day of the month
        const first = new Date(
            d.getFullYear(),
            d.getMonth(),
            1
        ).getDay();

        for (let i = 0; i < first; i++) {
            let e = document.createElement('div');
            e.className = 'day empty';
            days.appendChild(e);
        }

        const last = new Date(
            d.getFullYear(),
            d.getMonth() + 1,
            0
        ).getDate();

        for (let n = 1; n <= last; n++) {

            // IMPORTANT:
            // Create the date using local time, not UTC.
            const x = new Date(
                d.getFullYear(),
                d.getMonth(),
                n
            );

            if (x < currentStart || x > currentEnd)
                continue;

            const key = iso(x);

            let rec = records[key] || {
                status: x.getDay() === 0 ? 'HOLIDAY' : 'PRESENT',
                holiday_type: x.getDay() === 0 ? 'Sunday' : ''
            };

            let e = document.createElement('div');

            e.className = 'day ' + rec.status.toLowerCase();

            e.innerHTML = `
                <div class="num">${n}</div>
                <div class="status">
                    ${rec.status === 'HOLIDAY'
                        ? rec.holiday_type
                        : ' ' + rec.status}
                </div>
            `;

            e.onclick = () => edit(key, rec);

            days.appendChild(e);
        }

        month.appendChild(days);
        cal.appendChild(month);

        d = new Date(
            d.getFullYear(),
            d.getMonth() + 1,
            1
        );
    }
}

function edit(key, rec) {

    const m = document.createElement('div');

    m.className = 'modal';

    m.innerHTML = `
        <div class="modalbox">

            <button class="close">×</button>

            <h3>${key}</h3>

            <p>Select the correct status.</p>

            <button data-s="PRESENT">
                Present
            </button>

            <button data-s="ABSENT">
                Absent
            </button>

            <button data-s="HOLIDAY">
                Holiday
            </button>

            <div id="holidayChoices"
                 style="display:none;margin-top:12px">

                <label>Holiday type</label>

                <select>

                    <option value="Saturday">
                        Saturday
                    </option>

                    <option value="Local Holiday">
                        Local Holiday
                    </option>

                    <option value="Festival Holiday">
                        Festival Holiday
                    </option>

                    <option value="Other">
                        Other
                    </option>

                </select>

                <br>

                <button id="confirmHoliday">
                    Save Holiday
                </button>

            </div>

        </div>
    `;

    document.body.appendChild(m);

    m.querySelector('.close').onclick = () => {
        m.remove();
    };

    m.querySelectorAll('[data-s]').forEach(b => {

        b.onclick = async () => {

            let s = b.dataset.s;

            // When Holiday is clicked,
            // SHOW holiday choices instead of
            // automatically selecting Saturday.
            if (s === 'HOLIDAY') {

                m.querySelector('#holidayChoices')
                    .style.display = 'block';

                m.querySelector(
                    '[data-s="HOLIDAY"]'
                ).style.display = 'none';

                return;
            }

            await save(key, s, '');

            m.remove();
        };
    });

    m.querySelector('#confirmHoliday').onclick = async () => {

        const h =
            m.querySelector(
                '#holidayChoices select'
            ).value;

        await save(
            key,
            'HOLIDAY',
            h
        );

        m.remove();
    };
}

async function save(key, status, h) {

    await fetch('/api/attendance', {
        method: 'POST',

        headers: {
            'Content-Type': 'application/json'
        },

        body: JSON.stringify({
            student_id: STUDENT_ID,
            date: key,
            status: status,
            holiday_type: h
        })
    });

    records[key] = {
        status: status,
        holiday_type: h
    };

    render();
}

document.getElementById('analyze').onclick = () => {

    location.href =
        `/analyze?student_id=${STUDENT_ID}&start=${START}&end=${END}`;
};

load();
