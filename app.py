from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)
    conn.commit()
    conn.close()

def init_login_activity():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS login_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            role TEXT,
            login_time TEXT,
            logout_time TEXT
        )
    """)
    conn.commit()
    conn.close()

def init_tasks():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee TEXT,
            task TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_sample_users():
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO users VALUES (NULL,'admin','admin123','admin')")
    conn.execute("INSERT OR IGNORE INTO users VALUES (NULL,'manager','manager123','manager')")
    conn.execute("INSERT OR IGNORE INTO users VALUES (NULL,'employee','emp123','employee')")
    conn.commit()
    conn.close()

# ---- INIT CALLS ----
init_db()
init_login_activity()
init_tasks()
insert_sample_users()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():

    if "role" in session:
        return redirect(url_for(f"{session['role']}_dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        if user:
            login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn.execute(
                "INSERT INTO login_activity (username, role, login_time, logout_time) VALUES (?, ?, ?, NULL)",
                (user["username"], user["role"], login_time)
            )
            conn.commit()
            conn.close()

            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for(f"{user['role']}_dashboard"))

        conn.close()
        return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    admins = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
    managers = conn.execute("SELECT COUNT(*) FROM users WHERE role='manager'").fetchone()[0]
    employees = conn.execute("SELECT COUNT(*) FROM users WHERE role='employee'").fetchone()[0]
    conn.close()

    return render_template("admin_dashboard.html",
        total=total,
        admins=admins,
        managers=managers,
        employees=employees
    )

# ---------------- USERS ----------------
@app.route("/users")
def users():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    users = conn.execute("SELECT username, role FROM users").fetchall()
    conn.close()
    return render_template("users.html", users=users)

@app.route("/add_employee", methods=["GET", "POST"])
def add_employee():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, 'employee')",
                (request.form["username"], request.form["password"])
            )
            conn.commit()
            conn.close()
            return redirect(url_for("users"))
        except sqlite3.IntegrityError:
            return render_template("add_employee.html", error="Username already exists")

    return render_template("add_employee.html")



# ---------------- MANAGER DASHBOARD ----------------
@app.route("/manager")
def manager_dashboard():
    if session.get("role") != "manager":
        return redirect(url_for("login"))

    conn = get_db()

    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    admins = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
    managers = conn.execute("SELECT COUNT(*) FROM users WHERE role='manager'").fetchone()[0]
    employee_count = conn.execute("SELECT COUNT(*) FROM users WHERE role='employee'").fetchone()[0]
    total_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    pending_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Pending'").fetchone()[0]
    completed_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Completed'").fetchone()[0]


    employees = conn.execute(
        "SELECT username FROM users WHERE role='employee'"
    ).fetchall()

    activity = conn.execute(
        """
        SELECT username, login_time, logout_time
        FROM login_activity
        WHERE role='employee'
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "manager_dashboard.html",
        total=total,
        admins=admins,
        managers=managers,
        employee_count=employee_count,
        total_tasks=total_tasks,
        pending_tasks=pending_tasks,
        completed_tasks=completed_tasks,
        employees=employees,
        activity=activity
    )

# ---------------- ASSIGN TASK ----------------
@app.route("/assign_task", methods=["GET", "POST"])
def assign_task():
    if session.get("role") != "manager":
        return redirect(url_for("login"))

    conn = get_db()
    employees = conn.execute(
        "SELECT username FROM users WHERE role='employee'"
    ).fetchall()

    if request.method == "POST":
        conn.execute(
            "INSERT INTO tasks (employee, task, status) VALUES (?, ?, 'Pending')",
            (request.form["employee"], request.form["task"])
        )
        conn.commit()
        conn.close()
        return redirect(url_for("manager_dashboard"))

    conn.close()
    return render_template("assign_task.html", employees=employees)

# ---------------- REPORTS ----------------
@app.route("/reports")
def reports_page():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    admins = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
    managers = conn.execute("SELECT COUNT(*) FROM users WHERE role='manager'").fetchone()[0]
    employees = conn.execute("SELECT COUNT(*) FROM users WHERE role='employee'").fetchone()[0]
    activity = conn.execute(
        "SELECT username, role, login_time, logout_time FROM login_activity ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template("reports.html",
        total=total,
        admins=admins,
        managers=managers,
        employees=employees,
        activity=activity
    )

# ---------------- EMPLOYEE DASHBOARD ----------------
@app.route("/employee")
def employee_dashboard():
    if session.get("role") != "employee":
        return redirect(url_for("login"))

    conn = get_db()

    assigned = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE employee=?",
        (session["username"],)
    ).fetchone()[0]

    pending = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE employee=? AND status='Pending'",
        (session["username"],)
    ).fetchone()[0]

    completed = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE employee=? AND status='Completed'",
        (session["username"],)
    ).fetchone()[0]

    conn.close()

    return render_template(
        "employee_dashboard.html",
        assigned=assigned,
        pending=pending,
        completed=completed
    )


@app.route("/employee/tasks")
def employee_tasks():
    if session.get("role") != "employee":
        return redirect(url_for("login"))

    conn = get_db()
    tasks = conn.execute(
        "SELECT id, task, status FROM tasks WHERE employee=?",
        (session["username"],)
    ).fetchall()

    conn.close()


    return render_template("employee_tasks.html", tasks=tasks)

@app.route("/debug_tasks")
def debug_tasks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return str([dict(r) for r in rows])


@app.route("/complete_task/<int:task_id>")
def complete_task(task_id):
    if session.get("role") != "employee":
        return redirect(url_for("login"))

    conn = get_db()
    conn.execute(
        "UPDATE tasks SET status='Completed' WHERE id=? AND employee=?",
        (task_id, session["username"])
    )
    conn.commit()
    conn.close()

    return redirect(url_for("employee_tasks"))


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    if "username" in session:
        conn = get_db()
        conn.execute(
            """
            UPDATE login_activity
            SET logout_time = ?
            WHERE username = ? AND logout_time IS NULL
            """,
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session["username"])
        )
        conn.commit()
        conn.close()

    session.clear()
    return redirect(url_for("login"))

# ---------------- 404 ----------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(debug=True)
