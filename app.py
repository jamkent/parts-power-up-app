import sqlite3
import os
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a-default-secret-key-for-local-dev')
DATABASE = "rewards_v2.db"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, name, hash):
        self.id = id
        self.name = name
        self.hash = hash

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    mgr = db.execute("SELECT * FROM managers WHERE username = ?", (user_id,)).fetchone()
    db.close()
    if mgr:
        return User(id=mgr['username'], name=mgr['name'], hash=mgr['hash'])
    return None

EMPLOYEES_LIST = [f"Employee {i:02d}" for i in range(1, 58)]
MANAGERS_LIST = {
    "manager01": {"name":"Manager 01", "hash": generate_password_hash(os.environ.get("PASS_MANAGER01", "localpass1"))},
    "manager02": {"name":"Manager 02", "hash": generate_password_hash(os.environ.get("PASS_MANAGER02", "localpass2"))},
    "manager03": {"name":"Manager 03", "hash": generate_password_hash(os.environ.get("PASS_MANAGER03", "localpass3"))},
    "manager04": {"name":"Manager 04", "hash": generate_password_hash(os.environ.get("PASS_MANAGER04", "localpass4"))},
    "manager05": {"name":"Manager 05", "hash": generate_password_hash(os.environ.get("PASS_MANAGER05", "localpass5"))},
    "manager06": {"name":"Manager 06", "hash": generate_password_hash(os.environ.get("PASS_MANAGER06", "localpass6"))},
    "manager07": {"name":"Manager 07", "hash": generate_password_hash(os.environ.get("PASS_MANAGER07", "localpass7"))},
    "manager08": {"name":"Manager 08", "hash": generate_password_hash(os.environ.get("PASS_MANAGER08", "localpass8"))}
}

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employees'")
        if cursor.fetchone() is not None:
            db.close()
            return
        print("Database not found. Creating and populating tables...")
        cursor.execute("CREATE TABLE employees (name TEXT PRIMARY KEY, points INTEGER NOT NULL DEFAULT 0)")
        cursor.execute("CREATE TABLE logs (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_name TEXT NOT NULL, timestamp TEXT NOT NULL, manager TEXT NOT NULL, action TEXT NOT NULL, reason TEXT NOT NULL, FOREIGN KEY (employee_name) REFERENCES employees (name))")
        cursor.execute("CREATE TABLE managers (username TEXT PRIMARY KEY, name TEXT NOT NULL, hash TEXT NOT NULL)")
        for emp in EMPLOYEES_LIST:
            cursor.execute("INSERT INTO employees (name, points) VALUES (?, ?)", (emp, 0))
        for username, data in MANAGERS_LIST.items():
            cursor.execute("INSERT INTO managers (username, name, hash) VALUES (?, ?, ?)", (username, data['name'], data['hash']))
        db.commit()
        db.close()
        print("Database initialized successfully.")

# --- NEW PUBLIC ROUTE ---
@app.route('/view')
def public_view():
    """A public, read-only view for everyone."""
    return render_template('public_view.html')

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = load_user(username)
        if user and check_password_hash(user.hash, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Protected Application Routes ---
@app.route("/")
@login_required
def home():
    return render_template("index.html")

# --- API Routes ---
@app.route("/api/all_data")
def get_all_data():
    """A public API endpoint to get all employee points."""
    db = get_db()
    all_employees = db.execute("SELECT name, points FROM employees ORDER BY points DESC, name ASC").fetchall()
    db.close()
    return jsonify([dict(row) for row in all_employees])

@app.route("/api/employees")
@login_required
def get_employees():
    db = get_db()
    employees = db.execute("SELECT name FROM employees ORDER BY name").fetchall()
    db.close()
    return jsonify([row['name'] for row in employees])

@app.route("/api/data/<employee>")
@login_required
def get_employee_data(employee):
    db = get_db()
    emp_data = db.execute("SELECT points FROM employees WHERE name = ?", (employee,)).fetchone()
    logs = db.execute("SELECT * FROM logs WHERE employee_name = ? ORDER BY timestamp DESC", (employee,)).fetchall()
    db.close()
    if not emp_data: return jsonify({"points": 0, "logs": []})
    return jsonify({"points": emp_data['points'], "logs": [dict(row) for row in logs]})

def modify_points(employee, amount, manager, reason, action_text):
    db = get_db()
    cursor = db.cursor()
    try:
        current_points = cursor.execute("SELECT points FROM employees WHERE name = ?", (employee,)).fetchone()['points']
        new_points = max(0, current_points + amount)
        cursor.execute("UPDATE employees SET points = ? WHERE name = ?", (new_points, employee))
        log_entry = (employee, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), manager, f"{action_text} {abs(amount)} points", reason)
        cursor.execute("INSERT INTO logs (employee_name, timestamp, manager, action, reason) VALUES (?, ?, ?, ?, ?)", log_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
    return jsonify({"success": True})

@app.route("/api/add", methods=["POST"])
@login_required
def add_points():
    data = request.json
    return modify_points(data.get("employee"), int(data.get("amount", 0)), current_user.name, data.get("reason"), "Added")

@app.route("/api/remove", methods=["POST"])
@login_required
def remove_points():
    data = request.json
    return modify_points(data.get("employee"), -int(data.get("amount", 0)), current_user.name, data.get("reason"), "Removed")

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)