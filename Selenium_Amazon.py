from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import pandas as pd
import re
import pyperclip

def find_element_with_fallback(driver, xpaths):
    """Try multiple XPaths until one works"""
    for i, xpath in enumerate(xpaths):
        try:
            element = driver.find_element(By.XPATH, xpath)
            print(f"Found element with XPath {i+1}: {xpath}")
            return element
        except:
            continue
    raise Exception("None of the XPaths worked")

def wait_for_page_load(driver, timeout=10):
    """Wait for page to be fully loaded"""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)  # Additional wait for dynamic content
    except:
        time.sleep(5)  # Fallback wait

def scroll_to_element(driver, element):
    """Scroll to element to ensure it's visible"""
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(1)
    except:
        pass

def get_product_link(driver, product_number):
    """Extract the special product link by clicking share buttons - FIXED VERSION"""
    try:
        print(f"    → Getting product link for product {product_number}...")
        
        # Clear clipboard first
        pyperclip.copy("")
        time.sleep(1)
        
        # Wait for page to load completely
        wait_for_page_load(driver)
        
        # Step 1: Click on the primary share widget - FIXED selectors
        share_button_selectors = [
            '//*[@id="ssf-primary-widget-desktop"]/div/a',  # Your original selector
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
                
                # Try regular click first, then JavaScript click
                try:
                    share_button.click()
                except:
                    driver.execute_script("arguments[0].click();", share_button)
                
                print(f"    ✓ Clicked share button with selector {i+1}")
                share_clicked = True
                time.sleep(3)  # Wait for share menu to appear
                break
            except Exception as e:
                print(f"    → Share selector {i+1} failed: {str(e)[:50]}...")
                continue
        
        if not share_clicked:
            print(f"    ✗ Could not find any share button")
            return "Share button not found"
        
        # Step 2: Click on the copy link element - FIXED selectors for your specific case
        copy_link_selectors = [
            '//*[@id="ssf-channel-copy link"]/span[2]',  # Your original selector
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
                
                # Scroll to the copy link button
                scroll_to_element(driver, copy_link_button)
                
                try:
                    copy_link_button.click()
                except:
                    driver.execute_script("arguments[0].click();", copy_link_button)
                
                print(f"    ✓ Clicked copy link button with selector {i+1}")
                copy_clicked = True
                time.sleep(3)  # Wait for copy operation
                break
            except Exception as e:
                print(f"    → Copy selector {i+1} failed: {str(e)[:50]}...")
                continue
        
        if not copy_clicked:
            print(f"    ✗ Could not find copy link button")
            # Try to close any open share menu by pressing Escape
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except:
                pass
            return "Copy link button not found"
        
        # Step 3: Get the copied link from clipboard with enhanced validation
        for attempt in range(8):  # More attempts
            try:
                time.sleep(1.5)  # Longer wait between attempts
                copied_link = pyperclip.paste()
                
                print(f"    → Attempt {attempt + 1}: Clipboard content: '{copied_link[:100]}...'")
                
                # Enhanced validation for Amazon links
                if copied_link and copied_link.strip():
                    copied_link = copied_link.strip()
                    
                    # Check for various Amazon link formats
                    amazon_patterns = [
                        r'https://a\.co/',  # Short Amazon links like https://a.co/d/5dkQibC
                        r'amazon\.com',     # Regular Amazon links
                        r'amzn\.to'         # Another Amazon short format
                    ]
                    
                    if any(re.search(pattern, copied_link, re.IGNORECASE) for pattern in amazon_patterns):
                        print(f"    ✓ Successfully copied valid Amazon product link: {copied_link}")
                        # Close share menu by pressing Escape
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
            
            # If not successful, try clicking copy again for next attempts
            if attempt < 7:
                try:
                    # Try to click copy link again
                    for selector in copy_link_selectors[:3]:  # Try top 3 selectors again
                        try:
                            copy_element = driver.find_element(By.XPATH, selector)
                            copy_element.click()
                            print(f"    → Re-clicked copy button for attempt {attempt + 2}")
                            break
                        except:
                            continue
                except:
                    pass
        
        # If all attempts failed, try alternative methods
        print(f"    ⚠ All clipboard attempts failed, trying alternative methods...")
        
        # Alternative 1: Try to find the link in the share menu directly
        try:
            link_elements = driver.find_elements(By.XPATH, '//input[contains(@value, "amazon.com") or contains(@value, "a.co")]')
            for elem in link_elements:
                link_value = elem.get_attribute('value')
                if link_value and ('amazon.com' in link_value or 'a.co' in link_value):
                    print(f"    ✓ Found link in input field: {link_value}")
                    return link_value
        except:
            pass
        
        # Alternative 2: Get current URL as fallback and try to create short link
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
        # Close any open menus
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except:
            pass
        return f"Error getting link: {str(e)}"

def scrape_product_details(driver, product_url, product_number):
    """Scrape detailed information from individual product page"""
    try:
        print(f"  → Visiting product {product_number} page...")
        driver.get(product_url)
        wait_for_page_load(driver, 10)
        
        # Get the special product link first - THIS IS THE KEY FIX
        product_link = get_product_link(driver, product_number)
        
        # Get overall rating with improved selectors
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
                if selector.startswith('//*') or selector.startswith('//'):
                    element = driver.find_element(By.XPATH, selector)
                else:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                
                text = element.text.strip() or element.get_attribute('textContent').strip()
                if text and ('out of' in text.lower() or 'star' in text.lower()):
                    overall_rating = text
                    break
            except:
                continue
        
        # Get number of ratings with improved selectors
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
                if selector.startswith('//*') or selector.startswith('//'):
                    element = driver.find_element(By.XPATH, selector)
                else:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                
                text = element.text.strip()
                if text and ('rating' in text.lower() or 'review' in text.lower()):
                    num_ratings = text
                    break
            except:
                continue
        
        # Get first 10 reviews with improved approach
        reviews = []
        
        # Scroll down to load reviews
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
        
        # Try different selectors for reviews
        review_elements = []
        for selector in review_selectors:
            try:
                if selector.startswith('//'):
                    elements = driver.find_elements(By.XPATH, selector)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                if elements:
                    review_elements = elements
                    print(f"    Found {len(elements)} reviews using selector: {selector}")
                    break
            except:
                continue
        
        # Extract review text
        for i, element in enumerate(review_elements[:15]):  # Check more elements
            try:
                review_text = element.text.strip()
                if review_text and len(review_text) > 20 and len(review_text) < 1000:  # Filter length
                    reviews.append(review_text)
                    if len(reviews) >= 10:
                        break
            except:
                continue
        
        print(f"    ✓ Collected: Rating={overall_rating}, Reviews={num_ratings}, Review texts={len(reviews)}, Product Link={product_link[:50] if len(str(product_link)) > 50 else product_link}")
        
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
    """Extract product info from a single product element"""
    try:
        print(f"  Extracting info for product {index}...")
        
        # Scroll to product to ensure it's loaded
        scroll_to_element(driver, product)
        time.sleep(1)
        
        # Get ASIN for debugging
        asin = product.get_attribute('data-asin')
        print(f"  Debug: Product ASIN: {asin}")
        
        # Get product title with more comprehensive selectors
        title = ""
        title_selectors = [
            'h2 a span',
            'h2 span',
            '.a-size-mini .a-color-base',
            '.s-size-mini',
            'h2 .a-link-normal span',
            '[data-cy="title-recipe-title"]',
            '.a-size-base-plus',
            'a span.a-text-normal',
            '.a-size-base',
            '.a-color-base',
            'span.a-text-normal',
            '.s-color-base',
            '.s-size-mini.s-spacing-none.s-color-base',
            'h2.a-size-mini span',
            '.a-link-normal .a-text-normal',
            './/h2//span[string-length(text()) > 10]',
            './/a[contains(@href, "/dp/")]//span[string-length(text()) > 10]'
        ]
        
        for j, selector in enumerate(title_selectors):
            try:
                if selector.startswith('.//'):
                    title_element = product.find_element(By.XPATH, selector)
                else:
                    title_element = product.find_element(By.CSS_SELECTOR, selector)
                
                title = title_element.text.strip()
                if title and len(title) > 10 and not title.lower().startswith('sponsored'):
                    print(f"  ✓ Found title with selector {j+1}: {title[:50]}...")
                    break
            except:
                continue
        
        # If still no title, try more aggressive approach
        if not title:
            try:
                all_text_elements = product.find_elements(By.XPATH, './/span[string-length(text()) > 15]')
                for elem in all_text_elements:
                    text = elem.text.strip()
                    if text and len(text) > 15 and len(text) < 200:
                        if not any(word in text.lower() for word in ['sponsored', 'price', '$', 'rating', 'stars']):
                            title = text
                            print(f"  ✓ Found title with fallback method: {title[:50]}...")
                            break
            except:
                pass
        
        # Get product URL with improved selectors
        url = ""
        url_selectors = [
            'h2 a',
            '.a-link-normal[href*="/dp/"]',
            'a[href*="/dp/"]',
            '.s-link-style a',
            'a.a-text-normal',
            'a[href*="/gp/"]',
            '.a-link-normal',
            f'a[href*="{asin}"]' if asin else None,
            './/a[contains(@href, "/dp/")]',
            './/h2//a'
        ]
        
        url_selectors = [s for s in url_selectors if s]
        
        for j, selector in enumerate(url_selectors):
            try:
                if selector.startswith('.//'):
                    url_element = product.find_element(By.XPATH, selector)
                else:
                    url_element = product.find_element(By.CSS_SELECTOR, selector)
                
                url = url_element.get_attribute('href')
                if url and ('/dp/' in url or '/gp/' in url):
                    if not url.startswith('http'):
                        url = "https://www.amazon.com" + url
                    print(f"  ✓ Found URL with selector {j+1}: {url[:50]}...")
                    break
            except:
                continue
        
        # Get product price with improved selectors
        price = ""
        price_selectors = [
            '.a-price-whole',
            '.a-price .a-offscreen',
            '.a-price-symbol + .a-price-whole',
            '.a-price-range .a-offscreen',
            '.a-price .a-price-whole',
            '.a-price-fraction',
            './/span[contains(@class, "a-price")]//span[@class="a-offscreen"]',
            './/span[contains(text(), "$")]'
        ]
        
        for selector in price_selectors:
            try:
                if selector.startswith('.//'):
                    price_element = product.find_element(By.XPATH, selector)
                else:
                    price_element = product.find_element(By.CSS_SELECTOR, selector)
                
                price_text = price_element.text.strip() or price_element.get_attribute('textContent').strip()
                if price_text and '$' in price_text:
                    price = price_text
                    break
            except:
                continue
        
        if not price:
            try:
                price_elements = product.find_elements(By.XPATH, './/span[contains(text(), "$") or contains(@class, "price")]')
                for elem in price_elements:
                    text = elem.text.strip()
                    if text and '$' in text and len(text) < 20:
                        price = text
                        break
            except:
                price = "Price not available"
        
        return {
            'title': title,
            'url': url,
            'price': price if price else "Price not available",
            'asin': asin if asin else "Not found"
        }
    
    except Exception as e:
        print(f"  ✗ Error extracting info for product {index}: {str(e)}")
        return None

def scrape_products(driver, max_products=30):
    """Scrape product information from Amazon search results with improved detection"""
    products_data = []
    print(f"Starting to scrape up to {max_products} products...")
    
    # Store the search results URL
    search_results_url = driver.current_url
    print(f"Search results URL: {search_results_url}")
    
    # Wait for products to load
    wait_for_page_load(driver, 10)
    
    # Scroll down to load more products
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
    time.sleep(3)
    
    # First, collect all product information from the search page
    product_infos = []
    
    # Find all product containers
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
    
    # Filter out invalid products and collect info
    for i, product in enumerate(products[:max_products * 2], 1):  # Check more products than needed
        try:
            # Check if product has essential elements
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
    
    # Now visit each product page for detailed information
    for i, product_info in enumerate(product_infos, 1):
        try:
            print(f"\nScraping product {i}/{len(product_infos)}...")
            print(f"  Title: {product_info['title'][:50]}...")
            
            # Get detailed information by visiting the product page
            details = scrape_product_details(driver, product_info['url'], i)
            
            # Create reviews columns (Review_1, Review_2, etc.)
            review_data = {}
            for j, review in enumerate(details['reviews'][:10], 1):
                review_data[f'Review_{j}'] = review
            
            # Fill empty review slots if less than 10 reviews
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
                'Product_Link': details['product_link'],  # This should now be the short a.co link
                **review_data
            }
            
            products_data.append(product_data)
            print(f"  ✓ Product {i} completed successfully")
            
            # Navigate back to search results
            print(f"  → Navigating back to search results...")
            driver.get(search_results_url)
            wait_for_page_load(driver, 5)
            
        except Exception as e:
            print(f"✗ Error scraping product {i}: {str(e)}")
            # Make sure we're back on the search results page
            try:
                if driver.current_url != search_results_url:
                    driver.get(search_results_url)
                    wait_for_page_load(driver, 5)
            except:
                pass
            continue
    
    print(f"\nSuccessfully scraped {len(products_data)} products with detailed information")
    return pd.DataFrame(products_data)

def amazon_detailed_scraper(search_term, max_products=5):
    """
    Enhanced Amazon product scraper with FIXED product link extraction
    """
    
    website = "https://www.amazon.com/"
    
    # Chrome setup for Windows
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option("detach", True)
    
    # Windows Chrome path
    options.binary_location = r"C:\Users\rezan\Arupreza\Web_Scarping\chrome-win64\chrome.exe"
    
    try:
        # Initialize Chrome driver
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.get(website)
        print("Successfully opened Amazon")
        
        wait_for_page_load(driver, 10)
        
        # Handle location/language popup
        try:
            continue_buttons = [
                '//button[@alt="Continue shopping"]',
                '//button[contains(text(), "Continue")]',
                '//input[@aria-labelledby="GLUXZipUpdateButton"]'
            ]
            
            for button_xpath in continue_buttons:
                try:
                    button = driver.find_element(By.XPATH, button_xpath)
                    button.click()
                    print("Dismissed popup")
                    time.sleep(2)
                    break
                except:
                    continue
        except:
            print("No popup found")
        
        # Search for product
        try:
            search_box_xpaths = [
                '//*[@id="twotabsearchtextbox"]',
                '//input[@name="field-keywords"]',
                '#twotabsearchtextbox'
            ]
            
            search_box = None
            for xpath in search_box_xpaths:
                try:
                    if xpath.startswith('#'):
                        search_box = driver.find_element(By.CSS_SELECTOR, xpath)
                    else:
                        search_box = driver.find_element(By.XPATH, xpath)
                    break
                except:
                    continue
            
            if not search_box:
                raise Exception("Could not find search box")
            
            search_box.clear()
            search_box.send_keys(search_term)
            print(f"Entered '{search_term}' in search box")
            
            time.sleep(2)
            
            search_button_xpaths = [
                '//*[@id="nav-search-submit-button"]',
                '//input[@type="submit"][@value="Go"]',
                '#nav-search-submit-button'
            ]
            
            search_button = None
            for xpath in search_button_xpaths:
                try:
                    if xpath.startswith('#'):
                        search_button = driver.find_element(By.CSS_SELECTOR, xpath)
                    else:
                        search_button = driver.find_element(By.XPATH, xpath)
                    break
                except:
                    continue
            
            if search_button:
                search_button.click()
            else:
                # Try pressing Enter on search box
                search_box.send_keys(Keys.RETURN)
            
            print("Search initiated")
            wait_for_page_load(driver, 10)
            
            # Scrape products with improved detection
            products_df = scrape_products(driver, max_products=max_products)
            
            if not products_df.empty:
                print(f"\n{'='*80}")
                print("SCRAPING RESULTS - FIXED PRODUCT LINK VERSION")
                print(f"{'='*80}")
                print(f"Search term: {search_term}")
                print(f"Total products scraped: {len(products_df)}")
                print(f"DataFrame shape: {products_df.shape}")
                print(f"Columns: {list(products_df.columns)}")
                
                # Show summary of first product
                if len(products_df) > 0:
                    first_product = products_df.iloc[0]
                    print(f"\nFirst product details:")
                    print(f"Title: {first_product['Title'][:80]}...")
                    print(f"Price: {first_product['Price']}")
                    print(f"Rating: {first_product['Overall_Rating']}")
                    print(f"Reviews: {first_product['Number_of_Ratings']}")
                    print(f"Product Link: {first_product['Product_Link']}")
                
                return products_df
            else:
                print("No products were scraped successfully")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error during search or scraping: {e}")
            return pd.DataFrame()
        
    except Exception as e:
        print(f"Error initializing Chrome or accessing Amazon: {e}")
        return pd.DataFrame()
    
    finally:
        print("Script finished - browser remains open for inspection")

# # Example usage - HOW TO USE THE FUNCTION
# if __name__ == "__main__":
#     print("Starting fixed Amazon scraper...")
    
#     # Basic usage - scrape 3 products
#     data = amazon_detailed_scraper("wireless headphones", max_products=3)
    
#     if not data.empty:
#         print("\nScraping completed successfully!")
#         print("\nBasic info:")
#         print(data[['Product_Number', 'Title', 'Price', 'Overall_Rating', 'Product_Link']].to_string(index=False))
        
#         # Save to CSV
#         data.to_csv('amazon_products.csv', index=False)
#         print(f"\nData saved to 'amazon_products.csv'")
        
#         # Show detailed info for first product
#         print(f"\nDetailed info for first product:")
#         first_product = data.iloc[0]
#         print(f"Title: {first_product['Title']}")
#         print(f"Price: {first_product['Price']}")
#         print(f"Rating: {first_product['Overall_Rating']}")
#         print(f"Number of Reviews: {first_product['Number_of_Ratings']}")
#         print(f"Product Link (should be a.co format): {first_product['Product_Link']}")
#         print(f"ASIN: {first_product['ASIN']}")
#         print(f"Full URL: {first_product['URL']}")
        
#         # Show first few reviews
#         print(f"\nFirst 3 reviews:")
#         for i in range(1, 4):
#             review = first_product.get(f'Review_{i}', '')
#             if review:
#                 print(f"Review {i}: {review[:100]}...")
#     else:
#         print("Scraping failed - check error messages above")

# Alternative usage examples:

def example_usage_1():
    """Example 1: Search for laptops, get 5 products"""
    print("\n" + "="*50)
    print("EXAMPLE 1: Searching for laptops")
    print("="*50)
    
    results = amazon_detailed_scraper("gaming laptop", max_products=5)
    
    if not results.empty:
        print(f"Found {len(results)} gaming laptops")
        # Show just the titles and product links
        for idx, row in results.iterrows():
            print(f"{row['Product_Number']}. {row['Title'][:60]}...")
            print(f"   Link: {row['Product_Link']}")
            print(f"   Price: {row['Price']}")
            print()

def example_usage_2():
    """Example 2: Search for books, save specific columns"""
    print("\n" + "="*50)
    print("EXAMPLE 2: Searching for books")
    print("="*50)
    
    results = amazon_detailed_scraper("python programming books", max_products=4)
    
    if not results.empty:
        # Select specific columns
        book_info = results[['Title', 'Price', 'Overall_Rating', 'Product_Link']]
        print(book_info.to_string(index=False))
        
        # Save to Excel
        book_info.to_excel('python_books.xlsx', index=False)
        print("Data saved to python_books.xlsx")

def example_usage_3():
    """Example 3: Search and analyze reviews"""
    print("\n" + "="*50)
    print("EXAMPLE 3: Analyzing reviews")
    print("="*50)
    
    results = amazon_detailed_scraper("bluetooth speaker", max_products=2)
    
    if not results.empty:
        for idx, row in results.iterrows():
            print(f"\nProduct {row['Product_Number']}: {row['Title'][:50]}...")
            print(f"Rating: {row['Overall_Rating']}")
            print(f"Product Link: {row['Product_Link']}")
            
            # Count non-empty reviews
            review_count = 0
            for i in range(1, 11):
                review = row.get(f'Review_{i}', '')
                if review and review != "":
                    review_count += 1
            
            print(f"Collected {review_count} review texts")

# Uncomment the examples you want to run:
# example_usage_1()
# example_usage_2() 
# example_usage_3()