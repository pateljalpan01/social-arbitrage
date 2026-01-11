from playwright.sync_api import sync_playwright

def save_login_state():
    with sync_playwright() as p:
        # We launch Chrome in HEADED mode so you can see it
        # We add arguments to minimize bot detection flags just in case
        browser = p.chromium.launch(
            headless=False, 
            channel="chrome", 
            args=["--disable-blink-features=AutomationControlled"] 
        )
        context = browser.new_context()
        page = context.new_page()

        print("--- MANUAL LOGIN REQUIRED ---")
        print("1. I am opening Twitter for you.")
        print("2. Please log in manually (type user/pass yourself).")
        print("3. Solve any CAPTCHAs if they appear.")
        print("4. Wait until you see your Home Feed.")
        
        page.goto("https://twitter.com/i/flow/login")

        # The script pauses here effectively forever until you hit Enter in the terminal
        input("\n>>> ONCE YOU ARE LOGGED IN AND SEE THE FEED, PRESS ENTER HERE <<<")

        # Save the cookies to a file
        context.storage_state(path="state.json")
        print("\nSUCCESS! Credentials saved to 'state.json'.")
        print("You never have to log in again.")
        
        browser.close()

if __name__ == "__main__":
    save_login_state()