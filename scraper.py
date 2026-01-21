"""
LinkedIn Profile Scraper
A Selenium-based scraper to extract profile information from LinkedIn
"""

import os
import sys
import json
import time
import logging
import argparse
from typing import Dict, Optional, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from utils import scroll_to_load_content, safe_extract_text, setup_logger

# Setup logging
logger = setup_logger()


class LinkedInScraper:
    """LinkedIn Profile Scraper using Selenium"""
    
    def __init__(self, headless: bool = False):
        """
        Initialize the scraper
        
        Args:
            headless: Run browser in headless mode
        """
        self.headless = headless
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Setup Chrome WebDriver with options"""
        logger.info("Setting up Chrome WebDriver...")
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Additional options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Initialize driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)
        
        logger.info("WebDriver setup complete")
        
    def login(self, email: str, password: str):
        """
        Login to LinkedIn
        
        Args:
            email: LinkedIn email
            password: LinkedIn password
        """
        logger.info("Logging into LinkedIn...")
        
        try:
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)
            
            # Enter email
            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_field.send_keys(email)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(password)
            
            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # Wait for redirect to feed
            time.sleep(5)
            
            # Check if login was successful
            if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                logger.info("Login successful!")
            else:
                logger.warning("Login may have failed or requires additional verification")
                # Give extra time for manual intervention if needed
                time.sleep(10)
                
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise
            
    def navigate_to_profile(self, profile_input: str):
        """
        Navigate to LinkedIn profile
        
        Args:
            profile_input: Either profile ID or full URL
        """
        # Determine if input is full URL or just ID
        if profile_input.startswith("http"):
            profile_url = profile_input
        else:
            # Remove leading/trailing slashes if present
            profile_id = profile_input.strip("/")
            profile_url = f"https://www.linkedin.com/in/{profile_id}/"
            
        logger.info(f"Navigating to profile: {profile_url}")
        self.driver.get(profile_url)
        time.sleep(3)
        
        # Scroll to load all sections
        scroll_to_load_content(self.driver, logger)
        
    def extract_name(self) -> str:
        """Extract profile name"""
        logger.info("Extracting name...")
        
        selectors = [
            "h1.text-heading-xlarge",
            "h1.inline.t-24.v-align-middle.break-words",
            "div.ph5 h1",
            "h1"
        ]
        
        for selector in selectors:
            name = safe_extract_text(self.driver, By.CSS_SELECTOR, selector, logger)
            if name and name != "Not available":
                logger.info(f"Name found: {name}")
                return name
                
        logger.warning("Name not found")
        return "Not available"
        
    def extract_about(self) -> str:
        """Extract About section text"""
        logger.info("Extracting About section...")
        
        try:
            # Try to find and click "Show more" button first
            try:
                show_more = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    "div#about ~ div button[aria-expanded='false']"
                )
                self.driver.execute_script("arguments[0].click();", show_more)
                time.sleep(1)
            except:
                pass
            
            selectors = [
                "div#about ~ div span[aria-hidden='true']",
                "section.artdeco-card div.display-flex.ph5.pv3 div.inline-show-more-text span[aria-hidden='true']",
                "div.pv-about-section div.pv-about__summary-text",
                "section.summary div.pv-about__summary-text"
            ]
            
            for selector in selectors:
                about = safe_extract_text(self.driver, By.CSS_SELECTOR, selector, logger)
                if about and about != "Not available":
                    logger.info("About section found")
                    return about
                    
        except Exception as e:
            logger.warning(f"Error extracting about section: {str(e)}")
            
        logger.warning("About section not found")
        return "Not available"
        
    def check_open_to_work(self) -> bool:
        """Check if profile has 'Open to Work' badge"""
        logger.info("Checking 'Open to Work' status...")
        
        try:
            selectors = [
                "img[alt*='Open to work']",
                "div.pv-top-card-profile-picture__container img[alt*='Open to work']",
                "span:contains('Open to work')",
                "div.artdeco-entity-lockup__badge-text"
            ]
            
            for selector in selectors:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info("Open to work: True")
                    return True
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error checking open to work status: {str(e)}")
            
        logger.info("Open to work: False")
        return False
        
    def extract_experience(self) -> Dict[str, any]:
        """
        Extract experience data including companies and previous company
        
        Returns:
            Dictionary with 'companies', 'total_companies', and 'previous_company'
        """
        logger.info("Extracting experience data...")
        
        companies = []
        previous_company = "Not available"
        
        try:
            # Try to find and click "Show all experiences" button
            try:
                show_all = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "div#experience ~ div button[aria-label*='Show all']"
                )
                self.driver.execute_script("arguments[0].click();", show_all)
                time.sleep(2)
            except:
                pass
            
            # Find experience section
            experience_selectors = [
                "section#experience-section ul.pv-profile-section__section-info li",
                "div#experience ~ div ul li.artdeco-list__item",
                "section.experience-section ul li"
            ]
            
            experience_items = []
            for selector in experience_selectors:
                try:
                    experience_items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if experience_items:
                        break
                except:
                    continue
            
            if not experience_items:
                logger.warning("No experience items found")
                return {
                    "companies": [],
                    "total_companies": 0,
                    "previous_company": "Not available"
                }
            
            current_date_found = False
            
            for item in experience_items:
                try:
                    # Extract company name
                    company_selectors = [
                        "span.t-14.t-normal span[aria-hidden='true']",
                        "span.pv-entity__secondary-title",
                        "p.pv-entity__secondary-title",
                        "span[aria-hidden='true']"
                    ]
                    
                    company_name = None
                    for comp_sel in company_selectors:
                        try:
                            company_elem = item.find_element(By.CSS_SELECTOR, comp_sel)
                            company_name = company_elem.text.strip()
                            if company_name and not company_name.startswith("·"):
                                break
                        except:
                            continue
                    
                    if not company_name:
                        continue
                    
                    # Extract date range to determine if current or past
                    date_selectors = [
                        "span.t-14.t-normal.t-black--light span[aria-hidden='true']",
                        "span.pv-entity__date-range span:nth-child(2)",
                        "p.pv-entity__date-range span:nth-child(2)"
                    ]
                    
                    date_range = None
                    for date_sel in date_selectors:
                        try:
                            date_elem = item.find_element(By.CSS_SELECTOR, date_sel)
                            date_range = date_elem.text.strip().lower()
                            if date_range:
                                break
                        except:
                            continue
                    
                    # Add to companies list
                    if company_name not in companies:
                        companies.append(company_name)
                    
                    # Determine if this is a current or past role
                    is_current = date_range and ("present" in date_range or "current" in date_range)
                    
                    # If we haven't found a current role yet and this is past, it's previous
                    if not current_date_found and not is_current and previous_company == "Not available":
                        previous_company = company_name
                    
                    if is_current:
                        current_date_found = True
                        # Reset previous company if we found current role
                        if previous_company != "Not available":
                            # Re-scan for actual previous (second in list after current)
                            pass
                        
                except Exception as e:
                    logger.debug(f"Error processing experience item: {str(e)}")
                    continue
            
            # If we have companies but no previous company identified, use first non-current
            if companies and previous_company == "Not available":
                # If there's more than one company, second one is likely previous
                if len(companies) > 1:
                    previous_company = companies[1]
                elif len(companies) == 1:
                    previous_company = companies[0]
            
            logger.info(f"Total companies: {len(companies)}")
            logger.info(f"Previous company: {previous_company}")
            
        except Exception as e:
            logger.error(f"Error extracting experience: {str(e)}")
        
        return {
            "companies": companies,
            "total_companies": len(companies),
            "previous_company": previous_company
        }
        
    def scrape_profile(self, profile_input: str) -> Dict:
        """
        Main scraping function
        
        Args:
            profile_input: Profile ID or full URL
            
        Returns:
            Dictionary with extracted data
        """
        logger.info("=" * 60)
        logger.info("Starting profile scrape...")
        logger.info("=" * 60)
        
        try:
            # Navigate to profile
            self.navigate_to_profile(profile_input)
            
            # Extract all data
            name = self.extract_name()
            about = self.extract_about()
            open_to_work = self.check_open_to_work()
            experience_data = self.extract_experience()
            
            # Compile results
            results = {
                "profile_url": self.driver.current_url,
                "name": name,
                "about": about,
                "open_to_work": open_to_work,
                "previous_company": experience_data["previous_company"],
                "total_companies_worked": experience_data["total_companies"],
                "companies_list": experience_data["companies"]
            }
            
            logger.info("=" * 60)
            logger.info("Scraping completed successfully!")
            logger.info("=" * 60)
            
            return results
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            raise
            
    def close(self):
        """Close the browser"""
        if self.driver:
            logger.info("Closing browser...")
            self.driver.quit()


def main():
    """Main execution function"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="LinkedIn Profile Scraper - Extract profile information using Selenium"
    )
    parser.add_argument(
        "--profile",
        required=True,
        help="LinkedIn profile ID or full URL (e.g., 'johndoe' or 'https://www.linkedin.com/in/johndoe/')"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (not recommended for LinkedIn)"
    )
    
    args = parser.parse_args()
    
    # Get credentials from environment variables
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")
    
    if not email or not password:
        logger.error("LinkedIn credentials not found in environment variables!")
        logger.error("Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD")
        sys.exit(1)
    
    scraper = None
    
    try:
        # Initialize scraper
        scraper = LinkedInScraper(headless=args.headless)
        scraper.setup_driver()
        
        # Login
        scraper.login(email, password)
        
        # Scrape profile
        results = scraper.scrape_profile(args.profile)
        
        # Output results
        print("\n" + "=" * 60)
        print("SCRAPING RESULTS")
        print("=" * 60)
        print(json.dumps(results, indent=2))
        print("=" * 60)
        
        # Save to file
        output_file = "output.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {output_file}")
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
        
    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    main()
