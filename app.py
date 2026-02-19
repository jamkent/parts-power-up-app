import sqlite3
import os
from flask import Flask, jsonify, request, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
DATABASE = "rewards.db"

# --- Employee and Manager data (used for initial setup) ---
EMPLOYEES_LIST = sorted([
    "Aaron O'Sullivan","Adam Mcguigan","Adrian Vladau","Amaan Satti","Anna Shaw", "Blake Erridge","Carl Atkins","Charlie Sneath","Claudiu Axinte","Cristina Constantinescu", "Dan Hitchcock","Daniel Waller","David Allcock","Dom Sparkes","Ed Simonaitis", "Emma Charles","Gaz Smith","Gavin Warrington","George Dooler","Graham Ross", "Glenn Walters","Ian Macpherson","Ioan Scurtu","Jake Mitchell","Jake Turner", "Jamie Chilcott","James Szerencses","Jarek Powaga","JERRY ATTIANAH","Jon Foggo", "Jon Mcfadyen","Jordan Bullen","Josh Prance","Justin Parsons","Kieran Carr", "Liam Murphy","Mari Belboda","Mark Mcdonald","Martin Wherrett","Matt Hollamby", "Matt Nolan","Matt Pike","Michael Quinn","Mike Watts","Nada Musa", "Neil Baker","Neil Ellis","Nicola Stennett-Bale","Phil Buckland","Rob Flinn", "Ryan Birkett","Sean Phipps","Shaun Kane","Shoeb Ahmed","Stephen Hopkins", "Umar Pervez","William Rutherford"
])

MANAGERS_LIST = {
    # In a real app, passwords should come from secure environment variables.
    "jkent": {"name":"James Kent","hash": generate_password_hash("TeslaManage1")},
    "aise": {"name":"Andrei Isepciuc","hash": generate_password_hash("TeslaManage2")},
    "wwit": {"name":"Wayne Withers","hash": generate_password_hash("TeslaManage3")},
    "spol": {"name":"Steve Pollock","hash": generate_password_hash("TeslaManage4")},
    "jpow": {"name":"Jarek Powaga","hash": generate_password_hash("TeslaManage5")},
    "pdool": {"name":"Paul Doolan","hash": generate_password_hash("TeslaManage6")},
    "cbird": {"name":"Craig Bird","hash": generate_password_hash("TeslaManage7")},
    "nmcc": {"name":"Neil McCay","hash": generate_password_hash("TeslaManage8")}
}

# --- Database Helper Functions ---
def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        # Check if the 'employees' table exists. If not, the DB is new.
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employees'")
        if cursor.fetchone() is not None:
            db.close()
            return # Database already initialized

        print("Database not found. Creating and populating tables...")
        
        # Create tables
        cursor.execute("""
        CREATE TABLE employees (
            name TEXT PRIMARY KEY,
            points INTEGER NOT NULL DEFAULT 0
        )""")
        cursor.execute("""
        CREATE TABLE logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            manager TEXT NOT NULL,
            action TEXT NOT NULL,
            reason TEXT NOT NULL,
            FOREIGN KEY (employee_name) REFERENCES employees (name)
        )""")
        cursor.execute("""
        CREATE TABLE managers (
            username TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            hash TEXT NOT NULL
        )""")

        # Populate tables
        for emp in EMPLOYEES_LIST:
            cursor.execute("INSERT INTO employees (name, points) VALUES (?, ?)", (emp, 0))
        for username, data in MANAGERS_LIST.items():
            cursor.execute("INSERT INTO managers (username, name, hash) VALUES (?, ?, ?)", (username, data['name'], data['hash']))
        
        db.commit()
        db.close()
        print("Database initialized successfully.")

# --- Routes (No changes needed here) ---
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/employees")
def get_employees():
    db = get_db()
    employees = db.execute("SELECT name FROM employees ORDER BY name").fetchall()
    db.close()
    return jsonify([row['name'] for row in employees])

@app.route("/api/data/<employee>")
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
def add_points():
    data = request.json
    return modify_points(data.get("employee"), int(data.get("amount", 0)), data.get("manager"), data.get("reason"), "Added")

@app.route("/api/remove", methods=["POST"])
def remove_points():
    data = request.json
    return modify_points(data.get("employee"), -int(data.get("amount", 0)), data.get("manager"), data.get("reason"), "Removed")

@app.route("/api/login", methods=["POST"])
def manager_login():
    data = request.json
    username, password = data.get("username"), data.get("password")
    db = get_db()
    mgr = db.execute("SELECT * FROM managers WHERE username = ?", (username,)).fetchone()
    db.close()
    if not mgr or not check_password_hash(mgr['hash'], password):
        return jsonify({"error": "Invalid"}), 401
    return jsonify({"username": mgr['username'], "name": mgr['name']})

# --- Initialize DB on startup and run app ---
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)