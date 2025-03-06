from flask import Blueprint

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
def admin_home():
    return "Admin Home"

"""Crud Semua Tabel DISINI!"""