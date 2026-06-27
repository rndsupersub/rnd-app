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
from models import User, Project, SWOT, PESTLE, BMC, ProductAnalysis

# ==================== KONFIGURASI G.A.S. ====================
GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyL-5S22ZGaIC6tvub569AJOshJQ3Ik-Wime45Vvhv91LM6fFiqDQ9plC-39HenzCikXw/exec"

def kirim_ke_gsheet(sheet_name, data, clear=False):
    """Kirim data ke Google Spreadsheet via G.A.S. Web App"""
    try:
        payload = {
            "sheetName": sheet_name,
            "data": json.dumps(data),
            "clear": str(clear).lower()
        }
        response = requests.post(GAS_WEBHOOK_URL, data=payload, timeout=5)
        print(f"✅ GSheet: {response.text}")
    except Exception as e:
        print(f"❌ GSheet Error: {e}")

# ==================== SYNC PER SHEET ====================
def sync_proyek_to_gsheet():
    """Sinkronkan data proyek ke Google Spreadsheet (clear + rewrite)"""
    try:
        print("📤 Sinkronisasi data proyek ke GSheet...")
        projects = Project.query.all()
        kirim_ke_gsheet('proyek', {}, clear=True)
        for p in projects:
            kirim_ke_gsheet('proyek', {
                'nama_proyek': p.name,
                'deskripsi': p.description or '',
                'tipe': p.project_type,
                'status': p.status,
                'tanggal_mulai': p.start_date.isoformat() if p.start_date else '',
                'tanggal_selesai': p.end_date.isoformat() if p.end_date else '',
                'dibuat_oleh': User.query.get(p.user_id).username if p.user_id else ''
            })
        print("✅ Data proyek berhasil disinkronkan ke GSheet!")
    except Exception as e:
        print(f"❌ GSheet Sync Error: {e}")

def sync_swot_to_gsheet():
    """Sinkronkan data SWOT ke Google Spreadsheet (clear + rewrite)"""
    try:
        print("📤 Sinkronisasi data SWOT ke GSheet...")
        swot_list = SWOT.query.all()
        kirim_ke_gsheet('swot', {}, clear=True)
        for s in swot_list:
            kirim_ke_gsheet('swot', {
                'nama_proyek': s.project_name or '',
                'strengths': s.strengths or '',
                'weaknesses': s.weaknesses or '',
                'opportunities': s.opportunities or '',
                'threats': s.threats or '',
                'dibuat_oleh': User.query.get(s.user_id).username if s.user_id else ''
            })
        print("✅ Data SWOT berhasil disinkronkan ke GSheet!")
    except Exception as e:
        print(f"❌ GSheet Sync Error: {e}")

def sync_pestle_to_gsheet():
    """Sinkronkan data PESTLE ke Google Spreadsheet (clear + rewrite)"""
    try:
        print("📤 Sinkronisasi data PESTLE ke GSheet...")
        pestle_list = PESTLE.query.all()
        kirim_ke_gsheet('pestle', {}, clear=True)
        for p in pestle_list:
            kirim_ke_gsheet('pestle', {
                'nama_proyek': p.project_name or '',
                'political': p.political or '',
                'economic': p.economic or '',
                'social': p.social or '',
                'technological': p.technological or '',
                'legal': p.legal or '',
                'environmental': p.environmental or '',
                'dibuat_oleh': User.query.get(p.user_id).username if p.user_id else ''
            })
        print("✅ Data PESTLE berhasil disinkronkan ke GSheet!")
    except Exception as e:
        print(f"❌ GSheet Sync Error: {e}")

def sync_bmc_to_gsheet():
    """Sinkronkan data BMC ke Google Spreadsheet (clear + rewrite)"""
    try:
        print("📤 Sinkronisasi data BMC ke GSheet...")
        bmc_list = BMC.query.all()
        kirim_ke_gsheet('bmc', {}, clear=True)
        for b in bmc_list:
            kirim_ke_gsheet('bmc', {
                'nama_proyek': b.project_name or '',
                'key_partners': b.key_partners or '',
                'key_activities': b.key_activities or '',
                'key_resources': b.key_resources or '',
                'value_proposition': b.value_proposition or '',
                'customer_relationships': b.customer_relationships or '',
                'channels': b.channels or '',
                'customer_segments': b.customer_segments or '',
                'cost_structure': b.cost_structure or '',
                'revenue_streams': b.revenue_streams or '',
                'dibuat_oleh': User.query.get(b.user_id).username if b.user_id else ''
            })
        print("✅ Data BMC berhasil disinkronkan ke GSheet!")
    except Exception as e:
        print(f"❌ GSheet Sync Error: {e}")

def sync_product_to_gsheet():
    """Sinkronkan data Produk ke Google Spreadsheet (clear + rewrite)"""
    try:
        print("📤 Sinkronisasi data Produk ke GSheet...")
        product_list = ProductAnalysis.query.all()
        kirim_ke_gsheet('produk', {}, clear=True)
        for pr in product_list:
            kirim_ke_gsheet('produk', {
                'nama_produk': pr.product_name or '',
                'harga': pr.price or '',
                'terjual': pr.sold or '',
                'rating': pr.rating or '',
                'platform': pr.platform or '',
                'url': pr.url or '',
                'deskripsi': pr.description or '',
                'spesifikasi': pr.specs or '',
                'dibuat_oleh': User.query.get(pr.user_id).username if pr.user_id else ''
            })
        print("✅ Data Produk berhasil disinkronkan ke GSheet!")
    except Exception as e:
        print(f"❌ GSheet Sync Error: {e}")

# ==================== KONFIGURASI AWAL ====================
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'xls', 'doc'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

routes_bp = Blueprint('routes', __name__)

# ==================== KONFIGURASI APIFY ====================
APIFY_API_KEY = os.getenv('APIFY_API_KEY')
APIFY_ACTOR_ID = os.getenv('APIFY_ACTOR_ID')
if not APIFY_ACTOR_ID:
    APIFY_ACTOR_ID = 'xtracto~shopee-scraper'
if not APIFY_API_KEY:
    print("⚠️ APIFY_API_KEY tidak ditemukan!")

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
    projects = Project.query.all()
    swot_list = SWOT.query.all()
    pestle_list = PESTLE.query.all()
    bmc_list = BMC.query.all()
    product_list = ProductAnalysis.query.all()
    return render_template('dashboard.html', 
                         title='Dashboard',
                         projects=projects,
                         swot_list=swot_list,
                         pestle_list=pestle_list,
                         bmc_list=bmc_list,
                         product_list=product_list)

# ==================== CRUD PROYEK ====================
@routes_bp.route('/projects')
@login_required
def projects():
    projects = Project.query.all()
    return render_template('project.html', projects=projects)

@routes_bp.route('/project/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
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
            name=name, description=description, project_type=project_type,
            status=status, google_drive_link=google_drive_link, user_id=current_user.id
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
        
        kirim_ke_gsheet('proyek', {
            'nama_proyek': name,
            'deskripsi': description or '',
            'tipe': project_type,
            'status': status,
            'tanggal_mulai': start_date or '',
            'tanggal_selesai': end_date or '',
            'dibuat_oleh': current_user.username
        })
        
        flash('Proyek berhasil dibuat!', 'success')
        return redirect(url_for('routes.projects'))
    return render_template('project_form.html')

@routes_bp.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
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
        
        sync_proyek_to_gsheet()
        
        flash('Proyek berhasil diperbarui!', 'success')
        return redirect(url_for('routes.view_project', project_id=project.id))
    return render_template('project_edit.html', project=project)

@routes_bp.route('/project/<int:project_id>/delete')
@login_required
@roles_required('admin')
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    db.session.delete(project)
    db.session.commit()
    
    sync_proyek_to_gsheet()
    
    flash('Proyek berhasil dihapus!', 'success')
    return redirect(url_for('routes.projects'))

@routes_bp.route('/project/<int:project_id>')
@login_required
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project_detail.html', project=project)

@routes_bp.route('/project/<int:project_id>/download')
@login_required
def download_file(project_id):
    project = Project.query.get_or_404(project_id)
    if not project.file_path or not os.path.exists(project.file_path):
        flash('File tidak ditemukan.', 'danger')
        return redirect(url_for('routes.view_project', project_id=project.id))
    return send_file(project.file_path, as_attachment=True)

# ==================== CRUD SWOT ====================
@routes_bp.route('/swot', methods=['GET', 'POST'])
@login_required
def swot():
    if request.method == 'POST':
        if current_user.role != 'admin':
            flash('Anda tidak memiliki akses.', 'danger')
            return redirect(url_for('routes.dashboard'))
        try:
            project_name = request.form.get('project_name')
            strengths = request.form.get('strengths')
            weaknesses = request.form.get('weaknesses')
            opportunities = request.form.get('opportunities')
            threats = request.form.get('threats')
            edit_id = request.form.get('edit_id')
            if edit_id:
                swot_item = SWOT.query.get(edit_id)
                if swot_item:
                    swot_item.project_name = project_name
                    swot_item.strengths = strengths
                    swot_item.weaknesses = weaknesses
                    swot_item.opportunities = opportunities
                    swot_item.threats = threats
                    flash('Data SWOT berhasil diupdate!', 'success')
            else:
                new_swot = SWOT(
                    project_name=project_name, strengths=strengths, weaknesses=weaknesses,
                    opportunities=opportunities, threats=threats, user_id=current_user.id
                )
                db.session.add(new_swot)
                flash('Data SWOT berhasil disimpan!', 'success')
            db.session.commit()
            
            kirim_ke_gsheet('swot', {
                'nama_proyek': project_name,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'opportunities': opportunities,
                'threats': threats,
                'dibuat_oleh': current_user.username
            })
        except Exception as e:
            flash(f'Terjadi kesalahan: {e}', 'danger')
        return redirect(url_for('routes.swot'))
    swot_list = SWOT.query.all()
    swot_list_json = [{
        'id': item.id, 'project_name': item.project_name, 'strengths': item.strengths,
        'weaknesses': item.weaknesses, 'opportunities': item.opportunities, 'threats': item.threats,
        'created_at': item.created_at.isoformat() if item.created_at else None,
        'updated_at': item.updated_at.isoformat() if item.updated_at else None
    } for item in swot_list]
    return render_template('swot.html', swot_list_json=swot_list_json)

@routes_bp.route('/swot/<int:swot_id>/delete')
@login_required
@roles_required('admin')
def delete_swot(swot_id):
    swot_item = SWOT.query.get_or_404(swot_id)
    
    db.session.delete(swot_item)
    db.session.commit()
    
    sync_swot_to_gsheet()
    
    flash('Data SWOT berhasil dihapus!', 'success')
    return redirect(url_for('routes.swot'))

# ==================== CRUD PESTLE ====================
@routes_bp.route('/pestle', methods=['GET', 'POST'])
@login_required
def pestle():
    if request.method == 'POST':
        if current_user.role != 'admin':
            flash('Anda tidak memiliki akses.', 'danger')
            return redirect(url_for('routes.dashboard'))
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
                if pestle_item:
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
                    project_name=project_name, political=political, economic=economic,
                    social=social, technological=technological, legal=legal, environmental=environmental,
                    user_id=current_user.id
                )
                db.session.add(new_pestle)
                flash('Data PESTLE berhasil disimpan!', 'success')
            db.session.commit()
            
            kirim_ke_gsheet('pestle', {
                'nama_proyek': project_name,
                'political': political,
                'economic': economic,
                'social': social,
                'technological': technological,
                'legal': legal,
                'environmental': environmental,
                'dibuat_oleh': current_user.username
            })
        except Exception as e:
            flash(f'Terjadi kesalahan: {e}', 'danger')
        return redirect(url_for('routes.pestle'))
    pestle_list = PESTLE.query.all()
    pestle_list_json = [{
        'id': item.id, 'project_name': item.project_name, 'political': item.political,
        'economic': item.economic, 'social': item.social, 'technological': item.technological,
        'legal': item.legal, 'environmental': item.environmental,
        'created_at': item.created_at.isoformat() if item.created_at else None,
        'updated_at': item.updated_at.isoformat() if item.updated_at else None
    } for item in pestle_list]
    return render_template('pestle.html', pestle_list_json=pestle_list_json)

@routes_bp.route('/pestle/<int:pestle_id>/delete')
@login_required
@roles_required('admin')
def delete_pestle(pestle_id):
    pestle_item = PESTLE.query.get_or_404(pestle_id)
    
    db.session.delete(pestle_item)
    db.session.commit()
    
    sync_pestle_to_gsheet()
    
    flash('Data PESTLE berhasil dihapus!', 'success')
    return redirect(url_for('routes.pestle'))

# ==================== CRUD BMC ====================
@routes_bp.route('/bmc', methods=['GET', 'POST'])
@login_required
def bmc():
    if request.method == 'POST':
        if current_user.role != 'admin':
            flash('Anda tidak memiliki akses.', 'danger')
            return redirect(url_for('routes.dashboard'))
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
                if bmc_item:
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
                    project_name=project_name, key_partners=key_partners,
                    key_activities=key_activities, key_resources=key_resources,
                    value_proposition=value_proposition, customer_relationships=customer_relationships,
                    channels=channels, customer_segments=customer_segments,
                    cost_structure=cost_structure, revenue_streams=revenue_streams,
                    user_id=current_user.id
                )
                db.session.add(new_bmc)
                flash('Data BMC berhasil disimpan!', 'success')
            db.session.commit()
            
            kirim_ke_gsheet('bmc', {
                'nama_proyek': project_name,
                'key_partners': key_partners,
                'key_activities': key_activities,
                'key_resources': key_resources,
                'value_proposition': value_proposition,
                'customer_relationships': customer_relationships,
                'channels': channels,
                'customer_segments': customer_segments,
                'cost_structure': cost_structure,
                'revenue_streams': revenue_streams,
                'dibuat_oleh': current_user.username
            })
        except Exception as e:
            flash(f'Terjadi kesalahan: {e}', 'danger')
        return redirect(url_for('routes.bmc'))
    bmc_list = BMC.query.all()
    bmc_list_json = [{
        'id': item.id, 'project_name': item.project_name,
        'key_partners': item.key_partners, 'key_activities': item.key_activities,
        'key_resources': item.key_resources, 'value_proposition': item.value_proposition,
        'customer_relationships': item.customer_relationships, 'channels': item.channels,
        'customer_segments': item.customer_segments, 'cost_structure': item.cost_structure,
        'revenue_streams': item.revenue_streams,
        'created_at': item.created_at.isoformat() if item.created_at else None,
        'updated_at': item.updated_at.isoformat() if item.updated_at else None
    } for item in bmc_list]
    return render_template('bmc.html', bmc_list_json=bmc_list_json)

@routes_bp.route('/bmc/<int:bmc_id>/delete')
@login_required
@roles_required('admin')
def delete_bmc(bmc_id):
    bmc_item = BMC.query.get_or_404(bmc_id)
    
    db.session.delete(bmc_item)
    db.session.commit()
    
    sync_bmc_to_gsheet()
    
    flash('Data BMC berhasil dihapus!', 'success')
    return redirect(url_for('routes.bmc'))

# ==================== ANALISIS PRODUK ====================
@routes_bp.route('/product-analysis', methods=['GET', 'POST'])
@login_required
def product_analysis():
    product_data = None
    error = None
    edit_id = request.args.get('edit_id')
    edit_data = None
    if edit_id:
        edit_data = ProductAnalysis.query.filter_by(id=edit_id).first()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'save':
            if current_user.role != 'admin':
                flash('Anda tidak memiliki akses.', 'danger')
                return redirect(url_for('routes.dashboard'))
            try:
                project_name = request.form.get('project_name')
                product_name = request.form.get('product_name')
                price = request.form.get('price')
                sold = request.form.get('sold')
                rating = request.form.get('rating')
                platform = request.form.get('platform')
                url = request.form.get('url')
                image = request.form.get('image')
                description = request.form.get('description')
                specs_json = request.form.get('specs_json')
                edit_id = request.form.get('edit_id')
                if edit_id:
                    item = ProductAnalysis.query.get(edit_id)
                    if item:
                        item.project_name = project_name
                        item.product_name = product_name
                        item.price = price
                        item.sold = sold
                        item.rating = rating
                        item.platform = platform
                        item.url = url
                        item.image = image
                        item.description = description
                        item.specs = specs_json
                        flash('Data analisis produk berhasil diupdate!', 'success')
                else:
                    new_item = ProductAnalysis(
                        project_name=project_name, product_name=product_name,
                        price=price, sold=sold, rating=rating, platform=platform,
                        url=url, image=image, description=description, specs=specs_json,
                        user_id=current_user.id
                    )
                    db.session.add(new_item)
                    flash('Data analisis produk berhasil disimpan!', 'success')
                db.session.commit()
                
                kirim_ke_gsheet('produk', {
                    'nama_produk': product_name,
                    'harga': price,
                    'terjual': sold,
                    'rating': rating,
                    'platform': platform,
                    'url': url,
                    'deskripsi': description,
                    'spesifikasi': specs_json,
                    'dibuat_oleh': current_user.username
                })
                
                return redirect(url_for('routes.product_analysis'))
            except Exception as e:
                flash(f'Terjadi kesalahan: {e}', 'danger')
                db.session.rollback()
        elif action == 'analyze':
            url = request.form.get('product_url')
            if not url:
                error = "Silakan masukkan link produk."
            else:
                try:
                    clean_url = url.split('?')[0]
                    run_payload = {"country": "id", "mode": "url", "url": clean_url}
                    run_response = requests.post(
                        f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs",
                        params={"token": APIFY_API_KEY}, json=run_payload, timeout=60
                    )
                    if run_response.status_code == 201:
                        run_data = run_response.json()
                        run_id = run_data.get("data", {}).get("id")
                        if run_id:
                            max_wait, wait_time, result_data = 60, 0, None
                            while wait_time < max_wait:
                                time.sleep(3)
                                wait_time += 3
                                status_response = requests.get(
                                    f"https://api.apify.com/v2/actor-runs/{run_id}",
                                    params={"token": APIFY_API_KEY}, timeout=30
                                )
                                if status_response.status_code == 200:
                                    status_data = status_response.json()
                                    run_status = status_data.get("data", {}).get("status")
                                    if run_status == "SUCCEEDED":
                                        result_response = requests.get(
                                            f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items",
                                            params={"token": APIFY_API_KEY}, timeout=30
                                        )
                                        if result_response.status_code == 200:
                                            result_data = result_response.json()
                                            break
                                    elif run_status in ["FAILED", "TIMED-OUT", "ABORTED"]:
                                        error = f"Run gagal: {run_status}"
                                        break
                            if result_data and len(result_data) > 0:
                                product_info = result_data[0]
                                product_name = product_info.get('name') or product_info.get('title') or product_info.get('description') or 'Tidak ditemukan'
                                price = product_info.get('price_min') or product_info.get('price')
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
                                    'product_name': product_name, 'price': price, 'sold': sold,
                                    'rating': rating, 'platform': 'Shopee' if 'shopee' in url.lower() else 'Tokopedia' if 'tokopedia' in url.lower() else 'Lainnya',
                                    'url': clean_url, 'image': product_info.get('image', ''),
                                    'description': product_info.get('description', ''),
                                    'specs': specs
                                }
                            elif not error:
                                error = "Tidak ada data produk yang ditemukan."
                    else:
                        error = f"Gagal menjalankan Actor: {run_response.status_code} - {run_response.text}"
                except Exception as e:
                    error = f"Gagal memproses data: {str(e)}"
                    print(f"Error: {e}")
    saved_items = ProductAnalysis.query.all()
    saved_items_json = [{
        'id': item.id, 'project_name': item.project_name, 'product_name': item.product_name,
        'price': item.price, 'sold': item.sold, 'rating': item.rating, 'platform': item.platform,
        'url': item.url, 'image': item.image, 'description': item.description,
        'specs': json.loads(item.specs) if item.specs else {},
        'created_at': item.created_at.isoformat() if item.created_at else None,
        'updated_at': item.updated_at.isoformat() if item.updated_at else None
    } for item in saved_items]
    return render_template('product_analysis.html', 
                          product=product_data, error=error,
                          saved_items=saved_items_json, edit_data=edit_data)

@routes_bp.route('/product-analysis/<int:item_id>/delete')
@login_required
@roles_required('admin')
def delete_product_analysis(item_id):
    item = ProductAnalysis.query.get_or_404(item_id)
    
    db.session.delete(item)
    db.session.commit()
    
    sync_product_to_gsheet()
    
    flash('Data analisis produk berhasil dihapus!', 'success')
    return redirect(url_for('routes.product_analysis'))

# ==================== ROUTE DETAIL READ-ONLY ====================
@routes_bp.route('/view_swot/<int:swot_id>')
@login_required
def view_swot(swot_id):
    swot = SWOT.query.get_or_404(swot_id)
    return render_template('view_swot.html', swot=swot)

@routes_bp.route('/view_pestle/<int:pestle_id>')
@login_required
def view_pestle(pestle_id):
    pestle = PESTLE.query.get_or_404(pestle_id)
    return render_template('view_pestle.html', pestle=pestle)

@routes_bp.route('/view_bmc/<int:bmc_id>')
@login_required
def view_bmc(bmc_id):
    bmc = BMC.query.get_or_404(bmc_id)
    return render_template('view_bmc.html', bmc=bmc)

@routes_bp.route('/view_product/<int:product_id>')
@login_required
def view_product(product_id):
    product = ProductAnalysis.query.get_or_404(product_id)
    return render_template('view_product.html', product=product)

# ==================== ROUTE DAFTAR SEMUA DATA ====================
@routes_bp.route('/daftar_swot')
@login_required
def daftar_swot():
    swot_list = SWOT.query.all()
    return render_template('daftar_swot.html', swot_list=swot_list)

@routes_bp.route('/daftar_pestle')
@login_required
def daftar_pestle():
    pestle_list = PESTLE.query.all()
    return render_template('daftar_pestle.html', pestle_list=pestle_list)

@routes_bp.route('/daftar_bmc')
@login_required
def daftar_bmc():
    bmc_list = BMC.query.all()
    return render_template('daftar_bmc.html', bmc_list=bmc_list)

@routes_bp.route('/daftar_product')
@login_required
def daftar_product():
    product_list = ProductAnalysis.query.all()
    return render_template('daftar_product.html', product_list=product_list)