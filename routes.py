from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
import os
import json
import requests
import time
from werkzeug.utils import secure_filename
from app import db
from models import User, Project, SWOT, PESTLE, BMC

# ==================== KONFIGURASI AWAL ====================
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'xls', 'doc'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

routes_bp = Blueprint('routes', __name__)

# ==================== KONFIGURASI APIFY (DARI ENV) ====================
APIFY_API_KEY = os.getenv('APIFY_API_KEY')
APIFY_ACTOR_ID = os.getenv('APIFY_ACTOR_ID', 'xtracto~shopee-scraper')

if not APIFY_API_KEY:
    print("⚠️ PERINGATAN: APIFY_API_KEY tidak ditemukan di environment!")

# ==================== DEKORATOR AKSES ====================
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

# ==================== ROUTE DASHBOARD ====================
@routes_bp.route('/')
@routes_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', title='Dashboard')

# ==================== ROUTE PROYEK ====================
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

@routes_bp.route('/project/<int:project_id>/delete')
@login_required
@roles_required('admin', 'rnd_staff')
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id and current_user.role != 'admin':
        flash('Anda tidak memiliki akses.', 'danger')
        return redirect(url_for('routes.projects'))
    db.session.delete(project)
    db.session.commit()
    flash('Proyek berhasil dihapus!', 'success')
    return redirect(url_for('routes.projects'))

# ==================== CRUD SWOT ====================
@routes_bp.route('/swot', methods=['GET', 'POST'])
@login_required
def swot():
    if request.method == 'POST':
        try:
            project_name = request.form.get('project_name')
            strengths = request.form.get('strengths')
            weaknesses = request.form.get('weaknesses')
            opportunities = request.form.get('opportunities')
            threats = request.form.get('threats')
            edit_id = request.form.get('edit_id')

            if edit_id:
                swot_item = SWOT.query.get(edit_id)
                if swot_item and swot_item.user_id == current_user.id:
                    swot_item.project_name = project_name
                    swot_item.strengths = strengths
                    swot_item.weaknesses = weaknesses
                    swot_item.opportunities = opportunities
                    swot_item.threats = threats
                    flash('Data SWOT berhasil diupdate!', 'success')
            else:
                new_swot = SWOT(
                    project_name=project_name,
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
            flash(f'Terjadi kesalahan: {e}', 'danger')
        return redirect(url_for('routes.swot'))

    swot_list = SWOT.query.filter_by(user_id=current_user.id).all()
    swot_list_json = [{
        'id': item.id,
        'project_name': item.project_name,
        'strengths': item.strengths,
        'weaknesses': item.weaknesses,
        'opportunities': item.opportunities,
        'threats': item.threats,
        'created_at': item.created_at.isoformat() if item.created_at else None,
        'updated_at': item.updated_at.isoformat() if item.updated_at else None
    } for item in swot_list]
    return render_template('swot.html', swot_list_json=swot_list_json)

@routes_bp.route('/swot/<int:swot_id>/delete')
@login_required
def delete_swot(swot_id):
    swot_item = SWOT.query.get_or_404(swot_id)
    if swot_item.user_id != current_user.id:
        flash('Anda tidak memiliki akses.', 'danger')
        return redirect(url_for('routes.swot'))
    db.session.delete(swot_item)
    db.session.commit()
    flash('Data SWOT berhasil dihapus!', 'success')
    return redirect(url_for('routes.swot'))

# ==================== CRUD PESTLE ====================
@routes_bp.route('/pestle', methods=['GET', 'POST'])
@login_required
def pestle():
    if request.method == 'POST':
        try:
            project_name = request.form.get('project_name')
            political = request.form.get('political')
            economic = request.form.get('economic')
            social = request.form.get('social')
            technological = request.form.get('technological')
            legal = request.form.get('legal')
            environmental = request.form.get('environmental')
            edit_id = request.form.get('edit_id')

            if edit_id:
                pestle_item = PESTLE.query.get(edit_id)
                if pestle_item and pestle_item.user_id == current_user.id:
                    pestle_item.project_name = project_name
                    pestle_item.political = political
                    pestle_item.economic = economic
                    pestle_item.social = social
                    pestle_item.technological = technological
                    pestle_item.legal = legal
                    pestle_item.environmental = environmental
                    flash('Data PESTLE berhasil diupdate!', 'success')
            else:
                new_pestle = PESTLE(
                    project_name=project_name,
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
            flash(f'Terjadi kesalahan: {e}', 'danger')
        return redirect(url_for('routes.pestle'))

    pestle_list = PESTLE.query.filter_by(user_id=current_user.id).all()
    pestle_list_json = [{
        'id': item.id,
        'project_name': item.project_name,
        'political': item.political,
        'economic': item.economic,
        'social': item.social,
        'technological': item.technological,
        'legal': item.legal,
        'environmental': item.environmental,
        'created_at': item.created_at.isoformat() if item.created_at else None,
        'updated_at': item.updated_at.isoformat() if item.updated_at else None
    } for item in pestle_list]
    return render_template('pestle.html', pestle_list_json=pestle_list_json)

@routes_bp.route('/pestle/<int:pestle_id>/delete')
@login_required
def delete_pestle(pestle_id):
    pestle_item = PESTLE.query.get_or_404(pestle_id)
    if pestle_item.user_id != current_user.id:
        flash('Anda tidak memiliki akses.', 'danger')
        return redirect(url_for('routes.pestle'))
    db.session.delete(pestle_item)
    db.session.commit()
    flash('Data PESTLE berhasil dihapus!', 'success')
    return redirect(url_for('routes.pestle'))

# ==================== CRUD BMC ====================
@routes_bp.route('/bmc', methods=['GET', 'POST'])
@login_required
def bmc():
    if request.method == 'POST':
        try:
            project_name = request.form.get('project_name')
            key_partners = request.form.get('key_partners')
            key_activities = request.form.get('key_activities')
            key_resources = request.form.get('key_resources')
            value_proposition = request.form.get('value_proposition')
            customer_relationships = request.form.get('customer_relationships')
            channels = request.form.get('channels')
            customer_segments = request.form.get('customer_segments')
            cost_structure = request.form.get('cost_structure')
            revenue_streams = request.form.get('revenue_streams')
            edit_id = request.form.get('edit_id')

            if edit_id:
                bmc_item = BMC.query.get(edit_id)
                if bmc_item and bmc_item.user_id == current_user.id:
                    bmc_item.project_name = project_name
                    bmc_item.key_partners = key_partners
                    bmc_item.key_activities = key_activities
                    bmc_item.key_resources = key_resources
                    bmc_item.value_proposition = value_proposition
                    bmc_item.customer_relationships = customer_relationships
                    bmc_item.channels = channels
                    bmc_item.customer_segments = customer_segments
                    bmc_item.cost_structure = cost_structure
                    bmc_item.revenue_streams = revenue_streams
                    flash('Data BMC berhasil diupdate!', 'success')
            else:
                new_bmc = BMC(
                    project_name=project_name,
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
            flash(f'Terjadi kesalahan: {e}', 'danger')
        return redirect(url_for('routes.bmc'))

    bmc_list = BMC.query.filter_by(user_id=current_user.id).all()
    bmc_list_json = [{
        'id': item.id,
        'project_name': item.project_name,
        'key_partners': item.key_partners,
        'key_activities': item.key_activities,
        'key_resources': item.key_resources,
        'value_proposition': item.value_proposition,
        'customer_relationships': item.customer_relationships,
        'channels': item.channels,
        'customer_segments': item.customer_segments,
        'cost_structure': item.cost_structure,
        'revenue_streams': item.revenue_streams,
        'created_at': item.created_at.isoformat() if item.created_at else None,
        'updated_at': item.updated_at.isoformat() if item.updated_at else None
    } for item in bmc_list]
    return render_template('bmc.html', bmc_list_json=bmc_list_json)

@routes_bp.route('/bmc/<int:bmc_id>/delete')
@login_required
def delete_bmc(bmc_id):
    bmc_item = BMC.query.get_or_404(bmc_id)
    if bmc_item.user_id != current_user.id:
        flash('Anda tidak memiliki akses.', 'danger')
        return redirect(url_for('routes.bmc'))
    db.session.delete(bmc_item)
    db.session.commit()
    flash('Data BMC berhasil dihapus!', 'success')
    return redirect(url_for('routes.bmc'))

# ==================== ANALISIS PRODUK (APIFY API) ====================
@routes_bp.route('/product-analysis', methods=['GET', 'POST'])
@login_required
def product_analysis():
    product_data = None
    error = None

    if not APIFY_API_KEY:
        error = "API Key Apify tidak ditemukan. Silakan set APIFY_API_KEY di environment."
        return render_template('product_analysis.html', product=product_data, error=error)

    if request.method == 'POST':
        url = request.form.get('product_url')
        
        if not url:
            error = "Silakan masukkan link produk."
        else:
            try:
                clean_url = url.split('?')[0]
                
                # ========== 1. JALANKAN ACTOR APIFY ==========
                run_payload = {
                    "country": "id",
                    "mode": "url",
                    "url": clean_url
                }
                
                run_response = requests.post(
                    f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs",
                    params={"token": APIFY_API_KEY},
                    json=run_payload,
                    timeout=60
                )
                
                if run_response.status_code == 201:
                    run_data = run_response.json()
                    run_id = run_data.get("data", {}).get("id")
                    
                    if run_id:
                        # ========== 2. TUNGGU HASIL ==========
                        max_wait = 60
                        wait_time = 0
                        result_data = None
                        
                        while wait_time < max_wait:
                            time.sleep(3)
                            wait_time += 3
                            
                            status_response = requests.get(
                                f"https://api.apify.com/v2/actor-runs/{run_id}",
                                params={"token": APIFY_API_KEY},
                                timeout=30
                            )
                            
                            if status_response.status_code == 200:
                                status_data = status_response.json()
                                run_status = status_data.get("data", {}).get("status")
                                
                                if run_status == "SUCCEEDED":
                                    result_response = requests.get(
                                        f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items",
                                        params={"token": APIFY_API_KEY},
                                        timeout=30
                                    )
                                    
                                    if result_response.status_code == 200:
                                        result_data = result_response.json()
                                        break
                                elif run_status in ["FAILED", "TIMED-OUT", "ABORTED"]:
                                    error = f"Run gagal: {run_status}"
                                    break
                        
                        if result_data and len(result_data) > 0:
                            product_info = result_data[0]
                            
                            product_name = (
                                product_info.get('name') or 
                                product_info.get('title') or 
                                product_info.get('description') or 
                                'Tidak ditemukan'
                            )
                            
                            price = product_info.get('price')
                            if not price:
                                price = product_info.get('price_min')
                            if price:
                                price = f"Rp {price:,.0f}".replace(",", ".")
                            else:
                                price = "Tidak ditemukan"
                            
                            sold = product_info.get('historical_sold')
                            if sold:
                                sold = f"{sold:,}".replace(",", ".")
                            else:
                                sold = "Tidak ditemukan"
                            
                            rating = product_info.get('rating_star')
                            if rating:
                                rating = f"{rating} ⭐"
                            else:
                                rating = "Tidak ditemukan"
                            
                            specs = {}
                            attributes = product_info.get('attributes', [])
                            if attributes:
                                for attr in attributes:
                                    if isinstance(attr, dict):
                                        key = attr.get('name', '')
                                        value = attr.get('value', '')
                                        if key and value:
                                            specs[key] = value
                            
                            variants = []
                            tier_variations = product_info.get('tier_variations', [])
                            if tier_variations:
                                for tier in tier_variations:
                                    if isinstance(tier, dict):
                                        var_name = tier.get('name', '')
                                        var_options = tier.get('options', [])
                                        if var_name and var_options:
                                            variants.append(f"{var_name}: {', '.join(var_options)}")
                            
                            if variants:
                                specs['Varian'] = '; '.join(variants)
                            
                            product_data = {
                                'name': product_name,
                                'price': price,
                                'sold': sold,
                                'rating': rating,
                                'url': clean_url,
                                'platform': 'Shopee' if 'shopee' in url.lower() else 'Tokopedia' if 'tokopedia' in url.lower() else 'Lainnya',
                                'image': product_info.get('image', ''),
                                'description': product_info.get('description', ''),
                                'specs': specs
                            }
                        elif not error:
                            error = "Tidak ada data produk yang ditemukan."
                    else:
                        error = "Gagal mendapatkan run ID dari Apify."
                else:
                    error = f"Gagal menjalankan Actor: {run_response.status_code} - {run_response.text}"
                    
            except Exception as e:
                error = f"Gagal memproses data: {str(e)}"
                print(f"Error: {e}")

    return render_template('product_analysis.html', product=product_data, error=error)