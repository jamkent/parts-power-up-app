import sqlite3
import os
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
# SECRET_KEY is now read from environment variables
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a-default-secret-key-for-local-dev')
DATABASE = "rewards.db"

# --- Login Manager Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to /login if user is not authenticated

# --- User Model for Flask-Login ---
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

# --- Database Setup (Same as before) ---
EMPLOYEES_LIST = sorted([
    "Aaron O'Sullivan","Adam Mcguigan","Adrian Vladau","Amaan Satti","Anna Shaw", "Blake Erridge","Carl Atkins","Charlie Sneath","Claudiu Axinte","Cristina Constantinescu", "Dan Hitchcock","Daniel Waller","David Allcock","Dom Sparkes","Ed Simonaitis", "Emma Charles","Gaz Smith","Gavin Warrington","George Dooler","Graham Ross", "Glenn Walters","Ian Macpherson","Ioan Scurtu","Jake Mitchell","Jake Turner", "Jamie Chilcott","James Szerencses","Jarek Powaga","JERRY ATTIANAH","Jon Foggo", "Jon Mcfadyen","Jordan Bullen","Josh Prance","Justin Parsons","Kieran Carr", "Liam Murphy","Mari Belboda","Mark Mcdonald","Martin Wherrett","Matt Hollamby", "Matt Nolan","Matt Pike","Michael Quinn","Mike Watts","Nada Musa", "Neil Baker","Neil Ellis","Nicola Stennett-Bale","Phil Buckland","Rob Flinn", "Ryan Birkett","Sean Phipps","Shaun Kane","Shoeb Ahmed","Stephen Hopkins", "Umar Pervez","William Rutherford"
])

MANAGERS_LIST = {
    "jkent": {"name":"James Kent",      "hash": generate_password_hash(os.environ.get("PASS_JKENT", "localpass1"))},
    "aise":  {"name":"Andrei Isepciuc", "hash": generate_password_hash(os.environ.get("PASS_AISE",  "localpass2"))},
    "wwit":  {"name":"Wayne Withers",   "hash": generate_password_hash(os.environ.get("PASS_WWIT",  "localpass3"))},
    "spol":  {"name":"Steve Pollock",   "hash": generate_password_hash(os.environ.get("PASS_SPOL",  "localpass4"))},
    "jpow":  {"name":"Jarek Powaga",    "hash": generate_password_hash(os.environ.get("PASS_JPOW",  "localpass5"))},
    "pdool": {"name":"Paul Doolan",     "hash": generate_password_hash(os.environ.get("PASS_PDOOL", "localpass6"))},
    "cbird": {"name":"Craig Bird",      "hash": generate_password_hash(os.environ.get("PASS_CBIRD", "localpass7"))},
    "nmcc":  {"name":"Neil McCay",      "hash": generate_password_hash(os.environ.get("PASS_NMCC",  "localpass8"))}
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

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = load_user(username)
        if user and check_password_hash(user.hash, password):
            login_user(user) # Create a secure session
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

# --- Main execution ---
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)