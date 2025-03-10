from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint
from werkzeug.security import generate_password_hash, check_password_hash
import pytz

# Note: Timezone is hardcoded to Asia/Jakarta

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    full_name = db.Column(db.String(120))
    
    # Use timezone-aware Asia/Jakarta timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')),
        onupdate=lambda: datetime.now(pytz.timezone('Asia/Jakarta'))
    )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Admin {self.username}>'


class User(db.Model): # untuk guru pakai ini
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    division = db.Column(db.String(80), nullable=False)
    full_name = db.Column(db.String(120))
    gender = db.Column(db.Enum("L", "P"), nullable=False) # Laki-laki, Perempuan
    last_login = db.Column(db.DateTime, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete timestamp
    
    # Use timezone-aware Asia/Jakarta timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')),
        onupdate=lambda: datetime.now(pytz.timezone('Asia/Jakarta'))
    )
    
    attendances = db.relationship('Attendance', backref='user', lazy=True)
    agenda_attendees = db.relationship('AgendaAttendee', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def soft_delete(self):
        self.deleted_at = datetime.now(pytz.timezone('Asia/Jakarta'))
        db.session.commit()

    def __repr__(self):
        return f'<User {self.username}>'

class AttendanceLocation(db.Model):
    __tablename__ = 'attendance_locations'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    short_name = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)
    latitude = db.Column(db.String(20), nullable=False)
    longitude = db.Column(db.String(20), nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete timestamp

    # Use timezone-aware Asia/Jakarta timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')),
        onupdate=lambda: datetime.now(pytz.timezone('Asia/Jakarta'))
    )

    def soft_delete(self):
        self.deleted_at = datetime.now(pytz.timezone('Asia/Jakarta'))
        db.session.commit()

# absensi kerja harian
class Attendance(db.Model):
    __tablename__ = 'attendances'

    # Add a unique constraint for (user_id, attendance_date)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'attendance_date', name='uq_user_date'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.DateTime, nullable=False)
    check_in_location_id = db.Column(db.Integer, db.ForeignKey('attendance_locations.id'), nullable=False)
    check_out = db.Column(db.DateTime, nullable=True)
    check_out_location_id = db.Column(db.Integer, db.ForeignKey('attendance_locations.id'), nullable=True)
    status = db.Column(db.String(20), default='present')  # present, late, absent
    notes = db.Column(db.Text)

    # Use timezone-aware Asia/Jakarta timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')),
        onupdate=lambda: datetime.now(pytz.timezone('Asia/Jakarta'))
    )

    def __repr__(self):
        return f'<Attendance {self.user_id} {self.check_in.date()}>'

"""
Agenda ada 2, rutin dan tidak rutin
Rutin: berulang, bisa setiap hari, minggu, bulan, tahun
Tidak rutin: hanya sekali
Yang mengatur adalah admin
Agenda non-rutin akan muncul 2 hari sebelum batas waktu!
"""
class Agenda(db.Model):
    __tablename__ = 'agendas'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.Enum('routine', 'non_routine'), nullable=False)
    # for non-routine agenda
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    deadline_date = db.Column(db.DateTime, nullable=True)
    reminder_offset = db.Column(db.Integer, default=2) # in days

    # Lokasi hanya untuk agenda non-rutin, atau kalau agenda rutin dipisah, bisa juga
    # misal untuk agenda piket apel SMP dan SMA berbeda lokasi (sementara ini belum dipakai untuk rutin)
    location = db.Column(db.String(120), nullable=True)
    latitude = db.Column(db.Numeric(precision=9, scale=6), nullable=True)
    longitude = db.Column(db.Numeric(precision=9, scale=6), nullable=True)
    
    __table_args__ = (
        CheckConstraint('latitude BETWEEN -90 AND 90', name='check_latitude'),
        CheckConstraint('longitude BETWEEN -180 AND 180', name='check_longitude'),
    )

    # for routine agenda
    frequency = db.Column(db.String(30), nullable=True)  # frequency tulis manual bahasa indonesia
    # contoh: 'seminggu sekali', 'dua kali seminggu', 'tiap dua minggu' 'sebulan sekali', dll

    created_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    # Use timezone-aware Asia/Jakarta timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')),
        onupdate=lambda: datetime.now(pytz.timezone('Asia/Jakarta'))
    )
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete timestamp

    def soft_delete(self):
        self.deleted_at = datetime.now(pytz.timezone('Asia/Jakarta'))
        db.session.commit()

    def __repr__(self):
        return f'<Agenda {self.title}>'
    
    def get_reminder_date(self):
        return self.deadline_date - timedelta(days=self.reminder_offset)

# absen agenda 
class AgendaAttendee(db.Model):
    __tablename__ = 'agenda_attendees'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    agenda_id = db.Column(db.Integer, db.ForeignKey('agendas.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attendance_time = db.Column(db.DateTime, nullable=False)
    
    # Menggunakan Numeric type dengan presisi 9 digit (6 di belakang koma)
    latitude = db.Column(db.Numeric(precision=9, scale=6), nullable=False)
    longitude = db.Column(db.Numeric(precision=9, scale=6), nullable=False)
    
    __table_args__ = (
        CheckConstraint('latitude BETWEEN -90 AND 90', name='check_latitude'),
        CheckConstraint('longitude BETWEEN -180 AND 180', name='check_longitude'),
    )

    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')),
        onupdate=lambda: datetime.now(pytz.timezone('Asia/Jakarta'))
    )
    
    def __repr__(self):
        return f'<AgendaAttendee {self.agenda_id} {self.user_id}>'