# 🛒 Selenium eBay Scraper

A robust Python-based **eBay product scraper** using **Selenium WebDriver** with remote Chrome driver support. Efficiently extracts comprehensive product information from eBay search results and product detail pages.

---

## ✨ Features

- **Remote Chrome WebDriver** integration (`chromedriver --port=9515`)
- **Automatic consent popup handling** (GDPR/regional popups)
- **Dual-layer data extraction**:
  - **Search Results Page**: Title, price, condition, shipping, ratings
  - **Product Detail Page**: Item ID, seller info, sold count, return policy
- **CSV export** with timestamped filenames
- **Flexible CLI interface** with customizable parameters
- **Error handling** and graceful failure recovery

---

## 📦 Requirements

- **Python 3.8+**
- **Google Chrome** (latest version recommended)
- **ChromeDriver** (matching Chrome version)

### Install Dependencies

```bash
pip install selenium pandas
```

### ChromeDriver Setup

1. Check your Chrome version:
   ```bash
   google-chrome --version
   ```

2. Download matching ChromeDriver from [chromedriver.chromium.org](https://chromedriver.chromium.org/)

3. Add ChromeDriver to your PATH or note its location

---

## 🚀 Usage

### 1. Start ChromeDriver

Launch ChromeDriver in a separate terminal:

```bash
chromedriver --port=9515 --allowed-origins="*" --allowed-ips=""
```

### 2. Run the Scraper

Execute the scraper with your desired parameters:

```bash
python Selenium_eBay.py --query "wireless headphones" --max_products 3
```

### 3. Access Results

Results are automatically saved to:
```
Products/<sanitized_query>_<YYYYmmdd_HHMMSS>.csv
```

**Example**: `Products/wireless_headphones_20250830_153500.csv`

---

## ⚙️ Configuration

### CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--query` | **(required)** | Search term (e.g., "gaming laptop") |
| `--max_products` | `5` | Maximum products to scrape |
| `--executor_url` | `http://127.0.0.1:9515` | Remote WebDriver endpoint |
| `--chrome_binary` | `None` | Custom Chrome binary path |
| `--out_dir` | `Products` | Output directory |
| `--out_csv` | `None` | Custom CSV filename |

### Example Commands

```bash
# Basic usage
python Selenium_eBay.py --query "smartphone"

# Advanced configuration
python Selenium_eBay.py --query "gaming laptop" --max_products 10 --out_dir "results" --chrome_binary "/usr/bin/google-chrome"

# Custom output file
python Selenium_eBay.py --query "headphones" --out_csv "headphones_analysis.csv"
```

---

## 📊 Output Schema

### CSV Columns

| Column | Description |
|--------|-------------|
| `Product_Number` | Sequential product identifier |
| `Title` | Product name/title |
| `Price` | Product price (formatted) |
| `URL` | Direct product link |
| `Item_ID` | eBay item identifier |
| `Condition` | Product condition (new/used/refurbished) |
| `Shipping (Search)` | Shipping cost from search results |
| `Shipping (PDP)` | Shipping cost from product page |
| `Rating_Text` | Product rating description |
| `Reviews_Count` | Number of reviews |
| `Sold` | Units sold |
| `Seller` | Seller name |
| `Seller_Feedback` | Seller feedback score |
| `Returns` | Return policy information |

---

## 🛠 Troubleshooting

### Common Issues

**ChromeDriver Connection Failed**
- Ensure ChromeDriver is running on port 9515
- Verify Chrome and ChromeDriver version compatibility
- Check firewall settings

**Consent Popups Blocking Scraper**
- Script handles most popups automatically
- For persistent issues, try:
  - Using a US-based VPN
  - Setting Chrome language to `en-US`
  - Clearing browser data

**Search Elements Not Found**
- eBay may have updated their layout
- Update CSS selectors in the code
- Check for regional eBay variations

**Version Compatibility Check**
```bash
# Check versions match
google-chrome --version
chromedriver --version
```

### Performance Optimization

- **Reduce `max_products`** for faster execution
- **Use headless mode** for server environments
- **Implement delays** if encountering rate limits

---

## 🔧 Development

### Code Structure
```
Selenium_eBay.py          # Main scraper script
├── WebDriver setup       # Remote Chrome configuration  
├── Search execution      # Query processing
├── Data extraction       # Product information parsing
├── CSV export           # Results formatting
└── Error handling       # Graceful failure management
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Implement improvements
4. Add tests for new functionality
5. Submit a pull request

---

## 📄 License

This project is for educational and research purposes. Please respect eBay's Terms of Service and robots.txt when using this scraper.

---

## 🆘 Support

For issues and questions:
- Check the troubleshooting section above
- Review eBay's current page structure
- Ensure all dependencies are correctly installed