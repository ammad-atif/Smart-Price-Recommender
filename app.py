import gradio as gr
import pandas as pd
import plotly.graph_objects as go

# Load CSV
df = pd.read_csv("predicted_prices.csv")

# Fix Shopify URLs
def fix_url(url):
    if isinstance(url, str) and url.startswith("/s/files"):
        return "https://cdn.shopify.com" + url
    return url

df["image_url"] = df["image_url"].apply(fix_url)

# Compute best predicted model (closest to actual)
df["best_predicted_price"] = df[[
    "predicted_price_elastic_net",
    "predicted_price_linear_regression",
    "predicted_price_random_forest"
]].sub(df["cleaned_price"], axis=0).abs().idxmin(axis=1)

pred_cols = [
    "predicted_price_elastic_net",
    "predicted_price_linear_regression",
    "predicted_price_random_forest"
]

df["best_predicted_value"] = df.apply(
    lambda r: r[r["best_predicted_price"]],
    axis=1
)

df["deal_label"] = ""

# ---------- Sorting Helper ----------
def apply_sorting(df, sort_by):
    if sort_by == "Name A-Z":
        return df.sort_values("cleaned_name")
    elif sort_by == "Price Low-High":
        return df.sort_values("cleaned_price")
    elif sort_by == "Price High-Low":
        return df.sort_values("cleaned_price", ascending=False)
    elif sort_by == "Predicted Low-High":
        return df.sort_values("predicted_price_elastic_net")
    elif sort_by == "Predicted High-Low":
        return df.sort_values("predicted_price_elastic_net", ascending=False)
    return df
# ---------- Live time scarper ----------
import random
import time
from selenium_stealth import stealth
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys

def create_stealth_driver(headless=False):
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    ]
    ua = random.choice(USER_AGENTS)
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f"--user-agent={ua}")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")  # ensures elements are visible in headless

    if headless:
        chrome_options.add_argument("--headless=new")  # modern Chrome headless
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")  # ensures full page renders

    driver = webdriver.Chrome(options=chrome_options)

    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
    )
    return driver

def scrape_al_fateh(driver, word_to_search, wait_time=10):
    """
    Scrape Al-Fatah store for products
    Returns: list of products with store name, or empty list on error
    """
    try:
        store_name = "Al-Fateh"
        AL_FATEH_GROCERY_URL = f"https://alfatah.pk/search?q={word_to_search}"
        
        driver.get(AL_FATEH_GROCERY_URL)
        wait = WebDriverWait(driver, wait_time)
        
        product_cards = wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, ".col-6.col-sm-4.col-md-3.col-lg-2")
        ))
        
        products_details = []
        for product in product_cards:
            try:
                a_element = product.find_element(By.CSS_SELECTOR, "a[class='product-title-ellipsis']")
                product_link = a_element.get_attribute("href")
                product_name = a_element.text
                product_price= product.find_element(By.CLASS_NAME, "product-price").text
                image_container=product.find_element(By.CLASS_NAME, "image")
                image_url=image_container.find_element(By.TAG_NAME, "img").get_attribute("src")

                
                products_details.append({
                    "store": store_name,
                    "name": product_name,
                    "product-link": product_link,
                    "price": product_price,
                    "image_url": image_url
                })
            except Exception as e:
                print(f"[{store_name}] Error extracting product: {str(e)}")
                continue
        
        # Filter for relevance
        filtered_products = get_filtered_products(products_details, word_to_search)
        
        print(f"[{store_name}] Found {len(filtered_products)} relevant products")
        return filtered_products
        
    except Exception as e:
        print(f"[Al-Fateh] Error during scraping: {str(e)}")
        return []


def scrape_metro(driver, word_to_search, wait_time=10):
    try:
        store_name = "Metro"
        METRO_GROCERY_URL = f"https://www.metro-online.pk/search/{word_to_search}?searchText={word_to_search}"
        
        driver.get(METRO_GROCERY_URL)
        wait = WebDriverWait(driver, wait_time)
        
        product_cards = wait.until(EC.presence_of_all_elements_located(
            (By.CLASS_NAME, "CategoryGrid_product_card__FUMXW")
        ))

        products_details = []

        for product_card in product_cards:
            try:
                product_link=product_card.find_element(By.TAG_NAME, "a").get_attribute("href")
                name = product_card.find_element(By.CLASS_NAME, "CategoryGrid_product_name__3nYsN").text
                price = product_card.find_element(By.CLASS_NAME, "CategoryGrid_product_price__Svf8T").text
                
                image_container=product_card.find_element(By.CLASS_NAME, "CategoryGrid_productImg_container__Ga1ll")
                image_url=image_container.find_element(By.TAG_NAME, "img").get_attribute("src")
                products_details.append({
                        "store": store_name,
                        "name": name,
                        "product-link": product_link,
                        "price": price,
                        "image_url": image_url
                    })
            except Exception as e:
                print(f"[{store_name}] Error extracting product details: {str(e)}")
                continue
        
        
        # Filter for relevance
        filtered_products = get_filtered_products(products_details, word_to_search)

        print(f"[{store_name}] Found {len(filtered_products)} products")
        return filtered_products

    except Exception as e:
        print(f"[Metro] Error during scraping: {str(e)}")
        return []


def scrape_jalalsons(driver, word_to_search, wait_time=10):
    """
    Scrape Jalal Sons store for products with name and price
    Returns: list of products with store name, or empty list on error
    """
    try:
        store_name = "Jalal Sons"
        JALALSONS_GROCERY_URL = f"https://jalalsons.com.pk/shop?query={word_to_search}"
        
        driver.get(JALALSONS_GROCERY_URL)
        wait = WebDriverWait(driver, wait_time)
        
        # Close banner if present
        try:
            banner_close_button = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".cursor-pointer.ms-auto")
            ))
            banner_close_button.click()
        except TimeoutException:
            print(f"[{store_name}] No banner appeared")
        
        # Select location from dropdown
        try:
            from selenium.webdriver.support.ui import Select
            location_dropdown = wait.until(EC.presence_of_element_located(
                (By.ID, "selectDeliveryBranch")
            ))
            select_object = Select(location_dropdown)
            all_options = select_object.options
            
            enabled_options = [
                opt for opt in all_options
                if opt.is_enabled() and opt.get_attribute('value') != ""
            ]
            
            if enabled_options:
                random_option = random.choice(enabled_options)
                select_object.select_by_visible_text(random_option.text)
                
                try:
                    submit_button = driver.find_element(By.CLASS_NAME, "current_loc_pop_btn")
                    submit_button.click()
                except Exception as e:
                    print(f"[{store_name}] No button to confirm location selection: {str(e)}")
        except:
            print(f"[{store_name}] location box removed or not found")
        
        # Get products
        product_cards = wait.until(EC.presence_of_all_elements_located(
            (By.CLASS_NAME, "single_product_theme")
        ))

        products_details = []

        for product_card in product_cards:
            try:
                product_link = product_card.find_element(By.TAG_NAME, "a").get_attribute("href")
                name = product_card.find_element(By.CLASS_NAME, "product_name_theme").text
                
                currency = product_card.find_element(By.CLASS_NAME, "item-currency").text
                value = product_card.find_element(By.CLASS_NAME, "price-value").text
                price = f"{currency} {value.strip()}"
                image_url=product_card.find_element(By.TAG_NAME, "img").get_attribute("src")
                
                products_details.append({
                    "store": store_name,
                    "name": name,
                    "product-link": product_link,
                    "price": price,
                    "image_url":image_url
                })
            except Exception as e:
                print(f"[{store_name}] Error extracting product details: {str(e)}")
                continue
        
        
        filtered_products = get_filtered_products(products_details, word_to_search)
        print(f"[{store_name}] Found {len(filtered_products)} products")
        return filtered_products

    except Exception as e:
        print(f"[Jalal Sons] Error during scraping: {str(e)}")
        return []


def scrape_carrefour(driver, word_to_search, wait_time=10):
    """
    Scrape Carrefour store for products with name, price, and image
    Returns: list of products with store name, or empty list on error
    """
    store_name = "Carrefour"
    CAREFOUR_GROCERY_URL = f"https://www.carrefour.pk/mafpak/en/search?keyword={word_to_search}"
    
    try:
        driver.get(CAREFOUR_GROCERY_URL)
        wait = WebDriverWait(driver, 15)
        
        # Wait until product grid is visible
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.relative")))
        
        # Find all product cards
        product_cards = driver.find_elements(By.CSS_SELECTOR, "div.relative")
        products_details = []
        
        for card in product_cards:
            try:
                # Product link
                link_tag = card.find_element(By.CSS_SELECTOR, "a[href*='/p/']")
                link_href = link_tag.get_attribute("href")
                if link_href.startswith("/"):
                    link = "https://www.carrefour.pk" + link_href
                else:
                    link = link_href
                
                # Image
                img_tag = card.find_element(By.TAG_NAME, "img")
                image_url = img_tag.get_attribute("src")
                
                # Name
                name_span = card.find_element(By.CSS_SELECTOR, "div.line-clamp-2 span")
                name = name_span.text.strip()
                
                # Price (PKR)
                price_int = card.find_element(By.CSS_SELECTOR, "div.text-lg.font-bold").text
                price_frac = card.find_element(By.CSS_SELECTOR, "div.text-2xs.font-bold").text
                price = f"{price_int}.{price_frac} PKR"
                
                products_details.append({
                    "store": store_name,
                    "name": name,
                    "product-link": link,
                    "price": price,
                    "image_url": image_url
                })
            except Exception as e:
                continue
        
        # Filter products for relevance
        filtered_products = get_filtered_products(products_details, word_to_search)
        print(f"[{store_name}] Found {len(filtered_products)} products")
        return filtered_products
        
    except Exception as e:
        print(f"[{store_name}] Error during scraping: {str(e)}")
        return []


def scrape_imtiaz(driver, word_to_search, wait_time=5):
    """
    Scrape Imtiaz store for products with pagination
    Returns: list of products with store name, or empty list on error
    """
    try:
        store_name = "Imtiaz"
        IMTIAZ_GROCERY_URL = f"https://shop.imtiaz.com.pk/search?q={word_to_search}"
        driver.get(IMTIAZ_GROCERY_URL)
        wait = WebDriverWait(driver, wait_time)

        products_details = []
        
        # Select location
        try:
            area = wait.until(EC.presence_of_element_located(
                (By.XPATH, "/html/body/div[2]/div[3]/div/div/div/div/div[3]/div[3]/div/div/input")
            ))
            area.send_keys(Keys.ENTER)
            area.send_keys(Keys.DOWN)
            area.send_keys(Keys.DOWN)
            area.send_keys(Keys.ENTER)
            
            submit_button = wait.until(EC.presence_of_element_located(
                (By.XPATH, "/html/body/div[2]/div[3]/div/div/div/div/div[3]/button")
            ))
            submit_button.click()
        except TimeoutException:
            print(f"[{store_name}] No location box appeared")
        
        # Get initial products
        try:
            products = wait.until(EC.presence_of_all_elements_located(
                (By.CLASS_NAME, "hazle-product-item_product_item__FSm1N")
            ))
            
            current_url = driver.current_url
            
            # Extract products and handle pagination
            while True:
                try:
                    # Wait for products to load
                    products = wait.until(EC.presence_of_all_elements_located(
                        (By.CLASS_NAME, "hazle-product-item_product_item__FSm1N")
                    ))
                    time.sleep(5)  # Extra wait to ensure full load
                    # Extract all products on current page
                    for product in products:
                        try:
                            product_text_container = product.find_element(By.CLASS_NAME, "hazle-product-item_product_item_text_container__Apuq1")
                            
                            product_name = product_text_container.find_element(By.CLASS_NAME, "hazle-product-item_product_item_description__ejRDa").text.strip()
                            product_price = product_text_container.find_element(By.CLASS_NAME, "hazle-product-item_product_item_price_label__ET_we").text.strip()
                            
                            product_link_id = product.get_attribute("id")
                            product_link = f"https://shop.imtiaz.com.pk/product/{product_link_id}"
                            
                            image_url = product.find_element(By.TAG_NAME, "img").get_attribute("src")
                            
                            products_details.append({
                                "store": store_name,
                                "name": product_name,
                                "product-link": product_link,
                                "price": product_price,
                                "image_url": image_url
                            })
                        except Exception as e:
                            print(f"[{store_name}] Error extracting product info: {str(e)}")
                            continue
                    
                    # Try to find and click Next button
                    try:
                        button = driver.find_element(By.XPATH, "//button[normalize-space()='Next']")
                        
                        if button.get_attribute("disabled"):
                            print(f"[{store_name}] Reached last page")
                            break
                        else:
                            current_url = driver.current_url
                            button.click()
                            time.sleep(10)  # Wait for page to load
                    except NoSuchElementException:
                        print(f"[{store_name}] Last page reached")
                        break
                        
                except Exception as e:
                    print(f"[{store_name}] Error in pagination loop: {str(e)}")
                    break
            
            filtered_products = get_filtered_products(products_details, word_to_search)
            print(f"[{store_name}] Found {len(filtered_products)} products")
            return filtered_products
            
        except TimeoutException:
            print(f"[{store_name}] No products found")
            return []
        
    except Exception as e:
        print(f"[{store_name}] Error during scraping: {str(e)}")
        return []


# ===== MAIN SCRAPING FUNCTION =====
def scrape_all_stores(driver, word_to_search):
    """
    Scrape all 5 stores and combine results into a single list
    Returns: list of all products from all stores with store names
    """
    all_products = []
    
    print(f"\n{'='*60}")
    print(f"Starting scraping for: '{word_to_search}'")
    print(f"{'='*60}\n")
    
    # Scrape each store
    stores_scrapers = [
        ("Al-Fateh", scrape_al_fateh),
        ("Metro", scrape_metro),
        ("Jalal Sons", scrape_jalalsons),
        ("Carrefour", scrape_carrefour),
        ("Imtiaz", scrape_imtiaz),
    ]
    
    for store_label, scraper_func in stores_scrapers:
        print(f"\n[SCRAPING {store_label.upper()}]")
        try:
            products = scraper_func(driver, word_to_search)
            all_products.extend(products)
        except Exception as e:
            print(f"FATAL ERROR for {store_label}: {str(e)}")
            continue
    
    print(f"\n{'='*60}")
    print(f"Scraping Complete!")
    print(f"Total products collected: {len(all_products)}")
    print(f"{'='*60}\n")
    
    return all_products


def get_filtered_products(products_details, word_to_search):
    """
    Filter products for relevance based on search term
    Returns: list of relevant products
    """
    filtered = []
    search_term_lower = word_to_search.lower()
    
    for p in products_details:
        title_lower = p["name"].lower()
        if search_term_lower in title_lower:
            filtered.append(p)
            
    return filtered




# ---------- Bar Chart: Average Price ----------
def build_price_chart(df_filtered):
    if df_filtered.empty:
        return go.Figure()
    
    avg_prices = df_filtered.groupby("store")[["cleaned_price",
                                               "predicted_price_elastic_net",
                                               "predicted_price_linear_regression",
                                               "predicted_price_random_forest"]].mean().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=avg_prices["store"],
        y=avg_prices["cleaned_price"],
        name="Actual Price"
    ))
    fig.add_trace(go.Bar(
        x=avg_prices["store"],
        y=avg_prices["predicted_price_elastic_net"],
        name="Elastic Net"
    ))
    fig.add_trace(go.Bar(
        x=avg_prices["store"],
        y=avg_prices["predicted_price_linear_regression"],
        name="Linear Regression"
    ))
    fig.add_trace(go.Bar(
        x=avg_prices["store"],
        y=avg_prices["predicted_price_random_forest"],
        name="Random Forest"
    ))

    fig.update_layout(
        title="Average Price per Store",
        plot_bgcolor='black',
        paper_bgcolor='black',
        font_color='white',
        barmode='group',
        xaxis_title="Store",
        yaxis_title="Price (Rs)"
    )
    return fig

# ---------- Pie Chart: Number of Products ----------
def build_store_pie_chart(df_filtered):
    if df_filtered.empty:
        return go.Figure()
    
    store_counts = df_filtered["store"].value_counts().reset_index()
    store_counts.columns = ["store", "count"]

    fig = go.Figure(go.Pie(
        labels=store_counts["store"],
        values=store_counts["count"],
        textinfo='label+value',
        marker=dict(colors=['#ffffff', '#888888', '#cccccc', '#bbbbbb']),
        hole=0.3
    ))

    fig.update_layout(
        title="Number of Products per Store",
        font_color='white',
        paper_bgcolor='black',
        plot_bgcolor='black'
    )
    return fig

# ---------- Scatter: Actual vs All Model Predictions (Normalized) ----------
def build_actual_vs_best(df_filtered):
    if df_filtered.empty:
        return go.Figure()

    # Select columns to normalize
    cols = [
        "cleaned_price",
        "predicted_price_elastic_net",
        "predicted_price_linear_regression",
        "predicted_price_random_forest"
    ]

    # Min-max normalization
    df_norm = df_filtered.copy()
    for col in cols:
        min_val = df_norm[col].min()
        max_val = df_norm[col].max()
        df_norm[col] = (df_norm[col] - min_val) / (max_val - min_val)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_norm["cleaned_price"],
        y=df_norm["predicted_price_elastic_net"],
        mode="markers",
        name="Elastic Net",
        line=dict(color='white')
    ))
    fig.add_trace(go.Scatter(
        x=df_norm["cleaned_price"],
        y=df_norm["predicted_price_linear_regression"],
        mode="markers",
        name="Linear Regression"
    ))
    fig.add_trace(go.Scatter(
        x=df_norm["cleaned_price"],
        y=df_norm["predicted_price_random_forest"],
        mode="markers",
        name="Random Forest"
    ))

    fig.update_layout(
        title="Normalized Comparison: Actual vs Predicted Prices",
        xaxis_title="Actual Price (Normalized)",
        yaxis_title="Predicted Price (Normalized)",
        paper_bgcolor="black",
        plot_bgcolor="black",
        font_color="white",
        xaxis=dict(tick0=0, dtick=0.2),
        yaxis=dict(tick0=0, dtick=0.2)
    )
    return fig

# ---------- Vertical Store Comparison ----------
def build_vertical_store_comparison(results):
    stores = sorted(results["store"].unique())
    html = "<div style='display:flex; gap:30px; width:100%; background:black; padding:10px;'>"
    for store in stores:
        store_items = results[results["store"] == store]
        html += f"<div style='flex:1; min-width:250px; border:2px solid white; border-radius:10px; padding:15px;'>"
        html += f"<h2 style='text-align:center; color:white; margin-bottom:15px;'>{store}</h2>"
        for _, row in store_items.iterrows():
            img = row["image_url"]
            name = row["cleaned_name"]
            price = row["cleaned_price"]
            html += f"""
            <div style='margin-bottom:25px; border:1px solid white; border-radius:8px; padding:10px; background:black;'>
                <img src="{img}" style="width:100%; height:160px; object-fit:contain; border-radius:8px;" />
                <h4 style='font-size:14px; margin:8px 0; color:white;'>{name}</h4>
                {f"<p style='color:red; font-size:14px; font-weight:bold;'>🏷️ {row['deal_label']}</p>" if row['deal_label'] else ""}
                <p style='margin:4px 0; font-size:14px; color:white;'>Price: <b>Rs {price}</b></p>
                <p style='margin:4px 0; font-size:14px; color:yellow;'>Best Prediction: <b>Rs {row['best_predicted_value']:.2f}</b></p>
            </div>
            """
        html += "</div>"
    html += "</div>"
    return html

# ---------- Normal Card Layout ----------
def build_normal_cards(results):
    html = "<div style='background:black; padding:10px;'>"
    html += "<h2 style='color:white; margin-bottom:15px;'>Showing All Products</h2>"
    html += "<div style='display:flex; flex-wrap:wrap; gap:20px;'>"
    for _, row in results.iterrows():
        img = row["image_url"]
        name = row["cleaned_name"]
        store = row["store"]
        price = row["cleaned_price"]
        html += f"""
        <div style='width:220px; border:1px solid white; border-radius:10px; padding:10px; background:black; box-shadow:0 2px 5px rgba(255,255,255,0.15); font-family:Arial;'>
            <img src="{img}" style="width:100%; height:180px; object-fit:contain; border-radius:8px;" />
            <h4 style='font-size:14px; margin:8px 0; height:40px; overflow:hidden; color:white;'>{name}</h4>
            <p style='margin:4px 0; font-size:12px; color:white;'>Store: {store}</p>
            {f"<p style='color:red; font-size:14px; font-weight:bold;'>🏷️ {row['deal_label']}</p>" if row['deal_label'] else ""}
            <p style='margin:4px 0; font-size:14px; font-weight:bold; color:white;'>Rs {price}</p>
            <p style='margin:4px 0; font-size:14px; color:yellow;'>Best Prediction: <b>Rs {row['best_predicted_value']:.2f}</b></p>
        </div>
        """
    html += "</div></div>"
    return html
# ---------- Real time scraping ----------
def run_realtime_scraper(keyword):
    if not keyword.strip():
        return "<p style='color:white;'>Please enter a product keyword.</p>"
    
    driver = create_stealth_driver()
    try:
        products = scrape_all_stores(driver, keyword)
        if not products:
            return "<p style='color:white;'>No products found.</p>"

        html = "<div style='background:black; display:flex; flex-wrap:wrap; gap:20px;'>"
        for p in products:
            img = p.get("image_url", "")
            name = p.get("name", "")
            store = p.get("store", "")
            price = p.get("price", "")
            link = p.get("product-link", p.get("link", "#"))
            html += f"""
            <div style='width:220px; border:1px solid white; border-radius:10px; padding:10px; background:black;'>
                <img src="{img}" style="width:100%; height:180px; object-fit:contain; border-radius:8px;" />
                <h4 style='color:white; font-size:14px; margin:5px 0; height:40px; overflow:hidden;'>{name}</h4>
                <p style='color:white; font-size:12px;'>Store: {store}</p>
                <p style='color:white; font-size:14px; font-weight:bold;'>Rs {price}</p>
                <a href="{link}" target="_blank" style='color:yellow; font-size:12px;'>View Product</a>
            </div>
            """
        html += "</div>"
        return html

    finally:
        driver.quit()
# ---------- Main Function ----------
def search_products(query, selected_stores, selected_categories, sort_by):
    temp = df.copy()
    if selected_stores:
        temp = temp[temp["store"].isin(selected_stores)]
    if selected_categories:
        temp = temp[temp["cleaned_category"].isin(selected_categories)]
    temp = apply_sorting(temp, sort_by)
    if query.strip():
        temp = temp[temp["cleaned_name"].str.contains(query, case=False, na=False)]
    if temp.empty:
        return go.Figure(), go.Figure(), go.Figure(), "<h3 style='color:white;'>No products found</h3>"

    temp['diff_best'] = temp['best_predicted_value'] - temp['cleaned_price']

    best_deal = temp.loc[[temp['diff_best'].idxmax()]]
    best_deal["deal_label"] = "BEST DEAL"
    others = temp.drop(best_deal.index)
    others["deal_label"] = ""
    temp = pd.concat([best_deal, others], ignore_index=True)

    # Build visualizations
    avg_price_fig = build_price_chart(temp)
    store_pie_fig = build_store_pie_chart(temp)
    best_pred_fig = build_actual_vs_best(temp)

    # Layout
    if query.strip() and temp["store"].nunique() > 1:
        html = build_vertical_store_comparison(temp)
    else:
        html = build_normal_cards(temp)

    return avg_price_fig, store_pie_fig, best_pred_fig, html

# ---------- Gradio UI ----------
with gr.Blocks() as demo:

    with gr.Tab("Dashboard"):
        gr.Markdown("<h2 style='color:white; text-align:center;'>🛒 Product Search Dashboard</h2>")
        all_stores = sorted(df["store"].unique())
        all_categories = sorted(df["cleaned_category"].unique())

        with gr.Row():
            query = gr.Textbox(label="Search Product", placeholder="Search...")
            sort_by = gr.Dropdown(
                ["Default", "Name A-Z", "Price Low-High", "Price High-Low",
                "Predicted Low-High", "Predicted High-Low"],
                value="Default", label="Sort By"
            )

        with gr.Row():
            store_filter = gr.CheckboxGroup(all_stores, label="Filter by Store")
            category_filter = gr.CheckboxGroup(all_categories, label="Filter by Category")

        # Charts row
        with gr.Row():
            avg_price_chart = gr.Plot()
            store_pie_chart = gr.Plot()
            best_pred_scatter = gr.Plot()

        results_html = gr.HTML()

        # Show all products initially
        results_html.value = build_normal_cards(df)
        avg_price_chart.value = build_price_chart(df)
        store_pie_chart.value = build_store_pie_chart(df)
        best_pred_scatter.value = build_actual_vs_best(df)

        inputs = [query, store_filter, category_filter, sort_by]
        outputs = [avg_price_chart, store_pie_chart, best_pred_scatter, results_html]

        for inp in inputs:
            inp.change(search_products, inputs=inputs, outputs=outputs)
    
    with gr.Tab("Real-Time Scraper"):
        gr.Markdown("<h2 style='color:white; text-align:center;'>🛒 Real-Time Scraper</h2>")
        scraper_input = gr.Textbox(label="Enter Keyword", placeholder="e.g., pepsi")
        scraper_button = gr.Button("Scrape Now")
        scraper_output = gr.HTML()
        scraper_button.click(run_realtime_scraper, inputs=[scraper_input], outputs=[scraper_output])

demo.launch(server_name="127.0.0.1", server_port=2020)