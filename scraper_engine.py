from playwright.sync_api import sync_playwright
import time
import os

class TwitterScraper:
    def __init__(self, headless=False):
        # Check if the ticket exists before starting
        if not os.path.exists("state.json"):
            raise Exception("No state.json found! Run login_setup.py first.")

        self.p = sync_playwright().start()
        
        # We launch Chrome. 
        self.browser = self.p.chromium.launch(
            headless=headless, 
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # INJECT THE COOKIES (The Magic Step)
        self.context = self.browser.new_context(storage_state="state.json")
        self.page = self.context.new_page()
        print("--- Browser Launched (Session Injected) ---")

    def scrape_search(self, query, max_tweets=10):
        print(f"Searching for: {query}")
        self.page.goto(f"https://twitter.com/search?q={query}&src=typed_query&f=live")
        
        try:
            # Wait for tweets to appear
            self.page.wait_for_selector("article[data-testid='tweet']", timeout=20000)
        except:
            print("Error: Tweets didn't load.")
            return []
        
        tweets_data = []
        unique_tweets = set()
        
        while len(tweets_data) < max_tweets:
            self.page.keyboard.press("End")
            time.sleep(2) 
            
            elements = self.page.query_selector_all("article[data-testid='tweet']")
            for tweet in elements:
                try:
                    text_node = tweet.query_selector("div[data-testid='tweetText']")
                    if text_node:
                        text = text_node.inner_text().replace('\n', ' ')
                        if text not in unique_tweets:
                            tweets_data.append(text)
                            unique_tweets.add(text)
                            print(f"Found: {text[:50]}...") 
                except: 
                    continue
                
            if len(tweets_data) >= max_tweets: 
                break
                
        return tweets_data[:max_tweets]

    def close(self):
        self.browser.close()
        self.p.stop()
        print("--- Browser Closed ---")