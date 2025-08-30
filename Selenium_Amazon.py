# Selenium_Amazon.py
# Run Chromedriver first:
#   chromedriver --port=9515 --allowed-origins="*" --allowed-ips=""
# Then run:
#   python Selenium_Amazon.py --query "wireless headphones" --max_products 3
#
# Results are saved to: scrapes/<query>/<YYYYmmdd_HHMMSS>/results.csv by default.

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import pandas as pd
import re
import pyperclip
import argparse
from pathlib import Path
from datetime import datetime
import sys

# -------------------- small utils --------------------
def sanitize_name(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9._ -]+", "", s)
    s = re.sub(r"\s+", "_", s)
    return s[:80] if s else "query"

def timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

# -------------------- selenium helpers --------------------
def find_element_with_fallback(driver, xpaths):
    for i, xpath in enumerate(xpaths):
        try:
            element = driver.find_element(By.XPATH, xpath)
            print(f"Found element with XPath {i+1}: {xpath}")
            return element
        except:
            continue
    raise Exception("None of the XPaths worked")

def wait_for_page_load(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)
    except:
        time.sleep(5)

def scroll_to_element(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(1)
    except:
        pass

def get_product_link(driver, product_number):
    try:
        print(f"    → Getting product link for product {product_number}...")
        pyperclip.copy("")
        time.sleep(1)
        wait_for_page_load(driver)

        share_button_selectors = [
            '//*[@id="ssf-primary-widget-desktop"]/div/a',
            '//*[@id="ssf-primary-widget-desktop"]//a',
            '//div[@id="ssf-primary-widget-desktop"]//a',
            '//*[contains(@id, "ssf-primary-widget")]//a',
            '//a[contains(@class, "a-popover-trigger")]//span[contains(text(), "Share")]',
            '//span[contains(text(), "Share")]//parent::a',
            '//*[@id="share"]',
            '//button[contains(@aria-label, "Share")]',
            '//a[contains(@href, "share")]'
        ]
        share_clicked = False
        for i, selector in enumerate(share_button_selectors):
            try:
                print(f"    → Trying share button selector {i+1}: {selector}")
                share_button = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                scroll_to_element(driver, share_button)
                try:
                    share_button.click()
                except:
                    driver.execute_script("arguments[0].click();", share_button)
                print(f"    ✓ Clicked share button with selector {i+1}")
                share_clicked = True
                time.sleep(3)
                break
            except Exception as e:
                print(f"    → Share selector {i+1} failed: {str(e)[:50]}...")
                continue
        if not share_clicked:
            print("    ✗ Could not find any share button")
            return "Share button not found"

        copy_link_selectors = [
            '//*[@id="ssf-channel-copy link"]/span[2]',
            '//*[@id="ssf-channel-copy link"]//span[2]',
            '//*[@id="ssf-channel-copy link"]',
            '//span[@id="ssf-channel-copy link"]//span[2]',
            '//div[@id="ssf-channel-copy link"]//span[2]',
            '//*[contains(@id, "copy link")]//span[2]',
            '//*[contains(@id, "copy link")]//span[contains(text(), "Copy link")]',
            '//*[contains(@id, "copy")]//span[text()="Copy link"]',
            '//span[contains(text(), "Copy link")]',
            '//button[contains(text(), "Copy link")]',
            '//a[contains(text(), "Copy link")]',
            '//*[contains(@id, "copy")]//span[2]'
        ]
        copy_clicked = False
        for i, selector in enumerate(copy_link_selectors):
            try:
                print(f"    → Trying copy link selector {i+1}: {selector}")
                copy_link_button = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                scroll_to_element(driver, copy_link_button)
                try:
                    copy_link_button.click()
                except:
                    driver.execute_script("arguments[0].click();", copy_link_button)
                print(f"    ✓ Clicked copy link button with selector {i+1}")
                copy_clicked = True
                time.sleep(3)
                break
            except Exception as e:
                print(f"    → Copy selector {i+1} failed: {str(e)[:50]}...")
                continue
        if not copy_clicked:
            print("    ✗ Could not find copy link button")
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except:
                pass
            return "Copy link button not found"

        for attempt in range(8):
            try:
                time.sleep(1.5)
                copied_link = pyperclip.paste()
                print(f"    → Attempt {attempt + 1}: Clipboard content: '{copied_link[:100]}...'")
                if copied_link and copied_link.strip():
                    copied_link = copied_link.strip()
                    amazon_patterns = [r'https://a\.co/', r'amazon\.com', r'amzn\.to']
                    if any(re.search(p, copied_link, re.IGNORECASE) for p in amazon_patterns):
                        print(f"    ✓ Successfully copied valid Amazon product link: {copied_link}")
                        try:
                            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            time.sleep(1)
                        except:
                            pass
                        return copied_link
                    else:
                        print(f"    → Attempt {attempt + 1}: Not a valid Amazon link, retrying...")
                else:
                    print(f"    → Attempt {attempt + 1}: Clipboard empty or invalid, retrying...")
            except Exception as e:
                print(f"    → Attempt {attempt + 1}: Error accessing clipboard: {e}")

            if attempt < 7:
                try:
                    for selector in copy_link_selectors[:3]:
                        try:
                            driver.find_element(By.XPATH, selector).click()
                            print(f"    → Re-clicked copy button for attempt {attempt + 2}")
                            break
                        except:
                            continue
                except:
                    pass

        print("    ⚠ All clipboard attempts failed, trying alternative methods...")
        try:
            link_elements = driver.find_elements(By.XPATH, '//input[contains(@value, "amazon.com") or contains(@value, "a.co")]')
            for elem in link_elements:
                link_value = elem.get_attribute('value')
                if link_value and ('amazon.com' in link_value or 'a.co' in link_value):
                    print(f"    ✓ Found link in input field: {link_value}")
                    return link_value
        except:
            pass
        try:
            current_url = driver.current_url
            if 'amazon.com' in current_url and '/dp/' in current_url:
                print(f"    ⚠ Using current URL as fallback: {current_url}")
                return current_url
        except:
            pass
        return "Link extraction failed - clipboard and alternatives unsuccessful"

    except Exception as e:
        print(f"    ✗ General error getting product link: {e}")
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except:
            pass
        return f"Error getting link: {str(e)}"

def scrape_product_details(driver, product_url, product_number):
    try:
        print(f"  → Visiting product {product_number} page...")
        driver.get(product_url)
        wait_for_page_load(driver, 10)
        product_link = get_product_link(driver, product_number)

        overall_rating = ""
        rating_selectors = [
            '//*[@id="acrPopover"]/span[1]/a/span',
            '.a-icon-alt',
            '[data-hook="rating-out-of-text"]',
            '.a-size-base.a-color-base',
            '//span[contains(text(), "out of")]',
            '//span[contains(text(), "stars")]',
            '//*[contains(@class, "a-icon-alt")]'
        ]
        for selector in rating_selectors:
            try:
                el = driver.find_element(By.XPATH, selector) if selector.startswith('/') else driver.find_element(By.CSS_SELECTOR, selector)
                text = el.text.strip() or el.get_attribute('textContent').strip()
                if text and ('out of' in text.lower() or 'star' in text.lower()):
                    overall_rating = text
                    break
            except:
                continue

        num_ratings = ""
        num_rating_selectors = [
            '//*[@id="acrCustomerReviewText"]',
            '[data-hook="total-review-count"]',
            '.a-size-base.a-color-secondary',
            '#acrCustomerReviewText',
            '//span[contains(text(), "rating")]',
            '//span[contains(text(), "review")]',
            '//*[contains(text(), "ratings")]'
        ]
        for selector in num_rating_selectors:
            try:
                el = driver.find_element(By.XPATH, selector) if selector.startswith('/') else driver.find_element(By.CSS_SELECTOR, selector)
                text = el.text.strip()
                if text and ('rating' in text.lower() or 'review' in text.lower()):
                    num_ratings = text
                    break
            except:
                continue

        reviews = []
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(2)
        review_selectors = [
            '[data-hook="review-body"] span',
            '.review-text',
            '[data-hook="review-body"]',
            '.cr-original-review-text',
            '//div[@data-hook="review-body"]//span[not(@class)]',
            '//span[contains(@class, "cr-original-review-text")]'
        ]
        review_elements = []
        for selector in review_selectors:
            try:
                elems = driver.find_elements(By.XPATH, selector) if selector.startswith('/') else driver.find_elements(By.CSS_SELECTOR, selector)
                if elems:
                    review_elements = elems
                    print(f"    Found {len(elems)} reviews using selector: {selector}")
                    break
            except:
                continue

        for element in review_elements[:15]:
            try:
                t = element.text.strip()
                if t and 20 < len(t) < 1000:
                    reviews.append(t)
                    if len(reviews) >= 10:
                        break
            except:
                continue

        print(f"    ✓ Collected: Rating={overall_rating}, Reviews={num_ratings}, Review texts={len(reviews)}, Product Link={product_link if isinstance(product_link, str) else ''}")
        return {
            'overall_rating': overall_rating if overall_rating else "Not found",
            'num_ratings': num_ratings if num_ratings else "Not found",
            'reviews': reviews[:10] if reviews else ["No reviews found"],
            'product_link': product_link
        }

    except Exception as e:
        print(f"    ✗ Error scraping details for product {product_number}: {str(e)}")
        return {
            'overall_rating': "Error loading",
            'num_ratings': "Error loading",
            'reviews': ["Error loading reviews"],
            'product_link': "Error loading"
        }

def get_product_info_from_element(driver, product, index):
    try:
        print(f"  Extracting info for product {index}...")
        scroll_to_element(driver, product)
        time.sleep(1)
        asin = product.get_attribute('data-asin')
        print(f"  Debug: Product ASIN: {asin}")

        title = ""
        title_selectors = [
            'h2 a span','h2 span','.a-size-mini .a-color-base','.s-size-mini',
            'h2 .a-link-normal span','[data-cy="title-recipe-title"]','.a-size-base-plus',
            'a span.a-text-normal','.a-size-base','.a-color-base','span.a-text-normal',
            '.s-color-base','.s-size-mini.s-spacing-none.s-color-base','h2.a-size-mini span',
            '.a-link-normal .a-text-normal','.//h2//span[string-length(text()) > 10]',
            './/a[contains(@href, "/dp/")]//span[string-length(text()) > 10]'
        ]
        for selector in title_selectors:
            try:
                el = product.find_element(By.XPATH, selector) if selector.startswith('.//') else product.find_element(By.CSS_SELECTOR, selector)
                title = el.text.strip()
                if title and len(title) > 10 and not title.lower().startswith('sponsored'):
                    print(f"  ✓ Found title: {title[:50]}...")
                    break
            except:
                continue
        if not title:
            try:
                all_text = product.find_elements(By.XPATH, './/span[string-length(text()) > 15]')
                for el in all_text:
                    t = el.text.strip()
                    if t and 15 < len(t) < 200 and not any(w in t.lower() for w in ['sponsored','price','$','rating','stars']):
                        title = t
                        print(f"  ✓ Fallback title: {title[:50]}...")
                        break
            except:
                pass

        url = ""
        url_selectors = [
            'h2 a','.a-link-normal[href*="/dp/"]','a[href*="/dp/"]','.s-link-style a',
            'a.a-text-normal','a[href*="/gp/"]','.a-link-normal',
            f'a[href*="{asin}"]' if asin else None,'.//a[contains(@href, "/dp/")]','.//h2//a'
        ]
        url_selectors = [s for s in url_selectors if s]
        for selector in url_selectors:
            try:
                el = product.find_element(By.XPATH, selector) if selector.startswith('.//') else product.find_element(By.CSS_SELECTOR, selector)
                url = el.get_attribute('href')
                if url and ('/dp/' in url or '/gp/' in url):
                    if not url.startswith('http'):
                        url = "https://www.amazon.com" + url
                    print(f"  ✓ Found URL: {url[:60]}...")
                    break
            except:
                continue

        price = ""
        price_selectors = [
            '.a-price-whole','.a-price .a-offscreen','.a-price-symbol + .a-price-whole',
            '.a-price-range .a-offscreen','.a-price .a-price-whole','.a-price-fraction',
            './/span[contains(@class, "a-price")]//span[@class="a-offscreen"]',
            './/span[contains(text(), "$")]'
        ]
        for selector in price_selectors:
            try:
                el = product.find_element(By.XPATH, selector) if selector.startswith('.//') else product.find_element(By.CSS_SELECTOR, selector)
                price_text = el.text.strip() or el.get_attribute('textContent').strip()
                if price_text and '$' in price_text:
                    price = price_text
                    break
            except:
                continue
        if not price:
            try:
                for el in product.find_elements(By.XPATH, './/span[contains(text(), "$") or contains(@class, "price")]'):
                    t = el.text.strip()
                    if t and '$' in t and len(t) < 20:
                        price = t
                        break
            except:
                price = "Price not available"

        return {'title': title, 'url': url, 'price': price if price else "Price not available", 'asin': asin if asin else "Not found"}
    except Exception as e:
        print(f"  ✗ Error extracting info for product {index}: {str(e)}")
        return None

def scrape_products(driver, max_products=30):
    products_data = []
    print(f"Starting to scrape up to {max_products} products...")
    search_results_url = driver.current_url
    print(f"Search results URL: {search_results_url}")

    wait_for_page_load(driver, 10)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
    time.sleep(3)

    product_infos = []
    product_selectors = [
        '[data-component-type="s-search-result"]',
        '.s-result-item[data-component-type="s-search-result"]',
        '[data-asin]:not([data-asin=""])',
        '.s-result-item',
        '//div[@data-component-type="s-search-result"]',
        '//div[contains(@class, "s-result-item") and @data-asin]'
    ]
    products = []
    for selector in product_selectors:
        try:
            products = driver.find_elements(By.XPATH, selector) if selector.startswith('//') else driver.find_elements(By.CSS_SELECTOR, selector)
            if products:
                print(f"Found {len(products)} products using selector: {selector}")
                break
        except:
            continue
    if not products:
        print("No products found with any selector")
        return pd.DataFrame()

    for i, product in enumerate(products[:max_products * 2], 1):
        try:
            asin = product.get_attribute('data-asin')
            if asin and asin.strip():
                info = get_product_info_from_element(driver, product, i)
                if info and info['title'] and info['url']:
                    product_infos.append(info)
                    if len(product_infos) >= max_products:
                        break
        except:
            continue

    print(f"\nCollected basic info for {len(product_infos)} products from search page")
    for i, product_info in enumerate(product_infos, 1):
        try:
            print(f"\nScraping product {i}/{len(product_infos)}...")
            print(f"  Title: {product_info['title'][:50]}...")
            details = scrape_product_details(driver, product_info['url'], i)

            review_data = {}
            for j, review in enumerate(details['reviews'][:10], 1):
                review_data[f'Review_{j}'] = review
            for j in range(len(details['reviews']) + 1, 11):
                review_data[f'Review_{j}'] = ""

            product_data = {
                'Product_Number': i,
                'Title': product_info['title'],
                'Price': product_info['price'],
                'URL': product_info['url'],
                'ASIN': product_info['asin'],
                'Overall_Rating': details['overall_rating'],
                'Number_of_Ratings': details['num_ratings'],
                'Product_Link': details['product_link'],
                **review_data
            }
            products_data.append(product_data)
            print(f"  ✓ Product {i} completed successfully")

            driver.get(search_results_url)
            wait_for_page_load(driver, 5)
        except Exception as e:
            print(f"✗ Error scraping product {i}: {str(e)}")
            try:
                if driver.current_url != search_results_url:
                    driver.get(search_results_url)
                    wait_for_page_load(driver, 5)
            except:
                pass
            continue

    print(f"\nSuccessfully scraped {len(products_data)} products with detailed information")
    return pd.DataFrame(products_data)

def amazon_detailed_scraper(search_term, max_products=5, executor_url="http://127.0.0.1:9515", chrome_binary=None):
    website = "https://www.amazon.com/"
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--lang=en-US,en")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("detach", True)
    if chrome_binary:
        options.binary_location = chrome_binary

    try:
        driver = webdriver.Remote(command_executor=executor_url, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.get(website)
        print("Successfully opened Amazon")
        wait_for_page_load(driver, 10)

        page_lower = driver.page_source.lower()
        if "captcha" in page_lower or "sorry" in page_lower:
            print("⚠ Amazon bot check encountered; you may need to solve captcha or adjust IP/headers.")

        try:
            for button_xpath in [
                '//button[@alt="Continue shopping"]',
                '//button[contains(text(), "Continue")]',
                '//input[@aria-labelledby="GLUXZipUpdateButton"]'
            ]:
                try:
                    driver.find_element(By.XPATH, button_xpath).click()
                    print("Dismissed popup")
                    time.sleep(2)
                    break
                except:
                    continue
        except:
            print("No popup found")

        try:
            search_box = None
            for xp in ['//*[@id="twotabsearchtextbox"]','//input[@name="field-keywords"]','#twotabsearchtextbox']:
                try:
                    search_box = driver.find_element(By.CSS_SELECTOR, xp) if xp.startswith('#') else driver.find_element(By.XPATH, xp)
                    break
                except:
                    continue
            if not search_box:
                raise Exception("Could not find search box")

            search_box.clear()
            search_box.send_keys(search_term)
            print(f"Entered '{search_term}' in search box")
            time.sleep(2)

            search_button = None
            for xp in ['//*[@id="nav-search-submit-button"]','//input[@type="submit"][@value="Go"]','#nav-search-submit-button']:
                try:
                    search_button = driver.find_element(By.CSS_SELECTOR, xp) if xp.startswith('#') else driver.find_element(By.XPATH, xp)
                    break
                except:
                    continue
            if search_button:
                search_button.click()
            else:
                search_box.send_keys(Keys.RETURN)

            print("Search initiated")
            wait_for_page_load(driver, 10)
            return scrape_products(driver, max_products=max_products)

        except Exception as e:
            print(f"Error during search or scraping: {e}")
            return pd.DataFrame()

    except Exception as e:
        print(f"Error initializing Remote Chrome or accessing Amazon: {e}")
        return pd.DataFrame()
    finally:
        print("Script finished - browser remains open for inspection")

# -------------------- saving wrapper --------------------
def save_results(df: pd.DataFrame, query: str, out_dir: Path, out_csv: str | None) -> Path:
    """
    Save directly into ./Products (or the provided out_dir) with a flat file name:
    <sanitized_query>_<YYYYmmdd_HHMMSS>.csv, unless out_csv is given explicitly.
    """
    # Resolve relative out_dir against current working directory
    base_dir = (Path.cwd() / out_dir) if not out_dir.is_absolute() else out_dir
    ensure_dir(base_dir)

    fname = out_csv if out_csv else f"{sanitize_name(query)}_{timestamp()}.csv"
    csv_path = base_dir / fname
    df.to_csv(csv_path, index=False)
    print(f"\nSaved results to: {csv_path}")
    return csv_path

# -------------------- CLI --------------------
def parse_args():
    p = argparse.ArgumentParser(description="Amazon scraper (Remote WebDriver on chromedriver --port=9515).")
    p.add_argument("--query", type=str, required=True, help="Product name to search (e.g., 'wireless headphones')")
    p.add_argument("--max_products", type=int, default=5, help="Max products to scrape")
    p.add_argument("--executor_url", type=str, default="http://127.0.0.1:9515", help="Remote WebDriver executor URL")
    p.add_argument("--chrome_binary", type=str, default=None, help="Path to Chrome binary (optional)")
    p.add_argument("--out_dir", type=str, default="Products", help="Output directory (default: ./Products)")
    p.add_argument("--out_csv", type=str, default=None, help="Optional CSV filename (e.g., 'results.csv')")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    print("Starting Amazon scraper (Remote WebDriver, port 9515)...")
    df = amazon_detailed_scraper(
        args.query,
        max_products=args.max_products,
        executor_url=args.executor_url,
        chrome_binary=args.chrome_binary
    )
    if not df.empty:
        save_results(df, args.query, Path(args.out_dir), args.out_csv)
    else:
        print("\nNo data scraped. Check logs (captcha/region popup/element changes).")