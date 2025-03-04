from datetime import datetime, timedelta, timezone
from .model import db, Admin, User, AttendanceLocation, Attendance

def seed_all():
    """Seed all tables with initial data"""
    seed_admin()
    seed_users()
    seed_attendance_locations()
    seed_attendances()
    db.session.commit()

def seed_admin():
    """Seed admin table with initial admin user"""
    if Admin.query.filter_by(username='admin').first() is None:
        admin = Admin(
            username='admin',
            full_name='Administrator'
        )
        admin.set_password('admin123')  # You should change this in production
        db.session.add(admin)

def seed_users():
    """Seed users table with sample users"""
    sample_users = [
        {
            'username': 'john.doe',
            'password': 'password123',
            'division': 'Mathematics',
            'full_name': 'John Doe'
        },
        {
            'username': 'jane.smith',
            'password': 'password123',
            'division': 'Science',
            'full_name': 'Jane Smith'
        },
        {
            'username': 'bob.wilson',
            'password': 'password123',
            'division': 'English',
            'full_name': 'Bob Wilson'
        }
    ]

    for user_data in sample_users:
        if User.query.filter_by(username=user_data['username']).first() is None:
            user = User(
                username=user_data['username'],
                division=user_data['division'],
                full_name=user_data['full_name']
            )
            user.set_password(user_data['password'])
            db.session.add(user)

def seed_attendance_locations():
    """Seed attendance_locations table with sample locations"""
    sample_locations = [
        {
            'id': 'LOC001',
            'name': 'Main Building',
            'short_name': 'MAIN',
            'description': 'Main school building entrance',
            'latitude': '-7.123456',
            'longitude': '110.123456'
        },
        {
            'id': 'LOC002',
            'name': 'Science Building',
            'short_name': 'SCI',
            'description': 'Science department building entrance',
            'latitude': '-7.123457',
            'longitude': '110.123457'
        }
    ]

    for location_data in sample_locations:
        if AttendanceLocation.query.filter_by(id=location_data['id']).first() is None:
            location = AttendanceLocation(**location_data)
            db.session.add(location)

def seed_attendances():
    """Seed attendances table with sample attendance records"""
    # Get a user for sample attendance
    user = User.query.filter_by(username='john.doe').first()
    if not user:
        return

    # Get a location for sample attendance
    location = AttendanceLocation.query.filter_by(id='LOC001').first()
    if not location:
        return

    # Create attendance for the last 5 days
    for i in range(5):
        date = datetime.now(timezone(timedelta(hours=7))) - timedelta(days=i)
        attendance_date = date.date()
        
        # Skip if attendance already exists for this date
        if Attendance.query.filter_by(user_id=user.id, attendance_date=attendance_date).first():
            continue

        # Create check-in time at 07:30
        check_in_time = datetime.combine(attendance_date, datetime.strptime('07:30', '%H:%M').time())
        check_in_time = check_in_time.replace(tzinfo=timezone(timedelta(hours=7)))
        
        # Create check-out time at 16:00
        check_out_time = datetime.combine(attendance_date, datetime.strptime('16:00', '%H:%M').time())
        check_out_time = check_out_time.replace(tzinfo=timezone(timedelta(hours=7)))

        attendance = Attendance(
            user_id=user.id,
            attendance_date=attendance_date,
            check_in=check_in_time,
            check_in_location_id=location.id,
            check_out=check_out_time,
            check_out_location_id=location.id,
            status='present',
            notes='Regular attendance'
        )
        db.session.add(attendance)
