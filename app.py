# app.py - Complete Municipal Grievance Redressal System (SQLite Edition)
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime, timedelta
import os
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback_secret_key')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
DB_FILE = os.getenv('SQLITE_DB', 'municipal_db.sqlite')

# ================= DATABASE CONNECTION =================
def get_db_connection():
    """Helper function to open a connection to SQLite and return dictionary rows."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Access query results like regular Python dicts
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        
        # Create Complaints Table
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
        
        conn.commit()
        conn.close()
        print("✅ SQLite Database & Tables Connected/Initialized Successfully!")
        return True
    except Exception as e:
        print(f"❌ Database Connection/Initialization Error: {e}")
        return False

# ================= MERGED SEEDING LOGIC =================
def seed_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if data already exists to avoid duplicate seeding
    cursor.execute("SELECT count(*) FROM users")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    print("🚀 Seeding database...")
    users_data = [
        ('Municipal Commissioner', 'admin@muni.gov', '1234567890', 'admin123', 'admin', 'Administration'),
        ('Health Inspector Alpha', 'health@muni.gov', '9000000001', 'health123', 'health_inspector', 'Health'),
        ('Sr. Health Inspector Beta', 'srhealth@muni.gov', '9000000002', 'health123', 'senior_health_inspector', 'Health'),
        ('Environment Engineer Gamma', 'engineer@muni.gov', '9000000003', 'engineer123', 'environment_engineer', 'Public Works'),
        ('Chief Officer Delta', 'chief@muni.gov', '9000000004', 'chief123', 'chief_officer', 'Administration'),
        ('Test Citizen', 'citizen@test.com', '7778889990', 'citizen123', 'citizen', None)
    ]

    for name, email, mobile, password, role, dept in users_data:
        cursor.execute('''INSERT INTO users (name, email, mobile, password, role, department, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')''', (name, email, mobile, generate_password_hash(password), role, dept))

    now = datetime.now()
    complaints_data = [
        ('Garbage Pile Accumulation', 'Huge trash build-up.', 'John Doe', 'Health', 'Ward 4', (now - timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')),
        ('Water Pipeline Leakage', 'Main line broken.', 'Jane Smith', 'Public Works', 'Ward 2', (now - timedelta(hours=60)).strftime('%Y-%m-%d %H:%M:%S')),
        ('Illegal Industrial Dumping', 'Toxic chemical waste.', 'Bob Johnson', 'Public Works', 'Ward 7', (now - timedelta(hours=110)).strftime('%Y-%m-%d %H:%M:%S'))
    ]

    for category, desc, citizen, dept, ward, created_at in complaints_data:
        comp_id = f"COMP-{datetime.now().strftime('%Y%m%d%H%M')}-{random.randint(1000, 9999)}"
        cursor.execute('''INSERT INTO complaints (complaint_id, citizen_id, citizen_name, category, description, department, 
                ward, location, latitude, longitude, status, created_at) VALUES (?, '5', ?, ?, ?, ?, ?, 'Town Hall', '14.8', '75.8', 'Submitted', ?)''', 
                (comp_id, citizen, category, desc, dept, ward, created_at))
    
    conn.commit()
    conn.close()
    print("🎉 Database seeding completed!")

# Add these new columns dynamically
def patch_db_for_resolution():
    conn = get_db_connection()
    try:
        conn.execute("ALTER TABLE complaints ADD COLUMN resolved_photo TEXT;")
        conn.execute("ALTER TABLE complaints ADD COLUMN resolved_by_role TEXT;")
        conn.execute("ALTER TABLE complaints ADD COLUMN resolution_notes TEXT;")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()

# Initialize everything on start
init_db()
patch_db_for_resolution()
seed_database()

# ... (Keep the rest of your app.py routes and code below this point)
# Ensure you keep your existing route definitions here as they were in the original file

# ----------------------------------------------------
# ROUTE: VIEW COMPLAINT DETAILS
# ----------------------------------------------------
@app.route('/complaint/view/<int:complaint_id>', methods=['GET', 'POST'])
@login_required
def view_complaint(complaint_id):
    conn = get_db_connection()
    complaint = conn.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
    
    if not complaint:
        conn.close()
        flash('Requested complaint record could not be indexed.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        new_status = request.form.get('status')
        reason = request.form.get('reason')
        
        # --- ROBUST CROSS-DEPARTMENT VALIDATION ENGINE ---
        can_mutate = True
        
        # Check L1 Tier (Health Officials)
        if current_user.role in ['health_inspector', 'senior_health_inspector'] and complaint['department'] != 'Health':
            can_mutate = False
            flash('Operation Refused: Your account authority cannot alter Non-Health category records.', 'danger')
            
        # Check L2 Tier (Environment Engineers)
        elif current_user.role == 'environment_engineer' and complaint['department'] != 'Public Works':
            can_mutate = False
            flash('Operation Refused: Your account authority cannot alter Non-Public Works category records.', 'danger')
            
        # Check L0 Tier (Citizens)
        elif current_user.role == 'citizen':
            can_mutate = False
            flash('Operation Refused: Citizens cannot alter internal system processing flags.', 'danger')

        # If permissions check passes, run the update query block safely
        if can_mutate and new_status and reason:
            conn.execute('''
                UPDATE complaints 
                SET status = ?, resolution_reason = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (new_status, reason, complaint_id))
            conn.commit()
            flash(f'Complaint #{complaint_id} status successfully transitioned to {new_status}.', 'success')
            conn.close()
            return redirect(url_for('dashboard'))

    conn.close()
    return render_template('view_complaint.html', complaint=complaint)

# ----------------------------------------------------
# ROUTE: RESOLVE COMPLAINT (EITHER PHOTO OR REASON REQUIRED)
# ----------------------------------------------------
@app.route('/complaint/resolve/<string:complaint_id>', methods=['POST'])
@login_required
def resolve_complaint(complaint_id):
    if current_user.role == 'citizen':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))
        
    file = request.files.get('resolved_photo')
    notes = request.form.get('resolution_notes', '').strip()
    
    # --- FLEXIBLE MUTUAL EXCLUSIVITY VALIDATION ---
    has_file = file and file.filename != ''
    has_notes = len(notes) > 0

    # Trigger error if BOTH fields are left empty
    if not has_file and not has_notes:
        flash('Action Required: You must either upload media proof OR provide a resolution reason to close this ticket!', 'danger')
        return redirect(url_for('dashboard')) # Safely falls back to workflow workspace
        
    resolved_filename = None
    if has_file:
        filename = secure_filename(file.filename)
        # Prefix filename to distinguish resolution files
        resolved_filename = f"resolved_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], resolved_filename))
    
    # Track the clean title string formatting representation of the actor role
    display_role = current_user.role.replace('_', ' ').title()
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE complaints 
        SET status = 'Resolved',
            resolved_photo = ?,
            resolved_by_role = ?,
            resolution_notes = ?
        WHERE complaint_id = ?
    ''', (resolved_filename, display_role, notes if has_notes else "Resolved via media confirmation.", complaint_id))
    conn.commit()
    conn.close()
    
    flash(f'Complaint successfully marked as Resolved by {display_role}!', 'success')
    return redirect(url_for('dashboard'))
    
# ================= DEFAULT USERS =================
def create_default_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create Admin
        cursor.execute('SELECT * FROM users WHERE email = ?', ('admin@muni.gov',))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (name, email, mobile, password, role, department, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                'Municipal Commissioner', 'admin@muni.gov', '1234567890',
                generate_password_hash('admin123'), 'admin', 'Administration', 'active'
            ))
            print("✅ Admin Created: admin@muni.gov / admin123")
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating default users: {e}")

# ================= LOGIN MANAGER =================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_id, name, email, role, department=None):
        self.id = user_id
        self.name = name
        self.email = email
        self.role = role
        self.department = department

@login_manager.user_loader
def load_user(user_id):
    try:
        conn = get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE id = ?', (int(user_id),)).fetchone()
        conn.close()
        if user_data:
            return User(str(user_data['id']), user_data['name'], user_data['email'], user_data['role'], user_data['department'])
    except:
        pass
    return None

# ================= JINJA TEMPLATE FILTERS =================
@app.template_filter('date_format')
def date_format(value, format='%b %d, %Y'):
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return value 
    return value.strftime(format)

# ================= ROUTES =================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data['password'], password):
            user = User(str(user_data['id']), user_data['name'], user_data['email'], user_data['role'], user_data['department'])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        password = generate_password_hash(request.form['password'])
        
        conn = get_db_connection()
        existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        
        if existing_user:
            conn.close()
            flash('Email already registered', 'warning')
            return redirect(url_for('register'))

        conn.execute('''
            INSERT INTO users (name, email, mobile, password, role, status)
            VALUES (?, ?, ?, ?, 'citizen', 'active')
        ''', (name, email, mobile, password))
        conn.commit()
        conn.close()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    current_date = datetime.now().strftime('%d %B %Y')
    conn = get_db_connection()
    
    # ----------------------------------------------------
    # 1. CITIZEN DASHBOARD
    # ----------------------------------------------------
    if current_user.role == 'citizen':
        complaints = conn.execute('SELECT * FROM complaints WHERE citizen_id = ? ORDER BY id DESC', (str(current_user.id),)).fetchall()
        my_complaints = [dict(row) for row in complaints]
        conn.close()
        return render_template('citizen_dashboard.html', complaints=my_complaints, current_date=current_date)
    
    # ----------------------------------------------------
    # 2. OFFICIAL / ADMIN DASHBOARDS (Handling Escalation Matrix)
    # ----------------------------------------------------
    elif current_user.role in ['admin', 'commissioner', 'health_inspector', 'senior_health_inspector', 'environment_engineer', 'chief_officer']:
        
        role = current_user.role
        time_filter_query = ""
        
        # Build dynamic escalation windows relative to 'now' for analytical KPIs
        if role in ['admin', 'commissioner']:
            time_filter_query = "WHERE 1=1"
        
        elif role in ['health_inspector', 'senior_health_inspector']:
            # Level 1: Under 48 hours old
            time_filter_query = "WHERE datetime(created_at) >= datetime('now', '-48 hours')"
            
        elif role == 'environment_engineer':
            # Level 2: Between 48 hours and 96 hours old
            time_filter_query = "WHERE datetime(created_at) >= datetime('now', '-96 hours') AND datetime(created_at) < datetime('now', '-48 hours')"
            
        elif role == 'chief_officer':
            # Level 3: Over 96 hours old
            time_filter_query = "WHERE datetime(created_at) < datetime('now', '-96 hours')"

        # Calculate Isolated KPIs based on visibility window constraints
        total = conn.execute(f'SELECT COUNT(*) FROM complaints {time_filter_query}').fetchone()[0]
        in_progress = conn.execute(f"SELECT COUNT(*) FROM complaints {time_filter_query} AND status = 'In Progress'").fetchone()[0]
        resolved = conn.execute(f"SELECT COUNT(*) FROM complaints {time_filter_query} AND status = 'Resolved'").fetchone()[0]
        pending = conn.execute(f"SELECT COUNT(*) FROM complaints {time_filter_query} AND status IN ('Submitted', 'Assigned', 'Pending')").fetchone()[0]
        overdue = conn.execute(f"SELECT COUNT(*) FROM complaints {time_filter_query} AND status = 'Overdue'").fetchone()[0]
        
        # ------------------------------------------------======================
        # FIX: FETCH UNIFIED MASTER RECORD LIST FOR EVERYONE (Irrespective of category/time)
        # ----------------------------------------------------------------======
       # ----------------------------------------------------------------======
        # SIMPLIFIED FIX: Unified record fetching for all official & admin accounts
        # ----------------------------------------------------------------======
        db_rows = conn.execute('SELECT * FROM complaints ORDER BY id DESC').fetchall()
        all_complaints = [dict(row) for row in db_rows]
        # ----------------------------------------------------------------======
        # ----------------------------------------------------------------======

        # Process Real-time Chart Data Streams
        trend_data = []
        labels = []
        for i in range(6, -1, -1):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            labels.append(date.strftime('%a'))
            
            count = conn.execute(
                f"SELECT COUNT(*) FROM complaints {time_filter_query} AND created_at LIKE ?", [f"{date_str}%"]
            ).fetchone()[0]
            trend_data.append(count)
        
        if sum(trend_data) == 0:
            trend_data = [3, 5, 2, 8, 4, 6, 7]
            labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        ward_data = [{'ward': f'Ward {i}', 'count': i} for i in range(1, 24)]
        dept_data = [
            {'dept': 'Public Works', 'percentage': 75},
            {'dept': 'Health', 'percentage': 90},
            {'dept': 'Revenue', 'percentage': 65},
            {'dept': 'Planning', 'percentage': 80}
        ]
        sla_compliance = 85
        
        conn.close()
        
        return render_template('admin_dashboard.html', 
                             total=total, in_progress=in_progress, resolved=resolved,
                             overdue=overdue, trend_data=trend_data, labels=labels,
                             ward_data=ward_data, dept_performance=dept_data,
                             sla_compliance=sla_compliance, current_date=current_date, 
                             role=role, complaints=all_complaints) # <-- Added variable to template
    
    # ----------------------------------------------------
    # 3. FIELD OFFICER DASHBOARD
    # ----------------------------------------------------
    else:
        complaints = conn.execute('SELECT * FROM complaints WHERE assigned_to = ? ORDER BY id DESC', (str(current_user.id),)).fetchall()
        officer_complaints = [dict(row) for row in complaints]
        conn.close()
        return render_template('officer_view.html', complaints=officer_complaints, current_date=current_date)

@app.route('/complaint/new', methods=['GET', 'POST'])
@login_required
def new_complaint():
    if current_user.role != 'citizen':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        file = request.files.get('photo')
        filename = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        title = request.form['title']
        department = request.form['department']
        description = request.form['description']
        ward = request.form['ward']
        location = request.form['location']
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        
        generated_id = f"COMP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        conn = get_db_connection()
        
        # Find an assignment match (Checks for health inspectors first or standard field officers)
        officer = conn.execute('''
            SELECT * FROM users WHERE role IN ('health_inspector', 'field_officer') AND department = ? AND status = 'active' LIMIT 1
        ''', (department,)).fetchone()
        
        assigned_to = str(officer['id']) if officer else None
        assigned_officer_name = officer['name'] if officer else None

        conn.execute('''
            INSERT INTO complaints (
                complaint_id, citizen_id, citizen_name, category, description, department,
                ward, location, latitude, longitude, photo, status, assigned_to, assigned_officer_name, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Submitted', ?, ?, ?)
        ''', (
            generated_id, str(current_user.id), current_user.name, title,
            description, department, ward, location, latitude, longitude, filename,
            assigned_to, assigned_officer_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        conn.close()
        
        if officer:
            flash(f'Complaint submitted and assigned to {assigned_officer_name}', 'success')
        else:
            flash('Complaint submitted successfully', 'success')
        
        return redirect(url_for('complaint_success', complaint_id=generated_id))
    
    return render_template('new_complaint.html')

@app.route('/complaint/success/<string:complaint_id>')
@login_required
def complaint_success(complaint_id):
    conn = get_db_connection()
    complaint = conn.execute('SELECT * FROM complaints WHERE complaint_id = ?', (complaint_id,)).fetchone()
    conn.close()
    
    if complaint is None:
        flash('Complaint record missing or unavailable.', 'danger')
        return redirect(url_for('dashboard'))
        
    return render_template('complaint_success.html', complaint=complaint)

@app.route('/admin/users')
@login_required
def user_management():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    users_rows = conn.execute('SELECT * FROM users').fetchall()
    users = [dict(row) for row in users_rows]
    conn.close()
    return render_template('user_management.html', users=users, current_date=datetime.now().strftime('%d %B %Y'))

@app.route('/admin/user/create', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        department = request.form['department']
        
        conn = get_db_connection()
        existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        
        if existing_user:
            conn.close()
            flash('Email already exists', 'warning')
        else:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (name, email, mobile, password, role, department, status)
                VALUES (?, ?, ?, ?, ?, ?, 'active')
            ''', (name, email, mobile, password, role, department))
            new_user_id = cursor.lastrowid
            
            if role in ['field_officer', 'health_inspector']:
                conn.execute('''
                    UPDATE complaints 
                    SET assigned_to = ?, assigned_officer_name = ? 
                    WHERE department = ? AND status IN ('Submitted', 'Assigned')
                ''', (str(new_user_id), name, department))
                flash(f'{role.replace("_", " ").title()} created. Complaints auto-assigned.', 'success')
            else:
                flash(f'{role.replace("_", " ").title()} created successfully', 'success')
                
            conn.commit()
            conn.close()
        
        return redirect(url_for('user_management'))
    
    return render_template('create_user.html')

@app.route('/map_view')
@login_required
def map_view():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('map_view.html', current_date=datetime.now().strftime('%d %B %Y'))

@app.route('/reports')
@login_required
def reports():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    total = conn.execute('SELECT COUNT(*) FROM complaints').fetchone()[0]
    resolved = conn.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM complaints WHERE status != 'Resolved'").fetchone()[0]
    
    recent_rows = conn.execute('SELECT * FROM complaints ORDER BY created_at DESC LIMIT 50').fetchall()
    recent = []
    for row in recent_rows:
        d = dict(row)
        try:
            d['created_at'] = datetime.strptime(d['created_at'], '%Y-%m-%d %H:%M:%S')
        except:
            d['created_at'] = datetime.now()
        recent.append(d)
        
    conn.close()
    
    return render_template('reports.html', 
                         total=total, resolved=resolved, pending=pending,
                         complaints=recent, current_date=datetime.now().strftime('%d %B %Y'))

@app.route('/api/complaints/geojson')
@login_required
def get_geojson():
    conn = get_db_connection()
    data_rows = conn.execute('SELECT * FROM complaints WHERE latitude IS NOT NULL AND latitude != ""').fetchall()
    conn.close()
    
    features = []
    for doc in data_rows:
        try:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(doc['longitude']), float(doc['latitude'])]},
                "properties": {"category": doc['category'], "status": doc['status'], "location": doc['location'], "id": doc['complaint_id']}
            })
        except (ValueError, TypeError):
            continue
    return jsonify({"type": "FeatureCollection", "features": features})

@app.route('/export/excel')
@login_required
def export_excel():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    import csv
    from io import StringIO
    from flask import make_response
    
    conn = get_db_connection()
    complaints_rows = conn.execute('SELECT * FROM complaints').fetchall()
    conn.close()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Complaint ID', 'Category', 'Description', 'Department', 'Ward', 'Location', 'Status', 'Date Created'])
    
    for c in complaints_rows:
        cw.writerow([
            c['complaint_id'], c['category'], c['description'], c['department'],
            c['ward'], c['location'], c['status'], c['created_at']
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=complaints_report.csv"
    output.headers["Content-type"] = "text/csv"
    
    return output



if __name__ == '__main__':
    if init_db():
        create_default_users()

    os.makedirs('static/uploads', exist_ok=True)

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
