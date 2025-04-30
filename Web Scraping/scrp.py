from flask import Flask, request, render_template_string
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import re
import math

app = Flask(__name__)

# --- Scraper setup ---
def create_driver(chrome_path=None):
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if chrome_path:
        options.binary_location = chrome_path
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

def normalize_amazon_url(url):
    # Validate URL format and extract ASIN
    if not url.startswith("http"):
        raise ValueError("Invalid URL format. Please provide a valid Amazon product URL.")
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    if match:
        asin = match.group(1)
        return f"https://www.amazon.com.tr/dp/{asin}"
    raise ValueError("Invalid Amazon product URL. Could not extract ASIN.")

def get_amazon_reviews(product_url, max_reviews=20, timeout=15, chrome_path=None):
    try:
        clean_url = normalize_amazon_url(product_url)
    except ValueError as e:
        return [{"error": str(e)}]

    driver = None
    reviews = []
    try:
        driver = create_driver(chrome_path)
        max_pages = math.ceil(max_reviews / 10)

        for page in range(1, max_pages + 1):
            page_url = f"{clean_url}?pageNumber={page}"
            print(f"Fetching page: {page_url}")  # Debugging log
            driver.get(page_url)

            try:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-hook='review']"))
                )
                print("Reviews section loaded.")  # Debugging log
            except Exception as e:
                print(f"Timeout or no reviews found: {e}")  # Debugging log
                break

            elems = driver.find_elements(By.CSS_SELECTOR, "[data-hook='review']")
            if not elems:
                print("No review elements found.")  # Debugging log
                break

            for elem in elems:
                if len(reviews) >= max_reviews:
                    break
                try:
                    title = elem.find_element(By.CSS_SELECTOR, "[data-hook='review-title']").text.strip()
                except:
                    title = "No Title"
                try:
                    rating = elem.find_element(By.CSS_SELECTOR, "[data-hook='review-star-rating']").text.strip()
                except:
                    rating = "No Rating"
                try:
                    body = elem.find_element(By.CSS_SELECTOR, "[data-hook='review-body']").text.strip()
                except:
                    body = "No Text"
                reviews.append({"title": title, "rating": rating, "text": body})
                print(f"Review added: {title}, {rating}, {body}")  # Debugging log

            if len(reviews) >= max_reviews:
                break
    except Exception as e:
        reviews.append({"error": f"An error occurred: {str(e)}"})
        print(f"Error: {e}")  # Debugging log
    finally:
        if driver:
            driver.quit()

    return reviews

@app.route('/', methods=['GET', 'POST'])
def index():
    reviews = None
    url = ''
    if request.method == 'POST':
        url = request.form.get('product_url', '').strip()
        reviews = get_amazon_reviews(url, max_reviews=40)

    html = '''
<html lang="tr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Amazon Ürün Yorumları</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">

<nav class="navbar navbar-expand-lg navbar-dark bg-primary">
  <div class="container">
    <a class="navbar-brand" href="#">Amazon Yorum Tarayıcı</a>
  </div>
</nav>

<div class="container py-5">
    <div class="row justify-content-center">
        <div class="col-md-10 col-lg-8">
            <div class="card shadow-sm">
                <div class="card-body">
                    <h2 class="card-title text-center mb-4">Ürün Linki Girin</h2>
                    <form method="post" class="d-flex flex-column gap-3">
                        <input type="text" name="product_url" class="form-control" placeholder="Amazon ürün linkini buraya yapıştırın" value="{{ url }}" required>
                        <button type="submit" class="btn btn-primary btn-lg">Yorumları Getir</button>
                    </form>
                </div>
            </div>

            {% if reviews is not none %}
            <div class="mt-5">
                <h3 class="text-center mb-4">Yorumlar ({{ reviews|length }})</h3>
                {% for rev in reviews %}
                    {% if rev.error %}
                        <div class="alert alert-danger">{{ rev.error }}</div>
                    {% else %}
                        <div class="card mb-4 shadow-sm">
                            <div class="card-body">
                                <h5 class="card-title">{{ rev.title }}</h5>
                                <h6 class="card-subtitle mb-2 text-muted">{{ rev.rating }}</h6>
                                <p class="card-text">{{ rev.text }}</p>
                            </div>
                        </div>
                    {% endif %}
                {% endfor %}
            </div>
            {% endif %}
        </div>
    </div>
</div>

<footer class="bg-primary text-white text-center py-3 mt-5">
    <div class="container">
        <small>© 2025 Amazon Yorum Tarayıcı</small>
    </div>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

    return render_template_string(html, reviews=reviews, url=url)

if __name__ == '__main__':
    app.run(debug=True)