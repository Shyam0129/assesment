"""
LinkedIn Profile Scraper – FINAL STABLE VERSION
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, List
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from utils import scroll_to_load_content, setup_logger

logger = setup_logger()


class LinkedInScraper:

    def __init__(self, headless=False, attach=False):
        self.headless = headless
        self.attach = attach
        self.driver = None
        self.wait = None

    # ---------------------------------------------------------
    # DRIVER SETUP
    # ---------------------------------------------------------
    def setup_driver(self):
        chrome_options = Options()

        if self.attach:
            chrome_options.add_experimental_option(
                "debuggerAddress", "127.0.0.1:9222"
            )
        else:
            if self.headless:
                chrome_options.add_argument("--headless=new")

            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

        if not self.attach:
            self.driver.maximize_window()

    # ---------------------------------------------------------
    # LOGIN
    # ---------------------------------------------------------
    def login(self, email, password):
        if self.attach:
            logger.info("Attached mode – skipping login")
            return

        self.driver.get("https://www.linkedin.com/login")
        time.sleep(2)

        self.wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(email)
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(5)

    # ---------------------------------------------------------
    # BASIC PROFILE DATA
    # ---------------------------------------------------------
    def navigate_to_profile(self, profile):
        self.driver.get(profile)
        time.sleep(3)
        scroll_to_load_content(self.driver, logger)

    def extract_name(self):
        try:
            return self.driver.find_element(By.TAG_NAME, "h1").text.strip()
        except Exception:
            return "Not available"

    def extract_about(self):
        try:
            sec = self.driver.find_element(
                By.XPATH, "//section[.//span[normalize-space()='About']]"
            )
            return sec.text.replace("About", "").strip()
        except Exception:
            return "Not available"

    def check_open_to_work(self):
        return bool(self.driver.find_elements(By.XPATH, "//*[contains(text(),'Open to work')]"))

    # ---------------------------------------------------------
    # EXPERIENCE (DETAILS PAGE – FINAL SOURCE OF TRUTH)
    # ---------------------------------------------------------
    def extract_experience_details(self) -> Dict[str, List[str]]:
        logger.info("Opening full Experience details page")

        base = self.driver.current_url.rstrip("/")
        self.driver.get(f"{base}/details/experience/")
        time.sleep(3)

        companies = []
        current_companies = []

        items = self.driver.find_elements(
            By.XPATH, "//li[contains(@class,'artdeco-list__item')]"
        )

        for item in items:
            try:
                spans = item.find_elements(By.XPATH, ".//span[@aria-hidden='true']")
                texts = [s.text.strip() for s in spans if s.text.strip()]

                if len(texts) < 2:
                    continue

                t0 = texts[0]
                t1 = texts[1]

                # Check if t1 is a duration (indicating a multi-role company header)
                # e.g. t0="CRED", t1="5 yrs 1 mo"
                # vs Single Role: t0="SDE", t1="Google · Full-time"
                is_duration = any(x in t1 for x in [" yr", " mo"]) and any(c.isdigit() for c in t1)

                if is_duration:
                    company = t0
                    designation = "Multiple Roles"
                else:
                    designation = t0
                    company = t1.split("·")[0].strip()
                
                # Basic validation to skip roles/types being captured as companies
                if len(company) < 2 or any(x in company.lower() for x in ["full-time", "part-time", "self-employed"]):
                    continue

                if company not in companies:
                    companies.append(company)

                if "Present" in item.text:
                    current_companies.append(company)

                logger.info(f"Experience: {designation} @ {company}")

            except Exception:
                continue

        previous_company = (
            " | ".join(dict.fromkeys(current_companies))
            if current_companies
            else companies[0] if companies else "Not available"
        )

        return {
            "companies": companies,
            "total_companies": len(companies),
            "previous_company": previous_company
        }

    # ---------------------------------------------------------
    # MAIN SCRAPER
    # ---------------------------------------------------------
    def scrape_profile(self, profile):
        self.navigate_to_profile(profile)

        results = {
            "profile_url": self.driver.current_url,
            "name": self.extract_name(),
            "about": self.extract_about(),
            "open_to_work": self.check_open_to_work()
        }

        exp_data = self.extract_experience_details()
        results.update({
            "previous_company": exp_data["previous_company"],
            "total_companies_worked": exp_data["total_companies"],
            "companies_list": exp_data["companies"]
        })

        return results

    def close(self):
        if self.driver and not self.attach:
            self.driver.quit()


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------
def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--attach", action="store_true")
    args = parser.parse_args()

    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")

    scraper = LinkedInScraper(headless=args.headless, attach=args.attach)

    try:
        scraper.setup_driver()
        scraper.login(email, password)
        data = scraper.scrape_profile(args.profile)

        print(json.dumps(data, indent=2, ensure_ascii=False))

        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("Results saved to output.json")

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
