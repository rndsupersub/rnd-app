from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from functools import wraps
from app import db
from models import User

routes_bp = Blueprint('routes', __name__)

# ==================== DECORATOR RBAC ====================
def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('Anda tidak memiliki akses ke halaman ini.', 'danger')
                return redirect(url_for('routes.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==================== HALAMAN DASHBOARD ====================
@routes_bp.route('/')
@routes_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', title='Dashboard')

# ==================== FITUR PROYEK ====================
@routes_bp.route('/projects')
@login_required
def projects():
    """Halaman daftar proyek"""
    return render_template('projects.html', title='Manajemen Proyek')

@routes_bp.route('/project/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'rnd_staff')
def new_project():
    """Halaman buat proyek baru"""
    if request.method == 'POST':
        # Sementara hanya flash pesan
        flash('Fitur tambah proyek sedang dalam pengembangan.', 'info')
        return redirect(url_for('routes.projects'))
    return render_template('project_form.html', title='Buat Proyek Baru')

# ==================== FITUR SWOT ====================
@routes_bp.route('/swot')
@login_required
def swot():
    """Halaman analisis SWOT"""
    return render_template('swot.html', title='Analisis SWOT')

@routes_bp.route('/swot/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'rnd_staff')
def new_swot():
    """Halaman tambah SWOT (placeholder)"""
    flash('Fitur tambah SWOT sedang dalam pengembangan.', 'info')
    return redirect(url_for('routes.swot'))

# ==================== FITUR PESTLE ====================
@routes_bp.route('/pestle')
@login_required
def pestle():
    """Halaman analisis PESTLE"""
    return render_template('pestle.html', title='Analisis PESTLE')

@routes_bp.route('/pestle/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'rnd_staff')
def new_pestle():
    """Halaman tambah PESTLE (placeholder)"""
    flash('Fitur tambah PESTLE sedang dalam pengembangan.', 'info')
    return redirect(url_for('routes.pestle'))

# ==================== FITUR BMC ====================
@routes_bp.route('/bmc')
@login_required
def bmc():
    """Halaman Business Model Canvas"""
    return render_template('bmc.html', title='Business Model Canvas')

@routes_bp.route('/bmc/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'rnd_staff')
def new_bmc():
    """Halaman tambah BMC (placeholder)"""
    flash('Fitur tambah BMC sedang dalam pengembangan.', 'info')
    return redirect(url_for('routes.bmc'))