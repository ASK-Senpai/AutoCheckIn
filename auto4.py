import json
import os
import sys
import subprocess
from playwright.sync_api import sync_playwright
import requests

# Log file path
log_file_path = "script_output.log"

def log_final_result(message):
    """Log the final result to the log file."""
    with open(log_file_path, "w") as log_file:  # Overwrite the log file
        log_file.write(f"{message}\n")
    print(message)  # Also print to the console

def clean_cookies(cookies):
    """Clean cookies by removing or correcting invalid attributes."""
    cleaned_cookies = []
    for cookie in cookies:
        if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
            del cookie['sameSite']
        cleaned_cookies.append(cookie)
    return cleaned_cookies

def load_cookies_from_github_secrets(context):
    """Load cookies from GitHub Secrets into the Playwright context."""
    try:
        # Load cookies from the COOKIES_JSON GitHub secret
        cookies_json = os.getenv("COOKIES_JSON")
        if not cookies_json:
            raise ValueError("GitHub Secrets for cookies not found.")

        cookies = json.loads(cookies_json)
        if not isinstance(cookies, list):
            raise ValueError("Cookies data is not a list.")

        cleaned_cookies = clean_cookies(cookies)
        context.add_cookies(cleaned_cookies)
        print("Cookies loaded successfully from GitHub Secrets.")
    except ValueError as e:
        print(f"Error loading cookies: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error parsing cookies from GitHub Secrets: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error loading cookies: {e}")
        raise

def extract_cookies_for_header(cookies):
    """Extract cookies from the Playwright cookies list to create a Cookie header."""
    return '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])

def make_post_request(cookies_header):
    """Make a POST request to check the reward status."""
    url = "https://sg-hk4e-api.hoyolab.com/event/sol/sign?lang=en-us"
    payload = {"act_id": "e202102251931481"}
    headers = {
        "Cookie": cookies_header,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Origin": "https://act.hoyolab.com",
        "Referer": "https://act.hoyolab.com/"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.RequestException as e:
        print("Error during POST request: ", e)
        return None

def close_modal_if_present(page):
    """Close any modal if present on the page."""
    close_button_selector = "body > div._1NVi6w4R.custom-mihoyo-common-mask > div > div > span"
    try:
        page.wait_for_selector(close_button_selector, timeout=5000)
        page.click(close_button_selector)
        print("Close button clicked.")
        page.wait_for_timeout(2000)  # Wait for 2 seconds after closing the modal
    except Exception as e:
        print(f"No close button found; proceeding. Exception: {e}")

def claim_rewards(page, cookies_header):
    """Attempt to claim rewards and check for success or login popup."""
    claim_button_selector = "body > div > div.components-home-assets-__home_---home-content---1hcp1A > div > div > div > div.components-home-assets-__sign-content-test_---sign-list---3Nz_jn > div.components-home-assets-__sign-content-test_---sign-item---3gtMqV.components-home-assets-__sign-content-test_---sign-wrapper---22GpLY > div.components-home-assets-__sign-content-test_---sign-award---2rJ6SD"
    success_message_selector = "body > div.m-modal.m-dialog.pc-dialog.m-dialog-sign.components-common-common-dialog-__index_---common-dialog---99ed7a.components-common-common-dialog-__index_---sign-dialog---3tldeh > div.m-dialog-wrapper.sign-wrapper > div.m-dialog-body.pc-dialog-body > div > div > div.components-common-common-dialog-__index_---title---xH8wpC"

    claim_reward_js = """
    (selector) => {
        var rewardButton = document.querySelector(selector);
        if (rewardButton) {
            var event = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });
            rewardButton.dispatchEvent(event);
            return "Reward claimed.";
        } else {
            return "Reward button not found.";
        }
    }
    """

    try:
        # Attempt to click the claim button using JavaScript
        print("Attempting to click the claim button...")
        result = page.evaluate(claim_reward_js, claim_button_selector)
        print(result)

        # Wait for success message
        try:
            print("Waiting for success message...")
            page.wait_for_selector(success_message_selector, timeout=10000)  # Wait up to 10 seconds
            log_final_result("Reward claimed successfully.")
        except Exception as e:
            print("Success message not found, checking for network request...")
            # Make POST request to check for login popup or reward status
            response_json = make_post_request(cookies_header)

            if response_json:
                message = response_json.get('message')
                if message == "Traveler, you've already checked in today~":
                    log_final_result(message)
                elif message == 'Not logged in':
                    log_final_result("Cookies might have expired or there is an issue.")
                else:
                    log_final_result("There is an issue. Contact A.S.K._SENPAI.")
            else:
                log_final_result("Unable to get a response from the server.")
    except Exception as e:
        print(f"Error claiming reward with JavaScript: {e}")
        log_final_result("An unexpected error occurred during reward claiming.")

def main():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context()

        try:
            load_cookies_from_github_secrets(context)
        except Exception as e:
            print(f"Failed to load cookies: {e}")
            browser.close()
            return

        page = context.new_page()
        page.goto("https://act.hoyolab.com/ys/event/signin-sea-v3/index.html?act_id=e202102251931481")

        close_modal_if_present(page)
        cookies_header = extract_cookies_for_header(context.cookies())
        claim_rewards(page, cookies_header)

        browser.close()
        print("Browser closed.")

if __name__ == "__main__":
    main()
