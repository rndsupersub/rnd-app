from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from functools import wraps
from app import db
from models import User

routes_bp = Blueprint('routes', __name__)

def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('auth.login'))  # ← ini yang diganti
            if current_user.role not in roles:
                flash('Anda tidak memiliki akses ke halaman ini.', 'danger')
                return redirect(url_for('routes.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@routes_bp.route('/')
@routes_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', title='Dashboard')