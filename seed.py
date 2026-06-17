# seed.py - SQLite Database Seeding Script
import sqlite3
from werkzeug.security import generate_password_hash
import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_FILE = os.getenv('SQLITE_DB', 'municipal_db.sqlite')

def seed_database():
    print(f"Connecting to database: {DB_FILE}...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # ----------------------------------------------------
    # 1. SETUP TABLES (Synchronized with app.py)
    # ----------------------------------------------------
    try:
        cursor.execute("DROP TABLE IF EXISTS users;")
        cursor.execute("DROP TABLE IF EXISTS complaints;")
        print("🧹 Cleared existing tables for a pristine database seed.")
    except sqlite3.OperationalError:
        pass

    # Create Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            mobile TEXT,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')

    # Create Complaints Table (Matches app.py exact schema layout)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id TEXT UNIQUE NOT NULL,
            citizen_id TEXT NOT NULL,
            citizen_name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            department TEXT NOT NULL,
            ward TEXT NOT NULL,
            location TEXT NOT NULL,
            latitude TEXT,
            longitude TEXT,
            photo TEXT,
            status TEXT DEFAULT 'Submitted',
            assigned_to TEXT,
            assigned_officer_name TEXT,
            created_at TEXT NOT NULL
        )
    ''')

    # ----------------------------------------------------
    # 2. SEED USERS & ROLES
    # ----------------------------------------------------
    users_data = [
        # Admin / Commissioner
        ('Municipal Commissioner', 'admin@muni.gov', '1234567890', 'admin123', 'admin', 'Administration'),
        
        # Level 1 Escalate Window: 0 - 48 Hours
        ('Health Inspector Alpha', 'health@muni.gov', '9000000001', 'health123', 'health_inspector', 'Health'),
        ('Sr. Health Inspector Beta', 'srhealth@muni.gov', '9000000002', 'health123', 'senior_health_inspector', 'Health'),
        
        # Level 2 Escalate Window: 48 - 96 Hours
        ('Environment Engineer Gamma', 'engineer@muni.gov', '9000000003', 'engineer123', 'environment_engineer', 'Public Works'),
        
        # Level 3 Escalate Window: Over 96 Hours
        ('Chief Officer Delta', 'chief@muni.gov', '9000000004', 'chief123', 'chief_officer', 'Administration'),
        
        # Simple Citizen Account for validation testing
        ('Test Citizen', 'citizen@test.com', '7778889990', 'citizen123', 'citizen', None)
    ]

    print("\n👥 Seeding system accounts with organizational roles...")
    for name, email, mobile, password, role, dept in users_data:
        cursor.execute('''
            INSERT INTO users (name, email, mobile, password, role, department, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        ''', (name, email, mobile, generate_password_hash(password), role, dept))
        print(f"  ✅ Created {role.replace('_', ' ').title()}: ({email} / {password})")


    # ----------------------------------------------------
    # 3. SEED DUMMY COMPLAINTS FOR ESCALATION TIMELINE TESTING
    # ----------------------------------------------------
    print("\n📋 Seeding mock complaints into timeline tracking pipelines...")
    
    now = datetime.now()
    time_12_hours_ago = (now - timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
    time_60_hours_ago = (now - timedelta(hours=60)).strftime('%Y-%m-%d %H:%M:%S')
    time_110_hours_ago = (now - timedelta(hours=110)).strftime('%Y-%m-%d %H:%M:%S')

    # Mapping your target criteria inputs smoothly down into app.py keys
    complaints_data = [
        ('Garbage Pile Accumulation', 'Huge trash build-up outside ward 4.', 'John Doe', 'Health', 'Ward 4', time_12_hours_ago),
        ('Water Pipeline Leakage', 'Main line broken, wasting drinkable water.', 'Jane Smith', 'Public Works', 'Ward 2', time_60_hours_ago),
        ('Illegal Industrial Dumping', 'Toxic chemical waste dumped in open plot.', 'Bob Johnson', 'Public Works', 'Ward 7', time_110_hours_ago)
    ]

    for category, desc, citizen, dept, ward, created_at in complaints_data:
        # Generate clean custom structural string ID sequence
        comp_id = f"COMP-{datetime.now().strftime('%Y%m%d%H%M')}-{random.randint(1000, 9999)}"
        
        cursor.execute('''
            INSERT INTO complaints (
                complaint_id, citizen_id, citizen_name, category, description, department, 
                ward, location, latitude, longitude, photo, status, assigned_to, assigned_officer_name, created_at
            ) VALUES (?, '5', ?, ?, ?, ?, ?, 'Near Town Hall Center', '14.8000', '75.8000', NULL, 'Submitted', NULL, NULL, ?)
        ''', (comp_id, citizen, category, desc, dept, ward, created_at))
    
    print("  ✅ 1 New Complaint (12 hours old -> Belongs to Health Inspectors)")
    print("  ✅ 1 Mid-tier Complaint (60 hours old -> Escalated to Env. Engineer)")
    print("  ✅ 1 Critical Complaint (110 hours old -> Escalated to Chief Officer)")

    # Commit changes and close the connection
    conn.commit()
    conn.close()
    print("\n🎉 Database seeding completed successfully with tracking alignment!")

if __name__ == '__main__':
    seed_database()