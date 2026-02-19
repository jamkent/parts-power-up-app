from app import app, db
from app import Employee, Points, Log, Manager

def populate_db():
    # Drop existing tables (for development only)
    db.drop_all()
    db.create_all()

    # Add employees
    EMPLOYEES = [
        "Aaron O'Sullivan", "Adam Mcguigan", "Adrian Vladau", "Amaan Satti",
        "Anna Shaw", "Andrew Hoare", "Claudiu Axinte", "Cristina Constantinescu",
        "David Allcock", "Daniel Waller", "Dom Sparkes", "Ed Simonaitis",
        "Emma Charles", "Gaz Smith", "George Dooler", "Glenn Walters",
        "Graham Ross", "Ian Macpherson", "Jake Mitchell", "Jake Turner",
        "James Szerencses", "Jordan Bullen", "Kieran Carr", "Matt Hollamby",
        "Matt Nolan", "Matt Pike", "Matthew Gartside", "Mike Watts",
        "Nicola Stennett-Bale", "Nada Musa", "Neil Baker", "Neil Ellis",
        "Nick Lucas", "Phil Buckland", "Ryan Birkett", "Sean Phipps",
        "Shaun Kane", "Shoeb Ahmed", "Stephen Hopkins", "Umar Pervez",
        "William Rutherford", "Josh Prance", "Justin Parsons", "Liam Murphy",
        "Dan Hitchcock", "Jon Foggo", "Jon Mcfadyen", "JERRY ATTIANAH",
        "Mari Belboda", "Rob Flinn", "Carl Atkins", "Charlie Sneath"
    ]

    for name in EMPLOYEES:
        db.session.add(Employee(name=name))
    db.session.commit()
    print("✅ Employees and database initialized successfully!")

if __name__ == "__main__":
    with app.app_context():
        populate_db()