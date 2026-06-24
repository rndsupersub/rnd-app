# ==================== ANALISIS PRODUK E-COMMERCE (GRATIS) ====================
import requests
from bs4 import BeautifulSoup
import re
import json

@routes_bp.route('/product-analysis', methods=['GET', 'POST'])
@login_required
def product_analysis():
    product_data = None
    error = None
    raw_html = None
    
    if request.method == 'POST':
        url = request.form.get('product_url')
        
        if not url:
            error = "Silakan masukkan link produk."
        else:
            try:
                # ========== AMBIL DATA DENGAN HEADER ==========
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
                
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # ========== EKSTRAK DATA DARI HTML ==========
                product_name = "Tidak ditemukan"
                price = "Tidak ditemukan"
                sold = "Tidak ditemukan"
                rating = "Tidak ditemukan"
                image_url = ""
                description = ""
                
                # Coba cari di JSON-LD (data terstruktur)
                scripts = soup.find_all('script', type='application/ld+json')
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if data.get('@type') == 'Product':
                            product_name = data.get('name', product_name)
                            price = data.get('offers', {}).get('price', price)
                            description = data.get('description', description)
                            image_url = data.get('image', image_url)
                    except:
                        pass
                
                # Fallback: cari di meta tags
                if product_name == "Tidak ditemukan":
                    og_title = soup.find('meta', property='og:title')
                    if og_title:
                        product_name = og_title.get('content', product_name)
                
                if price == "Tidak ditemukan":
                    price_meta = soup.find('meta', property='product:price:amount')
                    if price_meta:
                        price = price_meta.get('content', price)
                
                # Cari rating
                rating_span = soup.find('span', {'class': re.compile(r'rating|stars|score', re.I)})
                if rating_span:
                    rating = rating_span.text.strip()
                
                # Cari terjual
                sold_span = soup.find('span', {'class': re.compile(r'sold|terjual|sales', re.I)})
                if sold_span:
                    sold = sold_span.text.strip()
                
                # Cari spesifikasi
                specs = {}
                spec_rows = soup.find_all('tr', {'class': re.compile(r'spec|attribute', re.I)})
                for row in spec_rows:
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        specs[th.text.strip()] = td.text.strip()
                
                product_data = {
                    'name': product_name,
                    'price': price,
                    'sold': sold,
                    'rating': rating,
                    'url': url,
                    'platform': 'Shopee' if 'shopee' in url.lower() else 'Tokopedia' if 'tokopedia' in url.lower() else 'Lainnya',
                    'image': image_url,
                    'description': description,
                    'specs': specs
                }
                
            except requests.exceptions.RequestException as e:
                error = f"Gagal mengakses URL: {str(e)}"
            except Exception as e:
                error = f"Gagal memproses data: {str(e)}"
    
    return render_template('product_analysis.html', product=product_data, error=error)