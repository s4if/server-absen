from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    full_name = db.Column(db.String(120))
    
    # Use timezone-aware Asia/Jakarta timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=7))))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone(timedelta(hours=7))),
        onupdate=lambda: datetime.now(timezone(timedelta(hours=7)))
    )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Admin {self.username}>'


class User(db.Model): # untuk guru pakai ini
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    division = db.Column(db.String(80), nullable=False)
    full_name = db.Column(db.String(120))
    
    # Use timezone-aware Asia/Jakarta timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=7))))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone(timedelta(hours=7))),
        onupdate=lambda: datetime.now(timezone(timedelta(hours=7)))
    )
    
    attendances = db.relationship('Attendance', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class AttendanceLocation(db.Model):
    __tablename__ = 'attendance_locations'
    
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    short_name = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)
    latitude = db.Column(db.String(20), nullable=False)
    longitude = db.Column(db.String(20), nullable=False)


class Attendance(db.Model):
    __tablename__ = 'attendances'

    # Add a unique constraint for (user_id, attendance_date)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'attendance_date', name='uq_user_date'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.DateTime, nullable=False)
    check_in_location_id = db.Column(db.String(20), db.ForeignKey('attendance_locations.id'), nullable=False)
    check_out = db.Column(db.DateTime, nullable=True)
    check_out_location_id = db.Column(db.String(20), db.ForeignKey('attendance_locations.id'), nullable=True)
    status = db.Column(db.String(20), default='present')  # present, late, absent
    notes = db.Column(db.Text)

    # Use timezone-aware Asia/Jakarta timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=7))))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone(timedelta(hours=7))),
        onupdate=lambda: datetime.now(timezone(timedelta(hours=7)))
    )

    def __repr__(self):
        return f'<Attendance {self.user_id} {self.check_in.date()}>'