from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session
from functools import wraps
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
import pytz
from .models import db, Admin, User, AttendanceLocation, Agenda  # Import the Admin model

bp = Blueprint('admin', __name__, url_prefix='/admin')

def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('admin.login'))
        return func(*args, **kwargs)
    return decorated_function

csrf = CSRFProtect()

@bp.route('/login', methods=['GET', 'POST'])
@csrf.exempt
def login():
    from .forms import LoginForm
    form = LoginForm(request.form)
    error = None
    if request.method == 'GET':
        return render_template('login.jinja', form=form)
    elif request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):  # Assuming you have a method to check the password
            session['logged_in'] = True
            session['admin_id'] = admin.id
            session['username'] = admin.username
            return redirect(url_for('admin.dashboard'))
        else:
            error = 'Username atau password salah'
            return render_template('login.jinja', form=form, error=error)
        
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))

@bp.route('/dashboard')
@login_required 
def dashboard():
    return render_template('admin/dashboard.jinja')

@bp.route('/users', methods=['GET'])
@login_required
def users():
    return render_template('admin/users/index.jinja')

@bp.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    from .forms import AddUserForm
    form = AddUserForm(request.form)
    form_url = url_for('admin.add_user')
    if request.method == 'GET':
        return render_template('admin/users/add.jinja', form_url=form_url, form=form)
    elif request.method == 'POST':
        if form.validate_on_submit():
            new_user = User(
                username=form.username.data,
                full_name=form.full_name.data,
                gender=form.gender.data,
                division=form.division.data
            )
            new_user.set_password(form.password.data)
            try:
                db.session.add(new_user)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred while adding the user: {str(e)}"
                return render_template('admin/users/add.jinja', form_url=form_url, form=form, error=error)
            return redirect(url_for('admin.users'))
        else:
            return render_template('admin/users/add.jinja', form_url=form_url, form=form)

@bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    from .forms import EditUserForm
    user = User.query.get(user_id)
    form_url = url_for('admin.edit_user', user_id=user_id)
    if not user:
        return redirect(url_for('admin.users'))
    
    form = EditUserForm(request.form, obj=user)
    if request.method == 'GET':
        return render_template('admin/users/add.jinja', edit=True, form_url=form_url, form=form)
    elif request.method == 'POST':
        if form.validate_on_submit():
            user.username = form.username.data
            user.full_name = form.full_name.data
            user.gender = form.gender.data
            user.division = form.division.data
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred while updating the user: {str(e)}"
                return render_template('admin/users/add.jinja', edit=True, form_url=form_url, user_id=user.id, form=form, error=error)
            return redirect(url_for('admin.users'))
        else:
            error = "Form validation failed"
            return render_template('admin/users/add.jinja',edit=True, form_url=form_url, form=form, error=error)

@bp.route('/get_users', methods=['GET'])
@login_required
def get_users():
    from .models import User
    # Correct filter syntax for non-deleted users
    users = User.query.filter(User.deleted_at.is_(None)).all()
    
    # Use list comprehension for cleaner data formatting
    data = [{
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'gender': user.gender,
        'division': user.division,
        'actions': f'<a href="{url_for("admin.edit_user", user_id=user.id)}" class="btn btn-sm btn-primary">Edit</a> '
                    f'<button onclick="konfirm_hapus({user.id})" class="btn btn-sm btn-danger">Delete</button>'
    } for user in users]
    
    return jsonify({"data": data})

@bp.route('/users/delete', methods=['POST'])
@login_required
def delete_user():
    id = request.json.get('id')
    user = User.query.get(id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    try:
        user.deleted_at = datetime.now(pytz.timezone('Asia/Jakarta'))  # Assuming you have a deleted_at field in your User model
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An error occurred while deleting the user: {str(e)}"}), 500
    
    return jsonify({"success": True}), 200

@bp.route('/locations', methods=['GET'])
@login_required
def locations():
    return render_template('admin/locations/index.jinja')

@bp.route('/add_location', methods=['GET', 'POST'])
@login_required
def add_location():
    from .forms import AttendanceLocationForm
    form = AttendanceLocationForm(request.form)
    form_url = url_for('admin.add_location')
    if request.method == 'GET':
        return render_template('admin/locations/add.jinja', form_url=form_url, form=form)
    elif request.method == 'POST':
        if form.validate_on_submit():
            new_location = AttendanceLocation(
                name=form.name.data,
                short_name=form.short_name.data,
                description=form.description.data,
                latitude=form.latitude.data,
                longitude=form.longitude.data
            )
            try:
                db.session.add(new_location)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred while adding the location: {str(e)}"
                return render_template('admin/locations/add.jinja', form_url=form_url, form=form, error=error)
            return redirect(url_for('admin.locations'))
        else:
            return render_template('admin/locations/add.jinja', form_url=form_url, form=form)

@bp.route('/edit_location/<int:location_id>', methods=['GET', 'POST'])
@login_required
def edit_location(location_id):
    from .forms import AttendanceLocationForm
    location = AttendanceLocation.query.get(location_id)
    form_url = url_for('admin.edit_location', location_id=location_id)
    if not location:
        return redirect(url_for('admin.locations'))
    
    form = AttendanceLocationForm(request.form, obj=location)
    if request.method == 'GET':
        return render_template('admin/locations/add.jinja', edit=True, form_url=form_url, form=form)
    elif request.method == 'POST':
        if form.validate_on_submit():
            location.name = form.name.data
            location.short_name = form.short_name.data
            location.description = form.description.data
            location.latitude = form.latitude.data
            location.longitude = form.longitude.data
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                error = f"An error occurred while updating the location: {str(e)}"
                return render_template('admin/locations/add.jinja', edit=True, form_url=form_url, location_id=location.id, form=form, error=error)
            return redirect(url_for('admin.locations'))
        else:
            error = "Form validation failed"
            return render_template('admin/locations/add.jinja', edit=True, form_url=form_url, form=form, error=error)

@bp.route('/get_locations', methods=['GET'])
@login_required
def get_locations():
    locations = AttendanceLocation.query.filter(AttendanceLocation.deleted_at.is_(None)).all()
    
    data = [{
        'id': location.id,
        'name': location.name,
        'short_name': location.short_name,
        'description': location.description,
        'latitude': location.latitude,
        'longitude': location.longitude,
        'actions': f'<a href="{url_for("admin.edit_location", location_id=location.id)}" class="btn btn-sm btn-primary">Edit</a> '
                    f'<button onclick="konfirm_hapus({location.id})" class="btn btn-sm btn-danger">Delete</button>'
    } for location in locations]
    
    return jsonify({"data": data})

@bp.route('/locations/delete', methods=['POST'])
@login_required
def delete_location():
    id = request.json.get('id')
    location = AttendanceLocation.query.get(id)
    if not location:
        return jsonify({"error": "Location not found"}), 404
    
    try:
        location.deleted_at = datetime.now(pytz.timezone('Asia/Jakarta'))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An error occurred while deleting the location: {str(e)}"}), 500
    
    return jsonify({"success": True}), 200