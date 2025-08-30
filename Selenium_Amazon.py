# Selenium_Amazon.py
# Run Chromedriver first (example):
#   chromedriver --port=9515 --allowed-origins="*" --allowed-ips=""
#
# Then run:
#   python Selenium_Amazon.py --query "portable monitor with bluetooth" --max_products=10 \
#     --max_review_pages=5 --max_reviews=300 --max_foreign_pages=3 --max_foreign_reviews=200
#
# Results saved to: ./Products/<sanitized_query>_<YYYYmmdd_HHMMSS>.csv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

import time
import re
import argparse
from pathlib import Path
from datetime import datetime
import sys
import pyperclip
import pandas as pd

# -------------------- utilities --------------------
def sanitize_name(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9._ -]+", "", s)
    s = re.sub(r"\s+", "_", s)
    return s[:80] if s else "query"

def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_asin_from_url(url: str) -> str | None:
    if not url: return None
    for pat in [r"/dp/([A-Z0-9]{8,16})", r"/product-reviews/([A-Z0-9]{8,16})", r"/global-reviews/([A-Z0-9]{8,16})"]:
        m = re.search(pat, url)
        if m: return m.group(1)
    return None

def wait_for_page_load(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(2)
    except:
        time.sleep(5)

def scroll_to_element(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", element)
        time.sleep(1)
    except:
        pass

def try_click(driver, by, selector, timeout=6):
    try:
        el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, selector)))
        scroll_to_element(driver, el)
        try: el.click()
        except: driver.execute_script("arguments[0].click();", el)
        return True
    except:
        return False

def top_k_review_texts(reviews, k=5):
    """Return exactly k review texts (strings), trimming and padding with ''. Handles dict or str."""
    out = []
    for rv in (reviews or []):
        if isinstance(rv, dict):
            t = (rv.get("review_text") or "").strip()
        else:
            t = (rv or "").strip()
        if t:
            out.append(t)
        if len(out) >= k:
            break
    while len(out) < k:
        out.append("")
    return out[:k]

# -------------------- warranty & support --------------------
def scrape_warranty_support(driver) -> dict:
    heading_text, body_text = "", ""

    x_heading = '//*[@id="productSpecifications_dp_warranty_and_support"]/div/h1'
    x_span3  = '//*[@id="productSpecifications_dp_warranty_and_support"]/div/div[1]/span[3]'

    fallback_headings = [
        x_heading,
        '//div[@id="productSpecifications_dp_warranty_and_support"]//h1',
        '//*[@id="productSupportAndWarranty"]//h1',
        '//h1[contains(., "Warranty") or contains(., "Support")]',
        '//h2[contains(., "Warranty") or contains(., "Support")]'
    ]
    fallback_bodies = [
        x_span3,
        '//*[@id="productSpecifications_dp_warranty_and_support"]//div[contains(@class,"a-section")]',
        '//*[@id="productSupportAndWarranty"]//div[contains(@class,"a-section")]',
        '//*[contains(text(), "Warranty")]/ancestor::div[1]',
    ]

    for expander in [
        '//*[@id="productSpecifications_dp_warranty_and_support"]//a[contains(@class,"a-expander-header")]',
        '//*[@id="productSupportAndWarranty"]//a[contains(@class,"a-expander-header")]',
    ]:
        if try_click(driver, By.XPATH, expander, timeout=2):
            time.sleep(1)

    for xp in fallback_headings:
        try:
            el = driver.find_element(By.XPATH, xp)
            heading_text = (el.text or el.get_attribute("textContent") or "").strip()
            if heading_text: break
        except:
            continue

    for xp in fallback_bodies:
        try:
            el = driver.find_element(By.XPATH, xp)
            body_text = (el.text or el.get_attribute("textContent") or "").strip()
            if body_text and len(body_text) > 5: break
        except:
            continue

    heading_text = re.sub(r"\s+", " ", heading_text or "").strip()
    body_text = re.sub(r"\s+", " ", body_text or "").strip()
    return {"warranty_heading": heading_text or "Not found", "warranty_text": body_text or "Not found"}

# -------------------- product link helper (Share → Copy link; else fallback) --------------------
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
            '//span[contains(text(), "Share")]/parent::a',
            '//*[@id="share"]',
            '//button[contains(@aria-label, "Share")]',
            '//a[contains(@href, "share")]'
        ]
        for i, selector in enumerate(share_button_selectors):
            if try_click(driver, By.XPATH, selector, timeout=6):
                print(f"    ✓ Clicked share button with selector {i+1}")
                time.sleep(2)
                break

        copy_link_selectors = [
            '//span[contains(text(), "Copy link")]',
            '//button[contains(text(), "Copy link")]',
            '//a[contains(text(), "Copy link")]'
        ]
        for i, selector in enumerate(copy_link_selectors):
            if try_click(driver, By.XPATH, selector, timeout=5):
                print(f"    ✓ Clicked copy link button with selector {i+1}")
                time.sleep(2)
                break

        for _ in range(6):
            time.sleep(1.2)
            try: copied_link = pyperclip.paste().strip()
            except: copied_link = ""
            if copied_link and re.search(r"(amazon\.|a\.co|amzn\.to)", copied_link, re.I):
                return copied_link

        cur = driver.current_url
        if 'amazon.' in cur and '/dp/' in cur:
            return cur
        return "Link extraction failed"
    except Exception as e:
        print(f"    ✗ General error getting product link: {e}")
        return driver.current_url

# -------------------- reviews: open reviews page --------------------
def open_reviews_page_from_product(driver, product_url: str) -> str | None:
    """
    Ensure we end up on the canonical /product-reviews/<ASIN> page.
    If clicking '#acrCustomerReviewText' doesn't redirect there, build the URL.
    """
    try:
        driver.get(product_url)
        wait_for_page_load(driver, 10)

        for by, sel in [(By.ID, "acrCustomerReviewText"),
                        (By.XPATH, '//*[@id="acrCustomerReviewText"]'),
                        (By.CSS_SELECTOR, '#acrCustomerReviewText')]:
            if try_click(driver, by, sel, timeout=4):
                break

        time.sleep(1.5)
        cur = driver.current_url
        if "/product-reviews/" in cur:
            return cur

        asin = get_asin_from_url(product_url) or get_asin_from_url(cur)
        if asin:
            return f"https://www.amazon.com/product-reviews/{asin}/?reviewerType=all_reviews"
    except Exception as e:
        print(f"    ✗ Could not open reviews page: {e}")
    return None

# -------------------- reviews: domestic (/product-reviews) --------------------
def scrape_full_reviews_from_reviews_page(driver, reviews_page_url: str, max_pages=5, max_reviews=300) -> list[dict]:
    results = []
    if not reviews_page_url:
        return results

    print(f"  → Navigating to reviews page: {reviews_page_url}")
    driver.get(reviews_page_url)
    wait_for_page_load(driver, 10)

    for page in range(1, max_pages + 1):
        print(f"    • On reviews page {page}")
        time.sleep(1.2)

        blocks = []
        for selector in [
            '//div[@data-hook="review"]',
            '//div[contains(@class,"a-section review aok-relative")]'
        ]:
            try:
                blocks = driver.find_elements(By.XPATH, selector)
                if blocks: break
            except:
                continue

        print(f"      Found {len(blocks)} review blocks")
        for b in blocks:
            try:
                title = ""
                text = ""
                rating = ""
                date = ""

                for xp in ['.//a[@data-hook="review-title"]//span', './/span[@data-hook="review-title"]']:
                    try:
                        title = b.find_element(By.XPATH, xp).text.strip()
                        if title: break
                    except: continue

                for xp in ['.//span[@data-hook="review-body"]//span', './/span[@data-hook="review-body"]']:
                    try:
                        text = b.find_element(By.XPATH, xp).text.strip()
                        if text: break
                    except: continue

                for xp in ['.//i[@data-hook="review-star-rating"]//span', './/i[contains(@class,"a-icon-star")]//span']:
                    try:
                        rating = b.find_element(By.XPATH, xp).text.strip()
                        if rating: break
                    except: continue

                for xp in ['.//span[@data-hook="review-date"]', './/span[contains(@class,"review-date")]']:
                    try:
                        date = b.find_element(By.XPATH, xp).text.strip()
                        if date: break
                    except: continue

                if text:
                    results.append({
                        "review_title": title,
                        "review_text": text,
                        "review_rating": rating,
                        "review_date": date,
                        "origin_country": ""  # domestic
                    })
                    if len(results) >= max_reviews:
                        print("      Reached max_reviews limit")
                        return results
            except:
                continue

        # Next page
        next_clicked = False
        for xp in ['//ul[@class="a-pagination"]//li[@class="a-last"]/a',
                   '//li[contains(@class,"a-last")]/a']:
            if try_click(driver, By.XPATH, xp, timeout=4):
                next_clicked = True
                wait_for_page_load(driver, 10)
                break
        if not next_clicked:
            break

    return results

# -------------------- reviews: inline domestic on PRODUCT page (your XPaths) --------------------
def scrape_inline_domestic_blocks(driver, limit=200) -> list[dict]:
    results = []
    try:
        try:
            hdr = driver.find_element(By.XPATH, '//*[@id="cm-cr-local-reviews-title"]/h3')
            scroll_to_element(driver, hdr)
            time.sleep(0.7)
        except:
            pass

        blocks = driver.find_elements(By.XPATH, '//div[starts-with(@id,"customer_review-") and not(starts-with(@id,"customer_review_foreign-"))]')
        print(f"      Inline domestic blocks found: {len(blocks)}")

        for b in blocks[:limit]:
            try:
                title = ""
                for xp in ['./div[2]/h5/a/span[2]',
                           './div[1]/a/div[2]/span',
                           './/a[@data-hook="review-title"]//span',
                           './/span[@data-hook="review-title"]']:
                    try:
                        title = b.find_element(By.XPATH, xp).text.strip()
                        if title: break
                    except: continue

                text = ""
                for xp in ['./div[4]/span/div/div[1]/span',
                           './/span[@data-hook="review-body"]//span',
                           './/span[@data-hook="review-body"]']:
                    try:
                        text = b.find_element(By.XPATH, xp).text.strip()
                        if text: break
                    except: continue

                rating = ""
                for xp in ['.//i[@data-hook="review-star-rating"]//span',
                           './/span[contains(@class,"a-icon-alt")]']:
                    try:
                        rating = b.find_element(By.XPATH, xp).text.strip()
                        if rating: break
                    except: continue

                date = ""
                for xp in ['.//span[@data-hook="review-date"]',
                           './/span[contains(@class,"review-date")]']:
                    try:
                        date = b.find_element(By.XPATH, xp).text.strip()
                        if date: break
                    except: continue

                if text:
                    results.append({
                        "review_title": title,
                        "review_text": text,
                        "review_rating": rating,
                        "review_date": date,
                        "origin_country": ""  # domestic
                    })
            except:
                continue
    except Exception as e:
        print(f"      ✗ Inline domestic scrape error: {e}")
    return results

# -------------------- reviews: foreign --------------------
def parse_country_from_date(date_text: str) -> str:
    if not date_text: return ""
    m = re.search(r"Reviewed in\s+(the\s+)?(.+?)\s+on\s+", date_text, re.I)
    return m.group(2).strip() if m else ""

def go_to_global_reviews_if_possible(driver) -> bool:
    # Scroll to header if present
    try:
        header = driver.find_element(By.XPATH, '//*[@id="reviews-medley-global-expand-head"]/h3')
        scroll_to_element(driver, header); time.sleep(0.8)
    except:
        pass

    # Try link near header
    link_candidates = [
        '//h3[@id="reviews-medley-global-expand-head"]/following::a[contains(@href,"global-reviews")][1]',
        '//a[contains(@href,"/global-reviews/")]',
        '//a[contains(., "other countries")]',
        '//a[contains(., "다른 국가") or contains(., "다른 나라")]',
    ]
    for xp in link_candidates:
        try:
            el = driver.find_element(By.XPATH, xp)
            href = el.get_attribute("href") or ""
            if href:
                driver.get(href)
                wait_for_page_load(driver, 10)
                return True
        except:
            continue
    return False

def scrape_inline_foreign_blocks(driver, limit=200) -> list[dict]:
    results = []
    blocks = driver.find_elements(By.XPATH, '//div[starts-with(@id,"customer_review_foreign-")]')
    print(f"      Inline foreign blocks found: {len(blocks)}")
    for b in blocks[:limit]:
        try:
            title = ""
            for xp in ['.//a[@data-hook="review-title"]//span', './/span[@data-hook="review-title"]']:
                try:
                    title = b.find_element(By.XPATH, xp).text.strip()
                    if title: break
                except: continue

            text = ""
            for xp in ['.//span[@data-hook="review-body"]//span',
                       './/div[4]//span']:
                try:
                    text = b.find_element(By.XPATH, xp).text.strip()
                    if text: break
                except: continue

            rating = ""
            for xp in ['.//i[@data-hook="review-star-rating"]//span',
                       './/span[contains(@class,"a-icon-alt")]']:
                try:
                    rating = b.find_element(By.XPATH, xp).text.strip()
                    if rating: break
                except: continue

            date = ""
            for xp in ['.//span[@data-hook="review-date"]',
                       './/span[contains(@class,"review-date")]']:
                try:
                    date = b.find_element(By.XPATH, xp).text.strip()
                    if date: break
                except: continue

            if text:
                results.append({
                    "review_title": title,
                    "review_text": text,
                    "review_rating": rating,
                    "review_date": date,
                    "origin_country": parse_country_from_date(date)
                })
        except:
            continue
    return results

def scrape_foreign_reviews_from_reviews_page(driver, max_pages=3, max_reviews=200) -> list[dict]:
    collected: list[dict] = []
    cur = driver.current_url
    at_global = "/global-reviews/" in cur or go_to_global_reviews_if_possible(driver)

    if at_global:
        print("    ✓ On global-reviews listing; scraping foreign reviews (paged)")
        for page in range(1, max_pages + 1):
            time.sleep(1)
            blocks = []
            for selector in ['//div[@data-hook="review"]',
                             '//div[contains(@class,"a-section review aok-relative")]']:
                try:
                    blocks = driver.find_elements(By.XPATH, selector)
                    if blocks: break
                except: continue

            print(f"      Global page {page}: {len(blocks)} reviews")
            for b in blocks:
                try:
                    title = ""
                    for xp in ['.//a[@data-hook="review-title"]//span', './/span[@data-hook="review-title"]']:
                        try:
                            title = b.find_element(By.XPATH, xp).text.strip()
                            if title: break
                        except: continue

                    text = ""
                    for xp in ['.//span[@data-hook="review-body"]//span', './/span[@data-hook="review-body"]']:
                        try:
                            text = b.find_element(By.XPATH, xp).text.strip()
                            if text: break
                        except: continue

                    rating = ""
                    for xp in ['.//i[@data-hook="review-star-rating"]//span', './/i[contains(@class,"a-icon-star")]//span']:
                        try:
                            rating = b.find_element(By.XPATH, xp).text.strip()
                            if rating: break
                        except: continue

                    date = ""
                    for xp in ['.//span[@data-hook="review-date"]', './/span[contains(@class,"review-date")]']:
                        try:
                            date = b.find_element(By.XPATH, xp).text.strip()
                            if date: break
                        except: continue

                    if text:
                        collected.append({
                            "review_title": title,
                            "review_text": text,
                            "review_rating": rating,
                            "review_date": date,
                            "origin_country": parse_country_from_date(date)
                        })
                        if len(collected) >= max_reviews:
                            print("      Reached max foreign reviews limit")
                            return collected
                except:
                    continue

            next_clicked = False
            for xp in ['//ul[@class="a-pagination"]//li[@class="a-last"]/a',
                       '//li[contains(@class,"a-last")]/a']:
                if try_click(driver, By.XPATH, xp, timeout=4):
                    next_clicked = True
                    wait_for_page_load(driver, 10)
                    break
            if not next_clicked:
                break

        return collected

    # Not on global list → try inline
    print("    • Scraping inline foreign blocks on the current page")
    return scrape_inline_foreign_blocks(driver, limit=max_reviews)

# -------------------- search tile parsing --------------------
def get_product_info_from_element(driver, product, index):
    try:
        scroll_to_element(driver, product); time.sleep(0.5)
        asin = product.get_attribute('data-asin')

        title = ""
        for selector in [
            'h2 a span','h2 span','.a-size-mini .a-color-base','.s-size-mini',
            'h2 .a-link-normal span','[data-cy="title-recipe-title"]','.a-size-base-plus',
            'a span.a-text-normal','.a-size-base','.a-color-base','span.a-text-normal',
            '.s-color-base','.s-size-mini.s-spacing-none.s-color-base','h2.a-size-mini span',
            '.a-link-normal .a-text-normal','.//h2//span[string-length(text()) > 10]',
            './/a[contains(@href, "/dp/")]//span[string-length(text()) > 10]'
        ]:
            try:
                el = product.find_element(By.XPATH, selector) if selector.startswith('.//') else product.find_element(By.CSS_SELECTOR, selector)
                t = el.text.strip()
                if t and len(t) > 10 and not t.lower().startswith('sponsored'):
                    title = t; break
            except: continue

        url = ""
        for selector in [
            'h2 a','.a-link-normal[href*="/dp/"]','a[href*="/dp/"]','.s-link-style a',
            'a.a-text-normal','a[href*="/gp/"]','.a-link-normal',
            f'a[href*="{asin}"]' if asin else None,'.//a[contains(@href, "/dp/")]','.//h2//a'
        ]:
            if not selector: continue
            try:
                el = product.find_element(By.XPATH, selector) if selector.startswith('.//') else product.find_element(By.CSS_SELECTOR, selector)
                href = el.get_attribute('href')
                if href and ('/dp/' in href or '/gp/' in href):
                    url = href if href.startswith('http') else "https://www.amazon.com" + href
                    break
            except: continue

        price = ""
        for selector in [
            '.a-price .a-offscreen','.a-price-whole',
            './/span[contains(@class, "a-price")]//span[@class="a-offscreen"]',
            './/span[contains(text(), "$")]'
        ]:
            try:
                el = product.find_element(By.XPATH, selector) if selector.startswith('.//') else product.find_element(By.CSS_SELECTOR, selector)
                t = (el.text or el.get_attribute('textContent') or "").strip()
                if t and '$' in t:
                    price = t; break
            except: continue

        return {'title': title, 'url': url, 'price': price or "Price not available", 'asin': asin or "Not found"}
    except Exception as e:
        print(f"  ✗ Error extracting info for product {index}: {str(e)}")
        return None

# -------------------- product details orchestrator --------------------
def scrape_product_details(driver, product_url, product_number,
                           max_review_pages=5, max_reviews=300,
                           max_foreign_pages=3, max_foreign_reviews=200):
    try:
        print(f"  → Visiting product {product_number} page...")
        driver.get(product_url)
        wait_for_page_load(driver, 10)
        product_link = get_product_link(driver, product_number)

        # Overall rating / number of ratings
        overall_rating, num_ratings = "", ""
        for selector in ['//*[@id="acrPopover"]/span[1]/a/span','//*[contains(@class,"a-icon-alt")]','//*[@data-hook="rating-out-of-text"]']:
            try:
                el = driver.find_element(By.XPATH, selector)
                text = (el.text or el.get_attribute('textContent') or "").strip()
                if text and ('out of' in text.lower() or 'star' in text.lower()):
                    overall_rating = text; break
            except: continue

        for selector in ['//*[@id="acrCustomerReviewText"]','//*[@data-hook="total-review-count"]','//*[contains(text(),"rating") or contains(text(),"review")]']:
            try:
                el = driver.find_element(By.XPATH, selector)
                t = (el.text or "").strip()
                if t and ('rating' in t.lower() or 'review' in t.lower()):
                    num_ratings = t; break
            except: continue

        warranty = scrape_warranty_support(driver)

        # Reviews: domestic
        reviews_page_url = open_reviews_page_from_product(driver, product_url)
        domestic_reviews = scrape_full_reviews_from_reviews_page(
            driver, reviews_page_url or "", max_pages=max_review_pages, max_reviews=max_reviews
        )

        # Fallback inline domestic if needed
        if not domestic_reviews:
            print("    • Domestic reviews not found on reviews page; trying inline domestic blocks")
            driver.get(product_url); wait_for_page_load(driver, 8)
            domestic_reviews = scrape_inline_domestic_blocks(driver, limit=max_reviews)

        # Reviews: foreign
        foreign_reviews = []
        if reviews_page_url:
            foreign_reviews = scrape_foreign_reviews_from_reviews_page(
                driver, max_pages=max_foreign_pages, max_reviews=max_foreign_reviews
            )
        if not foreign_reviews:
            print("    • Foreign reviews not found via global page; trying inline extraction")
            driver.get(product_url); wait_for_page_load(driver, 6)
            foreign_reviews = scrape_inline_foreign_blocks(driver, limit=max_foreign_reviews)

        print(f"    ✓ Collected: domestic={len(domestic_reviews)}, foreign={len(foreign_reviews)}")

        return {
            'overall_rating': overall_rating or "Not found",
            'num_ratings': num_ratings or "Not found",
            'reviews_full': domestic_reviews,
            'reviews_foreign': foreign_reviews,
            'product_link': product_link,
            'warranty_heading': warranty["warranty_heading"],
            'warranty_text': warranty["warranty_text"]
        }

    except Exception as e:
        print(f"    ✗ Error scraping details for product {product_number}: {str(e)}")
        return {
            'overall_rating': "Error loading",
            'num_ratings': "Error loading",
            'reviews_full': [],
            'reviews_foreign': [],
            'product_link': "Error loading",
            'warranty_heading': "Error loading",
            'warranty_text': "Error loading"
        }

# -------------------- main: scrape products --------------------
def scrape_products(
    driver,
    max_products: int = 30,
    max_review_pages: int = 5,
    max_reviews: int = 300,
    max_foreign_pages: int = 3,
    max_foreign_reviews: int = 200,
):
    products_data = []
    print(f"Starting to scrape up to {max_products} products...")

    search_results_url = driver.current_url
    wait_for_page_load(driver, 10)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
    time.sleep(1.2)

    # Find product tiles
    product_infos = []
    products = []
    for selector in [
        '[data-component-type="s-search-result"]',
        '.s-result-item[data-component-type="s-search-result"]',
        '[data-asin]:not([data-asin=""])',
        '.s-result-item',
        '//div[@data-component-type="s-search-result"]',
        '//div[contains(@class, "s-result-item") and @data-asin]',
    ]:
        try:
            if selector.startswith('//'):
                products = driver.find_elements(By.XPATH, selector)
            else:
                products = driver.find_elements(By.CSS_SELECTOR, selector)
            if products:
                print(f"Found {len(products)} products using selector: {selector}")
                break
        except:
            continue

    if not products:
        print("No products found with any selector")
        return pd.DataFrame()

    # Parse basic info from tiles
    for i, product in enumerate(products[: max_products * 2], 1):
        try:
            asin = product.get_attribute("data-asin")
            if asin and asin.strip():
                info = get_product_info_from_element(driver, product, i)
                if info and info.get("title") and info.get("url"):
                    product_infos.append(info)
                    if len(product_infos) >= max_products:
                        break
        except:
            continue

    print(f"\nCollected basic info for {len(product_infos)} products")

    # Visit each product
    for i, product_info in enumerate(product_infos, 1):
        try:
            print(f"\nScraping product {i}/{len(product_infos)}: {product_info['title'][:60]}...")
            details = scrape_product_details(
                driver,
                product_info["url"],
                i,
                max_review_pages=max_review_pages,
                max_reviews=max_reviews,
                max_foreign_pages=max_foreign_pages,
                max_foreign_reviews=max_foreign_reviews,
            )

            # Exactly 5 domestic + 5 foreign review texts; never NaN
            domestic_top5 = top_k_review_texts(details.get("reviews_full", []), k=5)
            foreign_top5  = top_k_review_texts(details.get("reviews_foreign", []), k=5)

            review_cols  = {f"Review_{k+1}": domestic_top5[k] for k in range(5)}
            foreign_cols = {f"Foreign_Review_{k+1}": foreign_top5[k] for k in range(5)}

            all_reviews_concat = " ||| ".join([t for t in top_k_review_texts(details.get("reviews_full", []), k=999) if t])
            all_foreign_concat = " ||| ".join([t for t in top_k_review_texts(details.get("reviews_foreign", []), k=999) if t])

            product_data = {
                "Product_Number": i,
                "Title": product_info["title"],
                "Price": product_info["price"],
                "URL": product_info["url"],
                "ASIN": product_info["asin"],
                "Overall_Rating": details.get("overall_rating", "Not found"),
                "Number_of_Ratings": details.get("num_ratings", "Not found"),
                "Product_Link": details.get("product_link", ""),
                "Warranty_Heading": details.get("warranty_heading", "Not found"),
                "Warranty_Text": details.get("warranty_text", "Not found"),
                "All_Reviews_Concat": all_reviews_concat,
                "All_Foreign_Reviews_Concat": all_foreign_concat,
                "Foreign_Reviews_Count": len(details.get("reviews_foreign", []) or []),
                **review_cols,
                **foreign_cols,
            }
            products_data.append(product_data)
            print(f"  ✓ Product {i} done")

            # Back to results
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
    df = pd.DataFrame(products_data).fillna("")  # ensure no NaN in review columns
    return df

# -------------------- orchestrator --------------------
def amazon_detailed_scraper(search_term, max_products=5, executor_url="http://127.0.0.1:9515",
                            chrome_binary=None, max_review_pages=5, max_reviews=300,
                            max_foreign_pages=3, max_foreign_reviews=200):
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

        # Dismiss common popups
        for xp in [
            '//button[@alt="Continue shopping"]',
            '//button[contains(text(), "Continue")]',
            '//input[@aria-labelledby="GLUXZipUpdateButton"]'
        ]:
            if try_click(driver, By.XPATH, xp, timeout=2):
                print("Dismissed popup"); break

        # Search
        search_box = None
        for xp in ['//*[@id="twotabsearchtextbox"]','//input[@name="field-keywords"]','#twotabsearchtextbox']:
            try:
                search_box = driver.find_element(By.CSS_SELECTOR, xp) if xp.startswith('#') else driver.find_element(By.XPATH, xp)
                break
            except: continue
        if not search_box:
            print("Could not find search box")
            return pd.DataFrame()

        search_box.clear()
        search_box.send_keys(search_term)
        print(f"Entered '{search_term}' in search box")
        time.sleep(1)

        search_button = None
        for xp in ['//*[@id="nav-search-submit-button"]','//input[@type="submit"][@value="Go"]','#nav-search-submit-button']:
            try:
                search_button = driver.find_element(By.CSS_SELECTOR, xp) if xp.startswith('#') else driver.find_element(By.XPATH, xp)
                break
            except: continue
        if search_button: search_button.click()
        else: search_box.send_keys(Keys.RETURN)

        print("Search initiated")
        wait_for_page_load(driver, 10)

        return scrape_products(driver,
                               max_products=max_products,
                               max_review_pages=max_review_pages,
                               max_reviews=max_reviews,
                               max_foreign_pages=max_foreign_pages,
                               max_foreign_reviews=max_foreign_reviews)

    except Exception as e:
        print(f"Error initializing Remote Chrome or accessing Amazon: {e}")
        return pd.DataFrame()
    finally:
        print("Script finished - browser remains open for inspection")

# -------------------- save wrapper & CLI --------------------
def save_results(df: pd.DataFrame, query: str, out_dir: Path, out_csv: str | None) -> Path:
    base_dir = (Path.cwd() / out_dir) if not Path(out_dir).is_absolute() else Path(out_dir)
    ensure_dir(base_dir)
    fname = out_csv if out_csv else f"{sanitize_name(query)}_{timestamp()}.csv"
    csv_path = base_dir / fname
    df.to_csv(csv_path, index=False)
    print(f"\nSaved results to: {csv_path}")
    return csv_path

def parse_args():
    p = argparse.ArgumentParser(description="Amazon scraper (Remote WebDriver on chromedriver --port=9515).")
    p.add_argument("--query", type=str, required=True)
    p.add_argument("--max_products", type=int, default=5)
    p.add_argument("--executor_url", type=str, default="http://127.0.0.1:9515")
    p.add_argument("--chrome_binary", type=str, default=None)
    p.add_argument("--out_dir", type=str, default="Products")
    p.add_argument("--out_csv", type=str, default=None)
    p.add_argument("--max_review_pages", type=int, default=5, help="Max domestic review pages")
    p.add_argument("--max_reviews", type=int, default=300, help="Max domestic reviews")
    p.add_argument("--max_foreign_pages", type=int, default=3, help="Max foreign/global review pages")
    p.add_argument("--max_foreign_reviews", type=int, default=200, help="Max foreign reviews")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    print("Starting Amazon scraper (Remote WebDriver, port 9515)...")
    df = amazon_detailed_scraper(
        args.query,
        max_products=args.max_products,
        executor_url=args.executor_url,
        chrome_binary=args.chrome_binary,
        max_review_pages=args.max_review_pages,
        max_reviews=args.max_reviews,
        max_foreign_pages=args.max_foreign_pages,
        max_foreign_reviews=args.max_foreign_reviews
    )
    if not df.empty:
        save_results(df, args.query, Path(args.out_dir), args.out_csv)
    else:
        print("\nNo data scraped. Check logs (captcha/region popup/element changes).")
