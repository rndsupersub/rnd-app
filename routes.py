from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from app import db
from models import User, Project, SWOT, PESTLE, BMC
import requests
from bs4 import BeautifulSoup
import re
import json
from requests_html import HTMLSession

UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'xls', 'doc'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

routes_bp = Blueprint('routes', __name__)

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

@routes_bp.route('/')
@routes_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', title='Dashboard')

@routes_bp.route('/projects')
@login_required
def projects():
    user_projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('project.html', projects=user_projects)

@routes_bp.route('/project/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'rnd_staff')
def new_project():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        project_type = request.form.get('project_type', 'Main')
        status = request.form.get('status', 'On Track')
        google_drive_link = request.form.get('google_drive_link')
        
        if not name:
            flash('Nama proyek harus diisi.', 'danger')
            return render_template('project_form.html')
        
        new_project = Project(
            name=name,
            description=description,
            project_type=project_type,
            status=status,
            google_drive_link=google_drive_link,
            user_id=current_user.id
        )
        
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        if start_date:
            new_project.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            new_project.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{datetime.utcnow().timestamp()}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                new_project.file_path = file_path
        
        db.session.add(new_project)
        db.session.commit()
        flash('Proyek berhasil dibuat!', 'success')
        return redirect(url_for('routes.projects'))
    
    return render_template('project_form.html')

@routes_bp.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'rnd_staff')
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id and current_user.role != 'admin':
        flash('Anda tidak memiliki akses ke proyek ini.', 'danger')
        return redirect(url_for('routes.projects'))
    
    if request.method == 'POST':
        project.name = request.form.get('name')
        project.description = request.form.get('description')
        project.project_type = request.form.get('project_type', 'Main')
        project.status = request.form.get('status', 'On Track')
        project.google_drive_link = request.form.get('google_drive_link')
        
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        if start_date:
            project.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            project.start_date = None
        if end_date:
            project.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            project.end_date = None
        
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename and allowed_file(file.filename):
                if project.file_path and os.path.exists(project.file_path):
                    os.remove(project.file_path)
                filename = secure_filename(file.filename)
                unique_filename = f"{datetime.utcnow().timestamp()}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                project.file_path = file_path
        
        db.session.commit()
        flash('Proyek berhasil diperbarui!', 'success')
        return redirect(url_for('routes.view_project', project_id=project.id))
    
    return render_template('project_edit.html', project=project)

@routes_bp.route('/project/<int:project_id>')
@login_required
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id and current_user.role != 'admin':
        flash('Anda tidak memiliki akses ke proyek ini.', 'danger')
        return redirect(url_for('routes.projects'))
    return render_template('project_detail.html', project=project)

@routes_bp.route('/project/<int:project_id>/download')
@login_required
def download_file(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id and current_user.role != 'admin':
        flash('Anda tidak memiliki akses.', 'danger')
        return redirect(url_for('routes.projects'))
    if not project.file_path or not os.path.exists(project.file_path):
        flash('File tidak ditemukan.', 'danger')
        return redirect(url_for('routes.view_project', project_id=project.id))
    return send_file(project.file_path, as_attachment=True)

# ==================== CRUD SWOT ====================
@routes_bp.route('/swot', methods=['GET', 'POST'])
@login_required
def swot():
    if request.method == 'POST':
        try:
            strengths = request.form.get('strengths')
            weaknesses = request.form.get('weaknesses')
            opportunities = request.form.get('opportunities')
            threats = request.form.get('threats')
            
            swot_data = SWOT.query.filter_by(user_id=current_user.id).first()
            
            if swot_data:
                swot_data.strengths = strengths
                swot_data.weaknesses = weaknesses
                swot_data.opportunities = opportunities
                swot_data.threats = threats
                flash('Data SWOT berhasil diupdate!', 'success')
            else:
                new_swot = SWOT(
                    strengths=strengths,
                    weaknesses=weaknesses,
                    opportunities=opportunities,
                    threats=threats,
                    user_id=current_user.id
                )
                db.session.add(new_swot)
                flash('Data SWOT berhasil disimpan!', 'success')
            
            db.session.commit()
        except Exception as e:
            print(f"ERROR SWOT: {e}")
            flash(f'Terjadi kesalahan: {e}', 'danger')
        
        return redirect(url_for('routes.swot'))
    
    swot_data = SWOT.query.filter_by(user_id=current_user.id).first()
    swot_list = SWOT.query.filter_by(user_id=current_user.id).all()
    return render_template('swot.html', swot=swot_data, swot_list=swot_list)

# ==================== CRUD PESTLE ====================
@routes_bp.route('/pestle', methods=['GET', 'POST'])
@login_required
def pestle():
    if request.method == 'POST':
        try:
            political = request.form.get('political')
            economic = request.form.get('economic')
            social = request.form.get('social')
            technological = request.form.get('technological')
            legal = request.form.get('legal')
            environmental = request.form.get('environmental')
            
            pestle_data = PESTLE.query.filter_by(user_id=current_user.id).first()
            
            if pestle_data:
                pestle_data.political = political
                pestle_data.economic = economic
                pestle_data.social = social
                pestle_data.technological = technological
                pestle_data.legal = legal
                pestle_data.environmental = environmental
                flash('Data PESTLE berhasil diupdate!', 'success')
            else:
                new_pestle = PESTLE(
                    political=political,
                    economic=economic,
                    social=social,
                    technological=technological,
                    legal=legal,
                    environmental=environmental,
                    user_id=current_user.id
                )
                db.session.add(new_pestle)
                flash('Data PESTLE berhasil disimpan!', 'success')
            
            db.session.commit()
        except Exception as e:
            print(f"ERROR PESTLE: {e}")
            flash(f'Terjadi kesalahan: {e}', 'danger')
        
        return redirect(url_for('routes.pestle'))
    
    pestle_data = PESTLE.query.filter_by(user_id=current_user.id).first()
    pestle_list = PESTLE.query.filter_by(user_id=current_user.id).all()
    return render_template('pestle.html', pestle=pestle_data, pestle_list=pestle_list)

# ==================== CRUD BMC ====================
@routes_bp.route('/bmc', methods=['GET', 'POST'])
@login_required
def bmc():
    if request.method == 'POST':
        try:
            key_partners = request.form.get('key_partners')
            key_activities = request.form.get('key_activities')
            key_resources = request.form.get('key_resources')
            value_proposition = request.form.get('value_proposition')
            customer_relationships = request.form.get('customer_relationships')
            channels = request.form.get('channels')
            customer_segments = request.form.get('customer_segments')
            cost_structure = request.form.get('cost_structure')
            revenue_streams = request.form.get('revenue_streams')
            
            bmc_data = BMC.query.filter_by(user_id=current_user.id).first()
            
            if bmc_data:
                bmc_data.key_partners = key_partners
                bmc_data.key_activities = key_activities
                bmc_data.key_resources = key_resources
                bmc_data.value_proposition = value_proposition
                bmc_data.customer_relationships = customer_relationships
                bmc_data.channels = channels
                bmc_data.customer_segments = customer_segments
                bmc_data.cost_structure = cost_structure
                bmc_data.revenue_streams = revenue_streams
                flash('Data BMC berhasil diupdate!', 'success')
            else:
                new_bmc = BMC(
                    key_partners=key_partners,
                    key_activities=key_activities,
                    key_resources=key_resources,
                    value_proposition=value_proposition,
                    customer_relationships=customer_relationships,
                    channels=channels,
                    customer_segments=customer_segments,
                    cost_structure=cost_structure,
                    revenue_streams=revenue_streams,
                    user_id=current_user.id
                )
                db.session.add(new_bmc)
                flash('Data BMC berhasil disimpan!', 'success')
            
            db.session.commit()
        except Exception as e:
            print(f"ERROR BMC: {e}")
            flash(f'Terjadi kesalahan: {e}', 'danger')
        
        return redirect(url_for('routes.bmc'))
    
    bmc_data = BMC.query.filter_by(user_id=current_user.id).first()
    bmc_list = BMC.query.filter_by(user_id=current_user.id).all()
    return render_template('bmc.html', bmc=bmc_data, bmc_list=bmc_list)

# ==================== ANALISIS PRODUK E-COMMERCE ====================
@routes_bp.route('/product-analysis', methods=['GET', 'POST'])
@login_required
def product_analysis():
    product_data = None
    error = None
    
    if request.method == 'POST':
        url = request.form.get('product_url')
        
        if not url:
            error = "Silakan masukkan link produk."
        else:
            try:
                session = HTMLSession()
                response = session.get(url)
                response.html.render(sleep=1, timeout=10)
                
                name_element = response.html.find('.product-name', first=True) or response.html.find('.shopee-product-name', first=True)
                product_name = name_element.text if name_element else "Tidak ditemukan"
                
                price_element = response.html.find('.product-price', first=True) or response.html.find('.shopee-product-price', first=True)
                price = price_element.text if price_element else "Tidak ditemukan"
                
                sold_element = response.html.find('.product-sold', first=True) or response.html.find('.shopee-product-sold', first=True)
                sold = sold_element.text if sold_element else "Tidak ditemukan"
                
                rating_element = response.html.find('.product-rating', first=True) or response.html.find('.shopee-product-rating', first=True)
                rating = rating_element.text if rating_element else "Tidak ditemukan"
                
                specs = {}
                spec_elements = response.html.find('.product-specification-item')
                for item in spec_elements:
                    key = item.find('.spec-name', first=True)
                    value = item.find('.spec-value', first=True)
                    if key and value:
                        specs[key.text] = value.text
                
                product_data = {
                    'name': product_name,
                    'price': price,
                    'sold': sold,
                    'rating': rating,
                    'url': url,
                    'platform': 'Shopee' if 'shopee' in url.lower() else 'Tokopedia' if 'tokopedia' in url.lower() else 'Lainnya',
                    'image': '',
                    'description': '',
                    'specs': specs
                }
                
            except Exception as e:
                error = f"Gagal memproses data: {str(e)}"
                print(f"Scraping error: {e}")
    
    return render_template('product_analysis.html', product=product_data, error=error)