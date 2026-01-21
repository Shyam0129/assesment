# QUICK START GUIDE

## Step-by-Step Setup (Windows)

### 1️⃣ Install Python Dependencies

```powershell
# Make sure you're in the project directory
cd c:\Users\shyam\assesment

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2️⃣ Configure LinkedIn Credentials

```powershell
# Copy the example env file
copy .env.example .env

# Edit .env file with your credentials
notepad .env
```

Add your LinkedIn credentials:
```
LINKEDIN_EMAIL=your_actual_email@example.com
LINKEDIN_PASSWORD=your_actual_password
```

### 3️⃣ Test the Scraper

```powershell
# Test with a public LinkedIn profile (e.g., Bill Gates)
python scraper.py --profile williamhgates

# Or with a full URL
python scraper.py --profile https://www.linkedin.com/in/williamhgates/
```

## 🎯 Usage Examples

### Example 1: Basic Scrape
```powershell
python scraper.py --profile satyanadella
```

### Example 2: With Full URL
```powershell
python scraper.py --profile "https://www.linkedin.com/in/satyanadella/"
```

### Example 3: Headless Mode (may trigger bot detection)
```powershell
python scraper.py --profile jeffweiner08 --headless
```

## 📊 Expected Output

### Console Output:
```
2026-01-21 22:18:37 - INFO - Setting up Chrome WebDriver...
2026-01-21 22:18:40 - INFO - WebDriver setup complete
2026-01-21 22:18:40 - INFO - Logging into LinkedIn...
2026-01-21 22:18:45 - INFO - Login successful!
============================================================
Starting profile scrape...
============================================================
2026-01-21 22:18:48 - INFO - Navigating to profile: https://www.linkedin.com/in/williamhgates/
2026-01-21 22:18:52 - INFO - Scrolling to load dynamic content...
2026-01-21 22:19:05 - INFO - Scrolling complete
2026-01-21 22:19:06 - INFO - Extracting name...
2026-01-21 22:19:06 - INFO - Name found: Bill Gates
2026-01-21 22:19:06 - INFO - Extracting About section...
2026-01-21 22:19:07 - INFO - About section found
2026-01-21 22:19:07 - INFO - Checking 'Open to Work' status...
2026-01-21 22:19:08 - INFO - Open to work: False
2026-01-21 22:19:08 - INFO - Extracting experience data...
2026-01-21 22:19:15 - INFO - Total companies: 3
2026-01-21 22:19:15 - INFO - Previous company: Microsoft
============================================================
Scraping completed successfully!
============================================================

============================================================
SCRAPING RESULTS
============================================================
{
  "profile_url": "https://www.linkedin.com/in/williamhgates/",
  "name": "Bill Gates",
  "about": "Co-chair of the Bill & Melinda Gates Foundation. Founder of Breakthrough Energy...",
  "open_to_work": false,
  "previous_company": "Microsoft",
  "total_companies_worked": 3,
  "companies_list": [
    "Bill & Melinda Gates Foundation",
    "Breakthrough Energy",
    "Microsoft"
  ]
}
============================================================
2026-01-21 22:19:15 - INFO - Results saved to output.json
2026-01-21 22:19:15 - INFO - Closing browser...
```

## 🐛 Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'selenium'`
**Solution:**
```powershell
pip install -r requirements.txt
```

### Issue: `ChromeDriver` not found
**Solution:** 
The `webdriver-manager` package automatically downloads it. Ensure you have Chrome installed.

### Issue: Login fails
**Solution:**
1. Check your credentials in `.env`
2. LinkedIn may require email verification
3. Try without `--headless` mode to see what's happening

### Issue: `LINKEDIN_EMAIL` environment variable not found
**Solution:**
1. Make sure `.env` file exists
2. Activate virtual environment
3. Or set environment variables manually:
```powershell
$env:LINKEDIN_EMAIL="your_email@example.com"
$env:LINKEDIN_PASSWORD="your_password"
python scraper.py --profile williamhgates
```

## 🚀 Push to GitHub

```powershell
# Already committed locally, now push to GitHub

# First, create a new repository on GitHub.com
# Then run:

git remote add origin https://github.com/YOUR_USERNAME/linkedin-scraper.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

## ⚡ Quick Test Without Setup

If you just want to test syntax without LinkedIn credentials:

```powershell
# This will show help and validate script loads
python scraper.py --help
```

Expected output:
```
usage: scraper.py [-h] --profile PROFILE [--headless]

LinkedIn Profile Scraper - Extract profile information using Selenium

optional arguments:
  -h, --help         show this help message and exit
  --profile PROFILE  LinkedIn profile ID or full URL (e.g., 'johndoe' or 
                     'https://www.linkedin.com/in/johndoe/')
  --headless         Run browser in headless mode (not recommended for LinkedIn)
```

## 📁 File Check

Verify all files are created:

```powershell
dir
```

You should see:
- `scraper.py` - Main scraper script (✓)
- `utils.py` - Helper functions (✓)
- `requirements.txt` - Dependencies (✓)
- `.env.example` - Template for credentials (✓)
- `.gitignore` - Git ignore rules (✓)
- `README.md` - Full documentation (✓)
- `QUICKSTART.md` - This file (✓)

## 🎓 Learning Resources

Want to understand the code better?

1. **Selenium Basics**: https://selenium-python.readthedocs.io/
2. **WebDriver Wait**: https://selenium-python.readthedocs.io/waits.html
3. **CSS Selectors**: https://www.w3schools.com/cssref/css_selectors.php

## ⚠️ Important Notes

1. **Rate Limiting**: Don't scrape too many profiles in quick succession
2. **Account Safety**: Use a test LinkedIn account if possible
3. **Legal**: This is for educational purposes only
4. **Updates**: LinkedIn changes their HTML frequently, selectors may need updates

## 🎯 Next Steps

After successful setup:

1. ✅ Test with a public profile
2. ✅ Check `output.json` file
3. ✅ Modify selectors if needed (LinkedIn updates frequently)
4. ✅ Add error handling for your specific use case
5. ✅ Consider adding more fields to extract

---

**Need Help?** Check the main README.md for detailed documentation.
