from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
import os
import re
import json
import requests
from bs4 import BeautifulSoup
from werkzeug.utils import secure_filename
from app import db
from models import User, Project, SWOT, PESTLE, BMC

# ==================== KONFIGURASI AWAL ====================
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'xls', 'doc'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

routes_bp = Blueprint('routes', __name__)

# ==================== KONFIGURASI BRIGHT DATA ====================
BRIGHT_DATA_API_KEY = "a024e68a-3426-4fc2-8b57-2ad8eb1a61d3"
BRIGHT_DATA_URL = "https://api.brightdata.com/request"

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

# ==================== HELPER: BRIGHT DATA SCRAPER ====================
def scrape_with_brightdata(url):
    """Scrape URL menggunakan Bright Data Web Unlocker"""
    headers = {
        "Authorization": f"Bearer {BRIGHT_DATA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "zone": "mcp_unlocker",
        "url": url,
        "format": "raw",
        "country": "id",
        "render_js": True,
        "wait_for_selector": "h1"
    }
    response = requests.post(BRIGHT_DATA_URL, json=payload, headers=headers, timeout=60)
    return response


def parse_tokopedia(html, url):
    """Parse HTML Tokopedia"""
    soup = BeautifulSoup(html, 'html.parser')
    product_data = {
        'name': 'Tidak ditemukan',
        'price': 'Tidak ditemukan',
        'sold': 'Tidak ditemukan',
        'sold_per_month': 'Tidak ditemukan',
        'rating': 'Tidak ditemukan',
        'url': url,
        'platform': 'Tokopedia',
        'image': '',
        'description': '',
        'specs': {},
        'variants': {}
    }

    # === NAMA PRODUK ===
    name_selectors = [
        ('h1', {'data-testid': 'lblPDPDetailProductName'}),
        ('h1', {'class': re.compile(r'css-\w+')}),
        ('meta', {'property': 'og:title'}),
    ]
    for tag, attrs in name_selectors:
        el = soup.find(tag, attrs)
        if el:
            product_data['name'] = el.get('content', el.get_text(strip=True))
            break

    # === HARGA ===
    price_selectors = [
        ('div', {'data-testid': 'lblPDPDetailProductPrice'}),
        ('span', {'data-testid': 'lblPDPDetailProductPrice'}),
        ('div', {'class': re.compile(r'price|harga', re.I)}),
    ]
    for tag, attrs in price_selectors:
        el = soup.find(tag, attrs)
        if el:
            price_text = el.get_text(strip=True)
            if 'Rp' in price_text or price_text.replace('.', '').isdigit():
                product_data['price'] = price_text
                break

    if product_data['price'] == 'Tidak ditemukan':
        meta_price = soup.find('meta', {'property': 'product:price:amount'})
        if meta_price:
            amount = meta_price.get('content', '')
            try:
                product_data['price'] = f"Rp {int(float(amount)):,}".replace(',', '.')
            except:
                pass

    # === TERJUAL ===
    sold_el = soup.find(string=re.compile(r'terjual|sold', re.I))
    if sold_el:
        parent = sold_el.parent
        text = parent.get_text(strip=True)
        product_data['sold'] = text
        numbers = re.findall(r'\d+', text.replace('.', ''))
        if numbers:
            try:
                total = int(numbers[0])
                product_data['sold_per_month'] = f"~{total // 12:,} / bulan (estimasi)".replace(',', '.')
            except:
                pass

    # === RATING ===
    rating_selectors = [
        ('span', {'data-testid': 'lblPDPDetailProductRatingNumber'}),
        ('span', {'class': re.compile(r'rating|review', re.I)}),
    ]
    for tag, attrs in rating_selectors:
        el = soup.find(tag, attrs)
        if el:
            product_data['rating'] = el.get_text(strip=True)
            break

    # === GAMBAR ===
    img = soup.find('meta', {'property': 'og:image'})
    if img:
        product_data['image'] = img.get('content', '')

    # === DESKRIPSI ===
    desc_el = soup.find('div', {'data-testid': 'lblPDPDescriptionProduk'})
    if desc_el:
        product_data['description'] = desc_el.get_text(strip=True)[:500]

    # === SPESIFIKASI ===
    spec_table = soup.find('table', {'data-testid': re.compile(r'spec|spesifikasi', re.I)})
    if spec_table:
        rows = spec_table.find_all('tr')
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 2:
                key = cols[0].get_text(strip=True)
                val = cols[1].get_text(strip=True)
                if key and val:
                    product_data['specs'][key] = val

    # === VARIAN (Ukuran, Warna) ===
    variant_sections = soup.find_all('div', {'data-testid': re.compile(r'variant|varian', re.I)})
    for section in variant_sections:
        label = section.find('p') or section.find('span')
        if label:
            label_text = label.get_text(strip=True)
            options = section.find_all('button')
            if options:
                product_data['variants'][label_text] = [o.get_text(strip=True) for o in options if o.get_text(strip=True)]

    # === FALLBACK: JSON-LD ===
    json_ld = soup.find('script', {'type': 'application/ld+json'})
    if json_ld:
        try:
            data = json.loads(json_ld.string)
            if isinstance(data, list):
                data = data[0]
            if product_data['name'] == 'Tidak ditemukan' and data.get('name'):
                product_data['name'] = data['name']
            if product_data['price'] == 'Tidak ditemukan' and data.get('offers'):
                offers = data['offers']
                if isinstance(offers, list):
                    offers = offers[0]
                price = offers.get('price', '')
                if price:
                    product_data['price'] = f"Rp {int(float(price)):,}".replace(',', '.')
            if not product_data['description'] and data.get('description'):
                product_data['description'] = data['description'][:500]
            if not product_data['image'] and data.get('image'):
                imgs = data['image']
                product_data['image'] = imgs[0] if isinstance(imgs, list) else imgs
            for prop in data.get('additionalProperty', []):
                k = prop.get('name', '')
                v = prop.get('value', '')
                if k and v:
                    product_data['specs'][k] = v
        except:
            pass

    return product_data


def parse_shopee(html, url):
    """Parse HTML Shopee"""
    soup = BeautifulSoup(html, 'html.parser')
    product_data = {
        'name': 'Tidak ditemukan',
        'price': 'Tidak ditemukan',
        'sold': 'Tidak ditemukan',
        'sold_per_month': 'Tidak ditemukan',
        'rating': 'Tidak ditemukan',
        'url': url,
        'platform': 'Shopee',
        'image': '',
        'description': '',
        'specs': {},
        'variants': {}
    }

    # === JSON-LD dulu (paling reliable) ===
    json_ld = soup.find('script', {'type': 'application/ld+json'})
    if json_ld:
        try:
            data = json.loads(json_ld.string)
            if isinstance(data, list):
                data = data[0]
            if data.get('name'):
                product_data['name'] = data['name']
            if data.get('offers'):
                offers = data['offers']
                if isinstance(offers, list):
                    offers = offers[0]
                price = offers.get('price', '')
                if price:
                    product_data['price'] = f"Rp {int(float(price)):,}".replace(',', '.')
            if data.get('description'):
                product_data['description'] = data['description'][:500]
            if data.get('image'):
                imgs = data['image']
                product_data['image'] = imgs[0] if isinstance(imgs, list) else imgs
            if data.get('aggregateRating'):
                product_data['rating'] = str(data['aggregateRating'].get('ratingValue', 'Tidak ditemukan'))
            for prop in data.get('additionalProperty', []):
                k = prop.get('name', '')
                v = prop.get('value', '')
                if k and v:
                    product_data['specs'][k] = v
        except:
            pass

    # === FALLBACK META ===
    if product_data['name'] == 'Tidak ditemukan':
        meta_title = soup.find('meta', {'property': 'og:title'})
        if meta_title:
            product_data['name'] = meta_title.get('content', '').split('|')[0].strip()

    if product_data['price'] == 'Tidak ditemukan':
        meta_price = soup.find('meta', {'property': 'product:price:amount'})
        if meta_price:
            try:
                amount = float(meta_price.get('content', 0))
                product_data['price'] = f"Rp {int(amount):,}".replace(',', '.')
            except:
                pass

    if not product_data['image']:
        img = soup.find('meta', {'property': 'og:image'})
        if img:
            product_data['image'] = img.get('content', '')

    # === TERJUAL ===
    page_text = soup.get_text()
    sold_patterns = [
        re.compile(r'(\d[\d\.]*)\s*(terjual|sold)', re.I),
        re.compile(r'(terjual|sold)\s*(\d[\d\.]*)', re.I),
    ]
    for pattern in sold_patterns:
        match = pattern.search(page_text)
        if match:
            sold_text = match.group(0)
            product_data['sold'] = sold_text
            numbers = re.findall(r'\d+', sold_text.replace('.', ''))
            if numbers:
                try:
                    total = int(numbers[0])
                    product_data['sold_per_month'] = f"~{total // 12:,} / bulan (estimasi)".replace(',', '.')
                except:
                    pass
            break

    # === RATING fallback ===
    if product_data['rating'] == 'Tidak ditemukan':
        rating_match = re.search(r'(\d+\.\d+)\s*(rating|bintang)', page_text, re.I)
        if rating_match:
            product_data['rating'] = rating_match.group(1)

    return product_data


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

        new_proj = Project(
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
            new_proj.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            new_proj.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{datetime.utcnow().timestamp()}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                new_proj.file_path = file_path

        db.session.add(new_proj)
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
        project.start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
        project.end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None

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

# ==================== ANALISIS PRODUK (BRIGHT DATA) ====================
@routes_bp.route('/product-analysis', methods=['GET', 'POST'])
@login_required
def product_analysis():
    product_data = None
    error = None

    if request.method == 'POST':
        url = request.form.get('product_url', '').strip()

        if not url:
            error = "Silakan masukkan link produk."
        else:
            try:
                clean_url = url.split('?')[0]

                is_tokopedia = 'tokopedia.com' in url.lower()
                is_shopee = 'shopee.co.id' in url.lower() or 'shopee.com' in url.lower()

                if not is_tokopedia and not is_shopee:
                    error = "Saat ini hanya support Shopee dan Tokopedia."
                else:
                    response = scrape_with_brightdata(clean_url)

                    if response.status_code == 200:
                        html = response.text
                        if is_tokopedia:
                            product_data = parse_tokopedia(html, clean_url)
                        else:
                            product_data = parse_shopee(html, clean_url)

                        if product_data['name'] == 'Tidak ditemukan':
                            error = f"Data produk tidak berhasil diekstrak. Response awal: {html[:300]}"
                            product_data = None
                    else:
                        error = f"Bright Data error {response.status_code}: {response.text[:300]}"

            except Exception as e:
                error = f"Error: {str(e)}"

    return render_template('product_analysis.html', product=product_data, error=error)