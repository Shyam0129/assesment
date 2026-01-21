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
from dotenv import load_dotenv
from typing import Dict, Optional, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
        
        
        # Initialize driver with Selenium's built-in driver manager
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window() # Maximize window to ensure better rendering
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
        
        # Wait for main content to load
        try:
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
            time.sleep(2)
        except:
            pass
        
        # Try LinkedIn's current structure first
        name_selectors = [
            "div.f0a6b000.e60f223a.a92e7eaf h1",  # Current LinkedIn structure
            "h1.text-heading-xlarge",
            "section div h1",
            "h1"
        ]
        
        for selector in name_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if text and len(text) > 2 and not text.startswith("·"):
                        logger.info(f"Name found: {text}")
                        return text
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
        
        # Fallback: Extract from page title
        try:
            page_title = self.driver.title
            if " | LinkedIn" in page_title:
                title_name = page_title.split(" | LinkedIn")[0].strip()
                logger.info(f"Name from page title: {title_name}")
                return title_name
        except:
            pass
        
        logger.warning("Name not found")
        return "Not available"
        
    def extract_about(self) -> str:
        """Extract About section text"""
        logger.info("Extracting About section...")
        try:
            time.sleep(1)
            
            about_text = "Not available"
            
            # Strategy: Find section with "About" header using robust XPath
            try:
                # 1. Try id="about" which is often an anchor
                targets = [
                    "//section[@id='about']",
                    "//div[@id='about']/ancestor::section",
                    "//section[.//h2[normalize-space()='About']]",
                    "//section[.//span[normalize-space()='About']]"
                ]
                
                target_section = None
                for xpath in targets:
                    try:
                        secs = self.driver.find_elements(By.XPATH, xpath)
                        if secs:
                            target_section = secs[0]
                            break
                    except:
                        continue
                
                if target_section:
                    # Look for text content
                    try:
                        btn = target_section.find_element(By.CSS_SELECTOR, "button.inline-show-more-text__button")
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
                    except:
                        pass
                        
                    # Get text from generic container or specific class
                    try:
                        t = target_section.find_element(By.XPATH, ".//div[contains(@class, 'display-flex')]//span[@aria-hidden='true']").text
                        if len(t) > 20: about_text = t
                    except:
                        about_text = target_section.text.replace("About", "").replace("Show more", "").strip()
            
            except Exception as e:
                logger.debug(f"About xpath strategy failed: {e}")

            # Clean up text
            if about_text != "Not available":
                 lines = [l.strip() for l in about_text.split('\n') if l.strip() and l.lower() not in ["show less", "show more"]]
                 if len(lines) == 1 and "|" in lines[0] and len(lines[0]) < 100:
                     logger.warning("Extracted text looks like headline, ignoring.")
                     about_text = "Not available"
                 else:
                     about_text = " ".join(lines)
                     logger.info(f"About section found ({len(about_text)} chars)")
            
            return about_text

        except Exception as e:
            logger.error(f"Error extracting about: {str(e)}")
            return "Not available"

    def check_open_to_work(self) -> bool:
        """Check if profile has 'Open to Work' badge"""
        logger.info("Checking 'Open to Work' status...")
        try:
            xpaths = [
                "//*[contains(text(), 'Open to work') or contains(text(), 'OPEN TO WORK')]",
                "//img[contains(@alt, 'Open to work')]",
                "//section[.//span[contains(text(), 'Open to work')]]",
                "//main//section//div[contains(@class, 'pv-top-card__badge-wrap')]"
            ]
            
            for xpath in xpaths:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        logger.info(f"Open to work found via XPath: {xpath}")
                        return True
                except:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Error checking Open to Work: {str(e)}")
            return False

    def extract_experience(self) -> Dict[str, any]:
        """
        Extract experience data including companies and previous company
        """
        logger.info("Extracting experience data...")
        
        companies = []
        current_companies = []
        previous_company_field = "Not available"
        
        try:
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(2)
            
            # Universal Strategy: Parse Body Text
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            start_markers = ["Experience\n", "Work Experience\n"]
            start_idx = -1
            for marker in start_markers:
                idx = body_text.find(marker)
                if idx != -1:
                    start_idx = idx
                    logger.info(f"Found Experience start at {start_idx}")
                    break
            
            lines = []
            if start_idx != -1:
                end_markers = ["Education\n", "Education", "Projects\n", "Skills\n", "Licenses", "Volunteering"]
                end_idx = start_idx + 5000 
                
                search_text = body_text[start_idx+15:]
                candidates = []
                for m in end_markers:
                    i = search_text.find(m)
                    if i != -1: candidates.append(i)
                
                if candidates:
                    end_idx = min(candidates) + start_idx + 15
                else:
                    end_idx = min(len(body_text), start_idx + 3000)
                
                section_text = body_text[start_idx:end_idx]
                lines = [l.strip() for l in section_text.split('\n') if l.strip()]
            else:
                logger.warning("Experience header not found in text.")

            # Filter Noise
            noise_keywords = [
                "mos", "yr", "present", "full-time", "contract", "internship", "experience",
                "india", "united states", "kingdom", "germany", "canada", "remote", "hybrid", "on-site",
                "jan ", "feb ", "mar ", "apr ", "may ", "jun ", "jul ", "aug ", "sep ", "oct ", "nov ", "dec ",
                "bangalore", "bengaluru", "hyderabad", "delhi", "mumbai", "karnataka", "telangana", "maharashtra"
            ]
            
            last_company = None
            
            for line in lines:
                # Identify Company using Separator
                if "·" in line or "•" in line:
                     sep = "·" if "·" in line else "•"
                     cand = line.split(sep)[0].strip()
                     
                     if len(cand) >= 2:
                         is_noise = False
                         if any(x in cand.lower() for x in noise_keywords): is_noise = True
                         if any(char.isdigit() for char in cand) and len(cand) < 10: is_noise = True
                         
                         if not is_noise:
                             if cand not in companies:
                                 companies.append(cand)
                                 logger.info(f"Added company: {cand}")
                                 last_company = cand
                             else:
                                 last_company = cand # Update context if company appears again

                # Identify if current ("Present")
                if "Present" in line or "present" in line:
                    if last_company and last_company not in current_companies:
                        current_companies.append(last_company)
                        logger.info(f"Marked {last_company} as current")


            # Fallback: Check Headline
            if not companies:
                logger.info("Checking Headline for company info...")
                try:
                    headline_candidates = [l for l in body_text.split('\n')[:20] if "@" in l]
                    for head in headline_candidates:
                        if " @ " in head:
                            parts = head.split(" @ ")
                            if len(parts) > 1:
                                company = parts[1].split("|")[0].split("-")[0].split(",")[0].strip()
                                if len(company) > 2:
                                    companies.append(company)
                                    current_companies.append(company) # Headline implies current
                                    logger.info(f"Extracted company from Headline: {company}")
                                    break
                except Exception as e:
                    logger.debug(f"Headline fallback failed: {e}")

            # Determine previous_company field (which now holds LATEST companies)
            if current_companies:
                # Join with commas if multiple
                previous_company_field = ", ".join(current_companies)
            elif companies:
                # Default to the first one found (usually most recent)
                previous_company_field = companies[0]

            logger.info(f"Total companies: {len(companies)}")
            logger.info(f"Latest/Current company(s): {previous_company_field}")
            
        except Exception as e:
            logger.error(f"Error extracting experience: {str(e)}")
        
        return {
            "companies": companies,
            "total_companies": len(companies),
            "previous_company": previous_company_field # This maps to desired logic
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
                "previous_company": experience_data["previous_company"], # Holds LATEST/CURRENT
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
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="LinkedIn Profile Scraper")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--headless", action="store_true")
    
    args = parser.parse_args()
    
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")
    
    if not email or not password:
        logger.error("LinkedIn credentials not found in environment variables!")
        sys.exit(1)
    
    scraper = None
    
    try:
        scraper = LinkedInScraper(headless=args.headless)
        scraper.setup_driver()
        scraper.login(email, password)
        results = scraper.scrape_profile(args.profile)
        
        print("\n" + "=" * 60)
        print("SCRAPING RESULTS")
        print("=" * 60)
        print(json.dumps(results, indent=2))
        print("=" * 60)
        
        output_file = "output.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {output_file}")
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    main()
