"""
LinkedIn Profile Scraper
A Selenium-based scraper to extract profile information from LinkedIn
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, List, Any
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from utils import scroll_to_load_content, setup_logger

# Setup logging
logger = setup_logger()


class LinkedInScraper:
    """LinkedIn Profile Scraper using Selenium"""

    def __init__(self, headless: bool = False, attach: bool = False):
        self.headless = headless
        self.attach = attach
        self.driver = None
        self.wait = None

    def setup_driver(self):
        """Setup Chrome WebDriver with options"""
        logger.info("Setting up Chrome WebDriver...")

        chrome_options = Options()
        
        if self.attach:
            logger.info("Attaching to existing Chrome instance on 127.0.0.1:9222")
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        else:
            if self.headless:
                chrome_options.add_argument("--headless=new")

            # Stability / Anti-bot tweaks
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)

            chrome_options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

        self.driver = webdriver.Chrome(options=chrome_options)
        
        if not self.attach:
            self.driver.maximize_window()
            
        self.wait = WebDriverWait(self.driver, 15)
        logger.info("WebDriver setup complete")

    def login(self, email: str, password: str):
        """Login to LinkedIn"""
        if self.attach:
            logger.info("Skipping login (attached mode).")
            return

        logger.info("Logging into LinkedIn...")

        try:
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)

            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_field.send_keys(email)

            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(password)

            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()

            time.sleep(5)

            if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                logger.info("Login successful!")
            else:
                logger.warning("Login may have failed or needs verification (captcha/2FA).")
                time.sleep(10)

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise

    def navigate_to_profile(self, profile_input: str):
        """Navigate to LinkedIn profile"""
        if profile_input.startswith("http"):
            profile_url = profile_input
        else:
            profile_id = profile_input.strip("/")
            profile_url = f"https://www.linkedin.com/in/{profile_id}/"

        logger.info(f"Navigating to profile: {profile_url}")
        self.driver.get(profile_url)
        time.sleep(3)

        scroll_to_load_content(self.driver, logger)

    def extract_name(self) -> str:
        """Extract profile name"""
        logger.info("Extracting name...")

        try:
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
            time.sleep(2)
        except Exception:
            pass

        name_selectors = [
            "h1.text-heading-xlarge",
            "section div h1",
            "h1",
        ]

        for selector in name_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if text and len(text) > 2 and not text.startswith("·"):
                        logger.info(f"Name found: {text}")
                        return text
            except Exception:
                continue

        try:
            page_title = self.driver.title
            if " | LinkedIn" in page_title:
                title_name = page_title.split(" | LinkedIn")[0].strip()
                logger.info(f"Name from page title: {title_name}")
                return title_name
        except Exception:
            pass

        logger.warning("Name not found")
        return "Not available"

    def extract_about(self) -> str:
        """Extract About section text"""
        logger.info("Extracting About section...")
        try:
            time.sleep(1)
            about_text = "Not available"

            targets = [
                "//section[@id='about']",
                "//div[@id='about']/ancestor::section",
                "//section[.//h2[normalize-space()='About']]",
                "//section[.//span[normalize-space()='About']]",
            ]

            target_section = None
            for xpath in targets:
                try:
                    secs = self.driver.find_elements(By.XPATH, xpath)
                    if secs:
                        target_section = secs[0]
                        break
                except Exception:
                    continue

            if target_section:
                # expand show more if exists
                try:
                    btn = target_section.find_element(By.CSS_SELECTOR, "button.inline-show-more-text__button")
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.5)
                except Exception:
                    pass

                # best attempt - aria hidden content
                try:
                    t = target_section.find_element(
                        By.XPATH,
                        ".//span[@aria-hidden='true']"
                    ).text
                    if t and len(t) > 20:
                        about_text = t
                except Exception:
                    about_text = target_section.text.replace("About", "").replace("Show more", "").strip()

            if about_text != "Not available":
                lines = [
                    l.strip() for l in about_text.split("\n")
                    if l.strip() and l.lower() not in ["show less", "show more"]
                ]
                about_text = " ".join(lines).strip()

            return about_text if about_text else "Not available"

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
            ]

            for xpath in xpaths:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        logger.info(f"Open to work found via XPath: {xpath}")
                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.error(f"Error checking Open to Work: {str(e)}")
            return False

    def extract_experience(self) -> Dict[str, Any]:
        """
        Extract experience data:
        - companies: list of all unique companies
        - previous_company: latest/current company or companies
        """
        logger.info("Extracting experience data...")

        companies: List[str] = []
        current_companies: List[str] = []
        previous_company_field = "Not available"

        try:
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(2)

            # Debug: Save page source
            try:
                with open("debug_page_source.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                logger.info("Saved debug_page_source.html")
            except Exception as e:
                logger.warning(f"Failed to save debug source: {e}")

            try:
                # Use innerText via JS which is often more reliable/complete than Selenium .text
                body_text = self.driver.execute_script("return document.body.innerText;")
            except Exception:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text

            start_markers = ["Experience\n", "Work Experience\n"]
            start_idx = -1
            for marker in start_markers:
                idx = body_text.find(marker)
                if idx != -1:
                    start_idx = idx
                    logger.info(f"Found Experience start at {start_idx}")
                    break

            lines: List[str] = []
            if start_idx != -1:
                end_markers = ["Education\n", "Projects\n", "Skills\n", "Licenses", "Volunteering"]
                end_idx = min(len(body_text), start_idx + 5000)

                search_text = body_text[start_idx + 10:]
                candidates = []
                for m in end_markers:
                    i = search_text.find(m)
                    if i != -1:
                        candidates.append(i)

                if candidates:
                    end_idx = min(candidates) + start_idx + 10
                else:
                    end_idx = min(len(body_text), start_idx + 3000)

                section_text = body_text[start_idx:end_idx]
                lines = [l.strip() for l in section_text.split("\n") if l.strip()]
            else:
                logger.warning("Experience header not found in text.")

            # ------------ FIXED company extraction logic -------------
            def looks_like_company(text: str) -> bool:
                if not text or len(text.strip()) < 2:
                    return False

                text_l = text.lower().strip()

                bad_contains = [
                    # Type/Duration
                    "full-time", "part-time", "internship", "contract", "present", "self-employed", "freelance",
                    "yr", "yrs", "mos", "month", "months", "year",
                    # Location
                    "india", "united states", "usa", "kingdom", "china", "germany", "france", "canada", "australia",
                    "bengaluru", "bangalore", "hyderabad", "mumbai", "delhi", "pune", "chennai", "gurgaon", "noida",
                    "karnataka", "telangana", "maharashtra", "tamil nadu", "uttar pradesh",
                    "texas", "california", "new york", "london", "san francisco", "area", "greater", "city",
                    # Sections
                    "experience", "education", "skills", "projects", "licenses", "certifications", "volunteering",
                    # Dates (Months)
                    "jan ", "feb ", "mar ", "apr ", "may ", "jun ", "jul ", "aug ", "sep ", "oct ", "nov ", "dec ",
                    # ROLES / TITLES (To exclude)
                    "engineer", "developer", "consultant", "analyst", "manager", "director", "president", "vp", "ceo", "cto",
                    "founder", "co-founder", "owner", "lead", "head", "chief", "principal", "senior", "junior",
                    "associate", "graduate", "trainee", "intern", "apprentice", "architect", "admin", "executive", "officer",
                    "specialist", "scientist", "researcher", "professor", "lecturer", "teacher", "trainer", "advisor",
                    "investor", "board member", "chair", "supervisor", "coordinator", "strategist", "technologist",
                    "writer", "editor", "designer", "creator", "artist", "producer", "recruiter", "hr", "representative", "agent",
                    "backend", "frontend", "full stack", "fullstack", "devops", "sre", "data", "quality", "security", "builder",
                    "freelancer", "contractor", "member", "fellow"
                ]

                # Strict check: any bad keyword invalidates the string
                if any(b in text_l for b in bad_contains):
                    return False

                # Multiple commas usually implies location "City, State, Country"
                if text.count(",") >= 2:
                    return False

                # Mostly digits
                if sum(c.isdigit() for c in text) >= 2:
                    return False

                # Too short
                if len(text.strip()) <= 2:
                    return False

                return True

            buffer: List[str] = []

            for line in lines:
                buffer.append(line)
                if len(buffer) > 10:
                    buffer.pop(0)

                # 1) "Company · Type" logic
                if "·" in line or "•" in line:
                    sep = "·" if "·" in line else "•"
                    cand = line.split(sep)[0].strip()
                    if looks_like_company(cand):
                        if cand not in companies:
                            companies.append(cand)
                            logger.info(f"Added company (bullet match): {cand}")

                # 2) Duration Logic: If line looks like "5 yrs 1 mo", the PREVIOUS line might be the company
                # Often: Company \n Duration \n Role...
                is_duration = any(u in line.lower() for u in [" yr", " yrs", " mo", " mos", " year"]) and any(c.isdigit() for c in line)
                if is_duration and len(buffer) >= 2:
                    # buffer[-1] is current 'line' (the duration). buffer[-2] is candidate.
                    cand = buffer[-2]
                    if looks_like_company(cand):
                        if cand not in companies:
                            companies.append(cand)
                            logger.info(f"Added company (duration match): {cand}")

                # 3) "Present" logic for Current Company
                if "present" in line.lower():
                    # Look backwards for the first valid company
                    for prev in reversed(buffer[:-1]): # skip current 'Present' line
                        # Check "Company · Type" pattern in history
                        if "·" in prev or "•" in prev:
                            sep = "·" if "·" in prev else "•"
                            cand = prev.split(sep)[0].strip()
                            if looks_like_company(cand):
                                if cand not in current_companies:
                                    current_companies.append(cand)
                                    logger.info(f"Marked as current: {cand}")
                                break
                        
                        # Check standalone line
                        if looks_like_company(prev):
                             if prev not in current_companies:
                                 current_companies.append(prev)
                                 logger.info(f"Marked as current: {prev}")
                             break

            # ------------- fallback headline parsing -------------
            if not companies:
                logger.info("Checking Headline for company info...")
                try:
                    headline_candidates = [l for l in body_text.split("\n")[:25] if "@" in l or " @ " in l]
                    for head in headline_candidates:
                        if " @ " in head:
                            parts = head.split(" @ ")
                            if len(parts) > 1:
                                company = parts[1].split("|")[0].split("-")[0].split(",")[0].strip()
                                if looks_like_company(company):
                                    companies.append(company)
                                    current_companies.append(company)
                                    logger.info(f"Extracted company from Headline: {company}")
                                    break
                except Exception as e:
                    logger.debug(f"Headline fallback failed: {e}")

            # Latest/current company(s)
            if current_companies:
                previous_company_field = ", ".join(current_companies)
            elif companies:
                previous_company_field = companies[0]
            else:
                previous_company_field = "Not available"

            logger.info(f"Total companies: {len(companies)}")
            logger.info(f"Latest/Current company(s): {previous_company_field}")

        except Exception as e:
            logger.error(f"Error extracting experience: {str(e)}")

        return {
            "companies": companies,
            "total_companies": len(companies),
            "previous_company": previous_company_field,  # This is CURRENT/LATEST (as you want)
        }

    def scrape_profile(self, profile_input: str) -> Dict[str, Any]:
        """Main scraping function"""
        logger.info("=" * 60)
        logger.info("Starting profile scrape...")
        logger.info("=" * 60)

        try:
            self.navigate_to_profile(profile_input)

            name = self.extract_name()
            about = self.extract_about()
            open_to_work = self.check_open_to_work()
            experience_data = self.extract_experience()

            results = {
                "profile_url": self.driver.current_url,
                "name": name,
                "about": about,
                "open_to_work": open_to_work,
                "previous_company": experience_data["previous_company"],  # current/latest
                "total_companies_worked": experience_data["total_companies"],
                "companies_list": experience_data["companies"],
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
            if self.attach:
                logger.info("Detaching from browser (leaving it open)...")
            else:
                logger.info("Closing browser...")
                self.driver.quit()


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="LinkedIn Profile Scraper")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--attach", action="store_true", help="Attach to existing Chrome on port 9222")

    args = parser.parse_args()

    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")

    if not args.attach and (not email or not password):
        logger.error("LinkedIn credentials not found in environment variables!")
        sys.exit(1)

    scraper = None

    try:
        scraper = LinkedInScraper(headless=args.headless, attach=args.attach)
        scraper.setup_driver()
        scraper.login(email, password)

        results = scraper.scrape_profile(args.profile)

        print("\\n" + "=" * 60)
        print("SCRAPING RESULTS")
        print("=" * 60)
        print(json.dumps(results, indent=2, ensure_ascii=False))
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
