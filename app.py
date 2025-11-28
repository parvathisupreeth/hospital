from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import or_
from flask import abort

app = Flask(__name__)
app.secret_key = 'boosss_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
db = SQLAlchemy()
db.init_app(app)
app.app_context().push()

# models

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, doctor, patient
    contact = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Department(db.Model):
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f'<Department {self.name}>'


class Doctor(db.Model):
    __tablename__ = 'doctor'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    availability = db.Column(db.String(255), nullable=True)

    user = db.relationship('User', backref='doctor')

    def __repr__(self):
        return f'<Doctor {self.user.username} - {self.specialization}>'


class Patient(db.Model):
    __tablename__ = 'patient'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contact_info = db.Column(db.String(255), nullable=True)

    user = db.relationship('User', backref='patient')

    def __repr__(self):
        return f'<Patient {self.user.username}>'


class Appointment(db.Model):
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)  # you can switch to date type if allowed
    time = db.Column(db.String(20), nullable=False)  # you can switch to time type if allowed
    status = db.Column(db.String(20), default='Booked', nullable=False)  # Booked, Completed, Cancelled

    patient = db.relationship('Patient', backref='appointments')
    doctor = db.relationship('Doctor', backref='appointments')

    __table_args__ = (db.UniqueConstraint('doctor_id', 'date', 'time', name='_doctor_appointment_uc'),)

    def __repr__(self):
        return f'<Appointment {self.patient.user.username} with {self.doctor.user.username} on {self.date} {self.time}>'


class Treatment(db.Model):
    __tablename__ = 'treatment'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    diagnosis = db.Column(db.String(255))
    prescription = db.Column(db.String(255))
    notes = db.Column(db.String(255))

    appointment = db.relationship('Appointment', backref='treatment')

    def __repr__(self):
        return f'<Treatment for Appointment ID {self.appointment_id}>'


def create_auto_admin():
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(username='Admin', password='@dmin123', role='admin')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created")
    else:
        print("Admin already exists")


# ---------------- AUTH ROUTES ---------------- #

@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template("signup.html")

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    contact = request.form.get('contact', '').strip()

    if not username or len(username) < 3:
        flash("Username must be at least 3 characters long!", "error")
        return redirect(url_for('signup'))

    if not password or len(password) < 6:
        flash("Password must be at least 6 characters long!", "error")
        return redirect(url_for('signup'))

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash("Username already exists! Please login.", "warning")
        return redirect(url_for('login'))

    try:
        new_user = User(username=username, password=password, contact=contact, role='patient')
        db.session.add(new_user)
        db.session.commit()
        flash("Signup successful! You can now log in.", "success")
        return redirect(url_for('login'))
    except Exception:
        db.session.rollback()
        flash("An error occurred during signup. Please try again.", "error")
        return redirect(url_for('signup'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if not user:
            flash('User not found. Please sign up first!', 'warning')
            return redirect(url_for('signup'))

        if user.password != password:
            flash('Incorrect password!', 'error')
            return redirect(url_for('login'))

        session['username'] = user.username
        session['user_id'] = user.id
        session['role'] = user.role
        flash('Login successful!', 'success')

        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role == 'doctor':
            return redirect(url_for('doc_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))


# ---------------- ADMIN ROUTES ---------------- #

# @app.route('/admin/dashboard')
# def admin_dashboard():
#     if 'user_id' not in session or session.get('role') != 'admin':
#         flash('Access denied', 'error')
#         return redirect(url_for('login'))

#     total_doctors = Doctor.query.count()
#     total_patients = Patient.query.count()
#     total_appointments = Appointment.query.count()
#     pending_appointments = Appointment.query.filter_by(status='Booked').count()
#     completed_appointments = Appointment.query.filter_by(status='Completed').count()

#     return render_template('admin_dashboard.html',
#                            total_doctors=total_doctors,
#                            total_patients=total_patients,
#                            total_appointments=total_appointments,
#                            pending_appointments=pending_appointments,
#                            completed_appointments=completed_appointments)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    # Basic counts
    total_doctors = Doctor.query.count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()
    pending_appointments = Appointment.query.filter_by(status='Booked').count()
    completed_appointments = Appointment.query.filter_by(status='Completed').count()
    cancelled_appointments = Appointment.query.filter_by(status='Cancelled').count()

    # Calculate percentages for department performance
    completion_rate = round((completed_appointments / total_appointments * 100) if total_appointments > 0 else 0)
    satisfaction_rate = 92  # You can calculate this from patient feedback if available
    efficiency_score = 85   # You can calculate this based on your metrics

    # Get doctors by specialization
    from sqlalchemy import func
    specialization_data = db.session.query(
        Doctor.specialization,
        func.count(Doctor.id).label('count')
    ).group_by(Doctor.specialization).all()

    # Find max count for percentage calculation
    max_count = max([s[1] for s in specialization_data]) if specialization_data else 1

    # Format specialization data for chart
    specializations = []
    class_names = ['cardiology', 'neurology', 'orthopedics', 'pediatrics', 'general']
    for idx, (spec, count) in enumerate(specialization_data):
        percentage = round((count / max_count) * 100)
        specializations.append({
            'name': spec,
            'count': count,
            'percentage': percentage,
            'class': class_names[idx % len(class_names)]
        })

    return render_template('admin_dashboard.html',
                           total_doctors=total_doctors,
                           total_patients=total_patients,
                           total_appointments=total_appointments,
                           pending_appointments=pending_appointments,
                           completed_appointments=completed_appointments,
                           cancelled_appointments=cancelled_appointments,
                           completion_rate=completion_rate,
                           satisfaction_rate=satisfaction_rate,
                           efficiency_score=efficiency_score,
                           specializations=specializations)


@app.route('/admin/doctors')
def view_doc():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    search = request.args.get('search', '').strip()
    
    if search:
        doctors = Doctor.query.join(User).filter(
            or_(
                User.username.ilike(f'%{search}%'),
                Doctor.specialization.ilike(f'%{search}%')
            )
        ).all()
    else:
        doctors = Doctor.query.all()
    
    return render_template('view_doc.html', doctors=doctors, search=search)


@app.route('/admin/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        contact = request.form.get('contact')
        specialization = request.form.get('specialization')
        availability = request.form.get('availability')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'warning')
            return redirect(url_for('add_doctor'))

        new_user = User(username=username, password=password, contact=contact, role='doctor')
        db.session.add(new_user)
        db.session.commit()

        new_doctor = Doctor(user_id=new_user.id, specialization=specialization, availability=availability)
        db.session.add(new_doctor)
        db.session.commit()

        flash('Doctor added successfully!', 'success')
        return redirect(url_for('view_doc'))

    return render_template('add_doc.html')


@app.route('/admin/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
def edit_doc(doctor_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    doctor = Doctor.query.get_or_404(doctor_id)

    if request.method == 'POST':
        doctor.user.username = request.form.get('username')
        doctor.user.contact = request.form.get('contact')

        new_password = request.form.get('password')
        if new_password:
            doctor.user.password = new_password

        doctor.specialization = request.form.get('specialization')
        doctor.availability = request.form.get('availability')
        db.session.commit()

        flash('Doctor updated successfully!', 'success')
        return redirect(url_for('view_doc'))

    return render_template('edit_doc.html', doctor=doctor)


@app.route('/admin/delete_doctor/<int:doctor_id>')
def delete_doc(doctor_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    doctor = Doctor.query.get_or_404(doctor_id)

    if Appointment.query.filter_by(doctor_id=doctor_id).count() > 0:
        flash('Cannot delete doctor with existing appointments!', 'error')
        return redirect(url_for('view_doc'))

    db.session.delete(doctor)
    db.session.delete(doctor.user)
    db.session.commit()

    flash('Doctor deleted successfully!', 'success')
    return redirect(url_for('view_doc'))


@app.route('/admin/appointments')
def view_appointments():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    search = request.args.get('search', '').strip()
    
    if search:
        # Search by patient or doctor name
        appointments = []
        
        # Search in patients
        patient_appointments = Appointment.query.join(
            Patient
        ).join(
            User, Patient.user_id == User.id
        ).filter(
            User.username.ilike(f'%{search}%')
        ).all()
        
        # Search in doctors
        doctor_appointments = Appointment.query.join(
            Doctor
        ).join(
            User, Doctor.user_id == User.id
        ).filter(
            User.username.ilike(f'%{search}%')
        ).all()
        
        # Combine and remove duplicates
        appointments = list(set(patient_appointments + doctor_appointments))
    else:
        appointments = Appointment.query.all()
    
    return render_template('view_appointments.html', appointments=appointments, search=search)


@app.route('/admin/treatments')
def view_all_treatments():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    search = request.args.get('search', '').strip()
    
    if search:
        # Search by patient name, doctor name, diagnosis, prescription, or notes
        treatments = Treatment.query.join(
            Appointment
        ).join(
            Patient, Appointment.patient_id == Patient.id
        ).join(
            User, Patient.user_id == User.id
        ).filter(
            or_(
                User.username.ilike(f'%{search}%'),
                Treatment.diagnosis.ilike(f'%{search}%'),
                Treatment.prescription.ilike(f'%{search}%'),
                Treatment.notes.ilike(f'%{search}%')
            )
        ).all()
    else:
        treatments = Treatment.query.all()
    
    return render_template('admin_treatments.html', treatments=treatments, search=search)


@app.route('/admin/patients')
def view_user():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    search = request.args.get('search', '').strip()
    
    if search:
        patients = Patient.query.join(User).filter(
            User.username.ilike(f'%{search}%')
        ).all()
    else:
        patients = Patient.query.all()
    
    return render_template('view_user.html', patients=patients, search=search)


# ---------------- DOCTOR ROUTES ---------------- #

# @app.route('/doctor/dashboard')
# def doc_dashboard():
#     if 'user_id' not in session or session.get('role') != 'doctor':
#         flash('Access denied', 'error')
#         return redirect(url_for('login'))

#     doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
#     if not doctor:
#         flash('Doctor profile not found', 'error')
#         return redirect(url_for('login'))

#     total_appointments = Appointment.query.filter_by(doctor_id=doctor.id).count()
#     pending = Appointment.query.filter_by(doctor_id=doctor.id, status='Booked').count()
#     completed = Appointment.query.filter_by(doctor_id=doctor.id, status='Completed').count()

#     return render_template('doc_dashboard.html', doctor=doctor,
#                            total_appointments=total_appointments,
#                            pending=pending, completed=completed)
@app.route('/doctor/dashboard')
def doc_dashboard():
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    if not doctor:
        flash('Doctor profile not found', 'error')
        return redirect(url_for('login'))

    # Appointment counts
    total_appointments = Appointment.query.filter_by(doctor_id=doctor.id).count()
    pending = Appointment.query.filter_by(doctor_id=doctor.id, status='Booked').count()
    completed = Appointment.query.filter_by(doctor_id=doctor.id, status='Completed').count()
    cancelled = Appointment.query.filter_by(doctor_id=doctor.id, status='Cancelled').count()

    # Calculate percentages for pie chart (FIXED)
    if total_appointments > 0:
        completed_percentage = round((completed / total_appointments) * 100)
        booked_percentage = round((pending / total_appointments) * 100)
        cancelled_percentage = round((cancelled / total_appointments) * 100)
    else:
        completed_percentage = 0
        booked_percentage = 0
        cancelled_percentage = 0

    # Treatment success rate
    completed_appointment_ids = [a.id for a in Appointment.query.filter_by(doctor_id=doctor.id, status='Completed').all()]
    treatments_given = Treatment.query.filter(Treatment.appointment_id.in_(completed_appointment_ids)).count() if completed_appointment_ids else 0
    successful_treatments = treatments_given  # Assuming all treatments are successful
    success_rate = round((successful_treatments / completed * 100) if completed > 0 else 0)

    return render_template('doc_dashboard.html',
                           doctor=doctor,
                           total_appointments=total_appointments,
                           pending=pending,
                           completed=completed,
                           cancelled=cancelled,
                           completed_percentage=completed_percentage,
                           booked_percentage=booked_percentage,
                           cancelled_percentage=cancelled_percentage,
                           success_rate=success_rate,
                           treatments_given=treatments_given,
                           successful_treatments=successful_treatments)

@app.route('/doctor/appointments')
def doc_appointments():
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()
    return render_template('doc_appointments.html', appointments=appointments, doctor=doctor)


@app.route('/doctor/complete_appointment/<int:appointment_id>')
def complete_appointment(appointment_id):
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    appointment = Appointment.query.get_or_404(appointment_id)
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()

    if appointment.doctor_id != doctor.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('doc_appointments'))

    appointment.status = 'Completed'
    db.session.commit()

    flash('Appointment marked as completed', 'success')
    return redirect(url_for('doc_appointments'))


@app.route('/doctor/add_treatment/<int:appointment_id>', methods=['GET', 'POST'])
def add_treatment(appointment_id):
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    appointment = Appointment.query.get_or_404(appointment_id)
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()

    if appointment.doctor_id != doctor.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('doc_appointments'))

    if appointment.status != 'Completed':
        flash('Treatment can only be added to completed appointments', 'warning')
        return redirect(url_for('doc_appointments'))

    existing_treatment = Treatment.query.filter_by(appointment_id=appointment_id).first()
    if existing_treatment:
        flash('Treatment record already exists for this appointment', 'warning')
        return redirect(url_for('doc_appointments'))

    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis')
        prescription = request.form.get('prescription')
        notes = request.form.get('notes')

        new_treatment = Treatment(
            appointment_id=appointment_id,
            diagnosis=diagnosis,
            prescription=prescription,
            notes=notes
        )
        db.session.add(new_treatment)
        db.session.commit()

        flash('Treatment record added successfully!', 'success')
        return redirect(url_for('doc_appointments'))

    return render_template('add_treatment.html', appointment=appointment)


# ---------------- PATIENT ROUTES ---------------- #

@app.route('/patient/dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    if not patient:
        patient = Patient(user_id=session['user_id'])
        db.session.add(patient)
        db.session.commit()

    # Appointment counts
    total_appointments = Appointment.query.filter_by(patient_id=patient.id).count()
    upcoming = Appointment.query.filter_by(patient_id=patient.id, status='Booked').count()
    completed = Appointment.query.filter_by(patient_id=patient.id, status='Completed').count()

    # Calculate completion rate
    completion_rate = round((completed / total_appointments * 100) if total_appointments > 0 else 0)

    # Get treatments received
    completed_appointment_ids = [a.id for a in Appointment.query.filter_by(patient_id=patient.id, status='Completed').all()]
    treatments_received = Treatment.query.filter(Treatment.appointment_id.in_(completed_appointment_ids)).count() if completed_appointment_ids else 0

    return render_template('user_dashboard.html',
                           patient=patient,
                           total_appointments=total_appointments,
                           upcoming=upcoming,
                           completed=completed,
                           completion_rate=completion_rate,
                           treatments_received=treatments_received)


@app.route('/patient/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    if not patient:
        flash('Patient profile not found', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        date = request.form.get('date')
        time = request.form.get('time')

        if not doctor_id or not date or not time:
            flash('All fields are required!', 'error')
            return redirect(url_for('book_appointment'))

        existing = Appointment.query.filter_by(doctor_id=doctor_id, date=date, time=time).first()
        if existing:
            flash('This time slot is already booked!', 'warning')
            return redirect(url_for('book_appointment'))

        try:
            new_appointment = Appointment(
                patient_id=patient.id,
                doctor_id=doctor_id,
                date=date,
                time=time,
                status='Booked'
            )
            db.session.add(new_appointment)
            db.session.commit()
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('user_appointments'))
        except Exception:
            db.session.rollback()
            flash('Error booking appointment. Please try again.', 'error')
            return redirect(url_for('book_appointment'))

    search = request.args.get('search', '').strip()
    query = Doctor.query
    if search:
        pattern = f"%{search}%"
        query = query.join(User).filter(or_(
            User.username.ilike(pattern),
            Doctor.specialization.ilike(pattern)
        ))

    doctors = query.all()
    return render_template('book_appointment.html', doctors=doctors, search=search)


@app.route('/patient/appointments')
def user_appointments():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    appointments = Appointment.query.filter_by(patient_id=patient.id).all()
    return render_template('user_appointments.html', appointments=appointments)


@app.route('/patient/treatments')
def view_treatments():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    appointments = Appointment.query.filter_by(patient_id=patient.id, status='Completed').all()

    treatments_data = []
    for appointment in appointments:
        treatment = Treatment.query.filter_by(appointment_id=appointment.id).first()
        if treatment:
            treatments_data.append({'appointment': appointment, 'treatment': treatment})

    return render_template('view_treatments.html', treatments_data=treatments_data)


@app.route('/patient/cancel_appointment/<int:appointment_id>')
def cancel_appointment(appointment_id):
    if 'user_id' not in session or session.get('role') != 'patient':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    appointment = Appointment.query.get_or_404(appointment_id)
    patient = Patient.query.filter_by(user_id=session['user_id']).first()

    if appointment.patient_id != patient.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('user_appointments'))

    if appointment.status != 'Booked':
        flash('Only booked appointments can be cancelled!', 'warning')
        return redirect(url_for('user_appointments'))

    appointment.status = 'Cancelled'
    db.session.commit()

    flash('Appointment cancelled successfully!', 'success')
    return redirect(url_for('user_appointments'))




if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_auto_admin()
    app.run(debug=True)
