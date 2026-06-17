import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_FILE = os.getenv('SQLITE_DB', 'municipal_db.sqlite')

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def auto_assign_officer(department, ward):
    """
    Finds an active field officer or health inspector in the given department 
    who currently has the minimum number of active complaints assigned.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch all active officers/inspectors for the specific department
    # We look for 'field_officer' or 'health_inspector' depending on how you route them
    cursor.execute('''
        SELECT id FROM users 
        WHERE department = ? 
        AND status = 'active' 
        AND role IN ('field_officer', 'health_inspector')
    ''', (department,))
    
    officers = cursor.fetchall()
    
    if not officers:
        conn.close()
        return None  # No officer available in this department

    selected_officer = None
    min_count = float('inf')

    # 2. Find the officer with the least workload
    for officer in officers:
        officer_id = str(officer['id'])
        
        cursor.execute('''
            SELECT COUNT(*) FROM complaints 
            WHERE assigned_to = ? 
            AND status IN ('Assigned', 'In Progress', 'Submitted')
        ''', (officer_id,))
        
        count = cursor.fetchone()[0]
        
        if count < min_count:
            min_count = count
            selected_officer = officer_id

    conn.close()
    return selected_officer