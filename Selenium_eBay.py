# Selenium_eBay.py
#   chromedriver --port=9515 --allowed-origins="*" --allowed-ips=""
#   python Selenium_eBay.py --query "wireless headphones" --max_products 10

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl
from pathlib import Path
from datetime import datetime
import pandas as pd
import argparse, time, re

# -------------------- small utils --------------------
def sanitize_name(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9._ -]+", "", s)
    s = re.sub(r"\s+", "_", s)
    return s[:80] if s else "query"

def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def save_results(df: pd.DataFrame, query: str, out_dir: Path) -> Path:
    ensure_dir(out_dir)
    path = out_dir / f"{sanitize_name(query)}_{timestamp()}.csv"
    df.to_csv(path, index=False)
    print(f"\nSaved results to: {path}")
    return path

# -------------------- language forcing --------------------
def force_english_url(url: str) -> str:
    try:
        u = urlparse(url)
        q = dict(parse_qsl(u.query, keep_blank_values=True))
        q["_lang"] = "en-us"
        return urlunparse((u.scheme, u.netloc, u.path, u.params, urlencode(q, doseq=True), u.fragment))
    except:
        return url

def wait_ready(driver, timeout=12):
    WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")

def is_english(driver) -> bool:
    try:
        lang = (driver.execute_script("return document.documentElement.lang || ''") or "").lower()
        return lang.startswith("en")
    except:
        return False

def cdp_force_english(driver):
    """Set browser-level language via CDP so server sees Accept-Language + locale as en-US."""
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {
            "headers": {"Accept-Language": "en-US,en;q=0.9"}
        })
        driver.execute_cdp_cmd("Emulation.setLocaleOverride", {"locale": "en-US"})
    except Exception as e:
        print("CDP override failed (non-fatal):", e)

def clear_site_prefs(driver, domain="https://www.ebay.com/"):
    """Remove cookies & local/session storage that may pin Korean locale."""
    try:
        driver.get("about:blank")
        driver.delete_all_cookies()
        driver.get(domain)
        wait_ready(driver, 10)
        # Clear storage (must run on the domain)
        driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
        time.sleep(0.2)
    except Exception as e:
        print("Clear prefs error (non-fatal):", e)

def dismiss_banners(driver):
    for by, sel in [
        (By.ID, "gdpr-banner-accept"),
        (By.CSS_SELECTOR, 'button[aria-label*="Accept"]'),
        (By.CSS_SELECTOR, 'button[title*="Accept"]'),
    ]:
        try:
            el = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((by, sel)))
            driver.execute_script("arguments[0].click();", el)
            time.sleep(0.2)
            break
        except:
            pass

def open_lang_menu_and_select_english(driver, timeout=10) -> bool:
    """Open header flyout and click the English entry (data-lang='en-US')."""
    wait_ready(driver, timeout)
    # Find flyout button (normalize to BUTTON node)
    btn = None
    for xp in [
        '//*[@id="gh"]/nav/div[2]/div[2]/button',
        '//div[contains(@class,"gh-language-toggle")]//button[contains(@class,"gh-flyout__target")]',
        '//button[contains(@aria-controls,"-dialog") and contains(@class,"gh-flyout__target")]',
    ]:
        try:
            el = driver.find_element(By.XPATH, xp)
            if el.tag_name.lower() != "button":
                el = el.find_element(By.XPATH, "./ancestor::button[1]")
            btn = el; break
        except:
            continue
    if not btn:
        return False

    try:
        ActionChains(driver).move_to_element(btn).pause(0.2).click(btn).perform()
    except:
        pass
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        driver.execute_script("arguments[0].click();", btn)
    except:
        pass

    # Resolve dialog
    dialog_id = btn.get_attribute("aria-controls") or ""
    dialog = None
    if dialog_id:
        try:
            dialog = WebDriverWait(driver, 6).until(EC.visibility_of_element_located((By.ID, dialog_id)))
        except:
            dialog = None
    if dialog is None:
        try:
            dialog = WebDriverWait(driver, 4).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".gh-flyout__dialog")))
        except:
            dialog = None
    if dialog is None:
        return False

    # Click English option (span[data-lang="en-US"] -> clickable ancestor)
    target = None
    try:
        target = dialog.find_element(
            By.XPATH,
            './/span[contains(@class,"gh-language-toggle__menu-text") and @data-lang="en-US"]/ancestor::*[self::a or self::button][1]'
        )
    except:
        try:
            target = dialog.find_element(
                By.XPATH,
                './/span[contains(@class,"gh-language-toggle__menu-text") and normalize-space()="English"]/ancestor::*[self::a or self::button][1]'
            )
        except:
            target = None
    if not target:
        return False

    try:
        driver.execute_script("arguments[0].click();", target)
    except:
        try:
            ActionChains(driver).move_to_element(target).pause(0.1).click(target).perform()
        except:
            return False

    wait_ready(driver, timeout)
    # Final nudge: ensure URL contains _lang=en-us
    driver.get(force_english_url(driver.current_url))
    wait_ready(driver, timeout)
    return is_english(driver)

def nav(driver, url: str, timeout: int = 12, verify_lang: bool = True):
    driver.get(force_english_url(url))
    wait_ready(driver, timeout)
    if verify_lang and not is_english(driver):
        # Reload same URL with _lang again (handles redirects)
        driver.get(force_english_url(driver.current_url))
        wait_ready(driver, timeout)

# -------------------- driver --------------------
def build_driver(executor_url: str, chrome_binary: str | None = None):
    opts = Options()
    # Browser language hints
    opts.add_argument("--lang=en-US")
    opts.add_experimental_option("prefs", {"intl.accept_languages": "en-US,en"})
    # Stability + stealth
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1366,900")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_experimental_option("detach", True)
    if chrome_binary:
        opts.binary_location = chrome_binary

    driver = webdriver.Remote(command_executor=executor_url, options=opts)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    # CDP language overrides
    cdp_force_english(driver)
    return driver

# -------------------- open + search --------------------
def open_english_ebay(driver):
    clear_site_prefs(driver)  # kill cached locale
    nav(driver, "https://www.ebay.com/", timeout=12, verify_lang=True)
    dismiss_banners(driver)
    if not is_english(driver):
        # Use header menu as last resort
        if not open_lang_menu_and_select_english(driver, timeout=12):
            # Hard fallback: reload with param again
            nav(driver, driver.current_url, timeout=10, verify_lang=True)
    print("Lang now:", driver.execute_script("return document.documentElement.lang"))

def search_ebay(driver, query: str):
    # Locate search box
    search_box = None
    for locator in [
        (By.CSS_SELECTOR, "#gh-ac"),
        (By.CSS_SELECTOR, 'input[aria-label="Search for anything"]'),
        (By.XPATH, '//input[@id="gh-ac"]'),
    ]:
        try:
            search_box = WebDriverWait(driver, 8).until(EC.presence_of_element_located(locator))
            break
        except:
            continue
    if not search_box:
        raise RuntimeError("Search box not found")

    search_box.clear()
    search_box.send_keys(query)
    time.sleep(0.2)

    # Click the search button
    search_btn = None
    for locator in [
        (By.CSS_SELECTOR, "#gh-btn"),
        (By.XPATH, '//input[@id="gh-btn"]'),
        (By.XPATH, '//button[@id="gh-btn"]'),
    ]:
        try:
            search_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(locator))
            break
        except:
            continue
    if search_btn:
        try:
            search_btn.click()
        except:
            driver.execute_script("arguments[0].click();", search_btn)
    else:
        search_box.send_keys(Keys.RETURN)

    wait_ready(driver, 12)
    # Re-force English on results (geo can flip again)
    nav(driver, driver.current_url, timeout=10, verify_lang=True)
    print("Search done. Lang:", driver.execute_script("return document.documentElement.lang"))

# -------------------- (optional) basic results scrape --------------------
def scrape_results_basic(driver, max_products=10) -> pd.DataFrame:
    cards = []
    for sel in ["li.s-item[data-view*='mi:']", "li.s-item", "ul.srp-results li.s-item"]:
        try:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards: break
        except: continue

    rows = []
    for card in cards:
        try:
            a = None
            for sel in ['a.s-item__link', 'a.s-item__title', 'a[href*="/itm/"]']:
                try:
                    a = card.find_element(By.CSS_SELECTOR, sel); break
                except: continue
            if not a: continue

            try:
                title_el = card.find_element(By.CSS_SELECTOR, "h3.s-item__title")
            except:
                title_el = a
            title = (title_el.text or title_el.get_attribute("textContent") or "").strip()
            if not title: continue

            href = a.get_attribute("href") or ""
            url = force_english_url(href)
            price = ""
            for ps in ["span.s-item__price", ".x-price .s-item__price", ".s-item__details .s-item__price"]:
                try:
                    price = (card.find_element(By.CSS_SELECTOR, ps).text or "").strip()
                    if price: break
                except: continue

            rows.append({"Title": title, "Price": price, "URL": url})
            if len(rows) >= max_products: break
        except: continue

    print(f"Collected {len(rows)} results")
    return pd.DataFrame(rows)

# -------------------- CLI --------------------
def parse_args():
    p = argparse.ArgumentParser(description="eBay English opener + product search.")
    p.add_argument("--query", required=True, help="Product to search (e.g., 'wireless headphones')")
    p.add_argument("--max_products", type=int, default=10)
    p.add_argument("--executor_url", default="http://127.0.0.1:9515")
    p.add_argument("--chrome_binary", default=None)
    p.add_argument("--out_dir", default="Products")
    return p.parse_args()

# -------------------- main --------------------
if __name__ == "__main__":
    args = parse_args()
    print("Starting (Remote WebDriver on port 9515)…")
    driver = None
    try:
        driver = build_driver(args.executor_url, args.chrome_binary)

        # 1) Open eBay in English (CDP overrides + clear prefs + URL param + menu fallback)
        open_english_ebay(driver)

        # 2) Search using the search button
        search_ebay(driver, args.query)

        # Optional: capture a few rows
        df = scrape_results_basic(driver, max_products=args.max_products)
        if not df.empty:
            save_results(df, args.query, Path(args.out_dir))
        else:
            print("No rows captured (layout/filters may differ).")

    except Exception as e:
        print("ERROR:", e)
    finally:
        print("Done. Browser left open for inspection.")
