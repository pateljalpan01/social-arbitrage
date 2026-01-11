import pandas as pd
import time
import csv
import os
import random
from datetime import datetime
from collections import deque 

# --- IMPORT THE BRAIN & SENSORS ---
try:
    from news_scraper import get_finviz_news, calculate_metrics, get_sentiment
    from market_scanner import get_market_movers  
    from scraper_engine import TwitterScraper
    # LINK THE DYNAMIC BRAIN
    from config_manager import ConfigManager      
except ImportError as e:
    print(f"CRITICAL ERROR: Missing module. {e}")
    exit()

# --- CONFIGURATION ---
CHECK_INTERVAL_SECONDS = 120  
DIVERSITY_THRESHOLD = 0.7     
LOG_FILE = "sentiment_signals.csv" 
REFRESH_TICKERS_CYCLES = 15  # Refresh hot list every ~30 mins
BROWSER_RESTART_CYCLES = 20  # <--- MEMORY FIX: Reboot browser every ~40 mins

# --- STATE MEMORY ---
# Maxlen ensures we never store more than 2000 tweets (RAM Protection)
seen_tweets = deque(maxlen=2000)

def log_signal(ticker, signal_type, score, news_score, diversity):
    file_exists = os.path.exists(LOG_FILE)
    try:
        with open(LOG_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Timestamp', 'Ticker', 'Signal', 'Score', 'News_Score', 'Diversity'])
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                ticker, signal_type, score, news_score, diversity
            ])
        print(f"   [Data Logged to {LOG_FILE}]")
    except IOError as e:
        print(f"   [ERROR] Could not write to log file: {e}")

def analyze_twitter_signal(scraper, ticker):
    query = ticker if ticker.startswith('$') else f"${ticker}"
    print(f"   > Scraping Twitter for {query}...")
    
    try:
        raw_tweets = scraper.scrape_search(query, max_tweets=15)
    except Exception as e:
        print(f"   [WARN] Scraper failed for {query}: {e}")
        return 0, 0, "Scraper Error"

    if not raw_tweets:
        return 0, 0, "No Tweets Found"

    new_tweets = []
    spam_keywords = ["discord.gg", "t.me/", "whatsapp", "join my group"]

    for text in raw_tweets:
        if any(spam in text.lower() for spam in spam_keywords):
            continue    

        if text not in seen_tweets:
            new_tweets.append(text)
            seen_tweets.append(text) 
            
    if not new_tweets:
        return 0, 0, "No New Tweets"
    
    total_new = len(new_tweets)
    # Check diversity to spot bots
    unique_texts = len(set(new_tweets))
    diversity_score = unique_texts / total_new if total_new > 0 else 0
    
    scores = [get_sentiment(t, source_type='social') for t in new_tweets]
    avg_sentiment = sum(scores) / len(scores) if scores else 0
    
    return diversity_score, avg_sentiment, f"{total_new} new tweets"

def main():
    print(f"--- STARTING ARBITRAGE ENGINE (V3.1 Memory Optimized) ---")
    
    try:
        print("Launching Headless Browser...")
        scraper = TwitterScraper(headless=True)
    except Exception as e:
        print(f"Error starting scraper: {e}")
        return

    # --- INITIALIZE THE CONFIG MANAGER ---
    cm = ConfigManager()
    print(f"   [Config] Connected to Learning Engine.")

    tickers = ['$TSLA', '$NVDA', '$AMD'] 
    cycle_count = 0

    try:
        while True:
            cycle_start_time = time.time()
            
            # 1. MEMORY CLEANUP: RESTART BROWSER
            # Headless Chrome leaks memory. We kill it and respawn it periodically.
            if cycle_count > 0 and cycle_count % BROWSER_RESTART_CYCLES == 0:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Maintenance: Restarting Browser to clear RAM...")
                try:
                    scraper.close()
                    time.sleep(5) # Give OS time to reclaim memory
                    scraper = TwitterScraper(headless=True)
                    print("   [Success] Browser rebooted.")
                except Exception as e:
                    print(f"   [Error] Browser restart failed: {e}")
                    # Try to continue even if restart failed, or re-raise if critical

            # 2. FETCH LATEST DYNAMIC THRESHOLDS
            BUY_THRESH, SELL_THRESH = cm.get_thresholds()
            print(f"   [Config] Active Threshold: +/- {BUY_THRESH:.3f}")

            # 3. REFRESH TICKERS periodically
            if cycle_count % REFRESH_TICKERS_CYCLES == 0:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Updating Market Movers...")
                try:
                    raw_tickers = get_market_movers()
                    if raw_tickers:
                        tickers = [t if t.startswith('$') else f"${t}" for t in raw_tickers]
                    print(f"   > Tracking Targets: {tickers}")
                except Exception as e:
                    print(f"   > Scanner failed ({e}). Keeping old list.")

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning Markets (Cycle {cycle_count})...")
            
            for ticker in tickers:
                # 4. STEALTH MODE (Random Sleep)
                sleep_delay = random.uniform(3, 7)
                print(f"   [Wait] Sleeping {sleep_delay:.1f}s to act human...")
                time.sleep(sleep_delay)

                try:
                    clean_ticker = ticker.replace('$', '')
                    
                    # A. GET NEWS
                    try:
                        news_df = get_finviz_news(clean_ticker)
                        _, news_score = calculate_metrics(news_df)
                    except Exception as e:
                        print(f"   [WARN] News failed for {ticker}: {e}")
                        news_score = 0
                    
                    # B. GET TWITTER
                    diversity, social_score, status = analyze_twitter_signal(scraper, ticker)
                    
                    # C. DECISION MATRIX (Dynamic Logic)
                    sentiment_gap = social_score - news_score
                    print(f" > {ticker}: News({news_score:.2f}) | Social({social_score:.2f}) | Gap({sentiment_gap:.2f})")
                    
                    signal = "HOLD"

                    # --- SCENARIO 1: PURE ARBITRAGE (The Leak) ---
                    # Twitter knows something, News is silent.
                    if diversity > DIVERSITY_THRESHOLD and abs(news_score) < 0.2:
                        
                        # Case A: Bullish (Dynamic Threshold)
                        if social_score > BUY_THRESH:
                            signal = "BUY (Social-Arbitrage)"
                            print(f"   >>> SIGNAL: {signal}")
                            log_signal(ticker, signal, social_score, news_score, diversity)

                        # Case B: Bearish (Dynamic Threshold)
                        elif social_score < -BUY_THRESH:
                            signal = "SELL (Social-Arbitrage)"
                            print(f"   >>> SIGNAL: {signal}")
                            log_signal(ticker, signal, social_score, news_score, diversity)

                    # --- SCENARIO 2: THE REBELLION (The Conflict) ---
                    # News and Social are fighting. We bet on the Crowd.
                    
                    # Case A: News Good, Crowd Bad -> SHORT
                    elif news_score > BUY_THRESH and social_score < -BUY_THRESH:
                        signal = "SELL (Rebellion)"
                        print(f"   >>> SIGNAL: {signal} | Fading the News!")
                        log_signal(ticker, signal, social_score, news_score, diversity)

                    # Case B: News Bad, Crowd Good -> LONG
                    elif news_score < -BUY_THRESH and social_score > BUY_THRESH:
                        signal = "BUY (Rebellion)"
                        print(f"   >>> SIGNAL: {signal} | Buying the Fear!")
                        log_signal(ticker, signal, social_score, news_score, diversity)

                    # --- SCENARIO 3: NOISE / CONSENSUS ---
                    else:
                        if abs(social_score) > BUY_THRESH and abs(news_score) > BUY_THRESH:
                             print(f"   [Hold] Consensus (Priced In).")
                
                except Exception as e:
                    print(f"   [ERROR] Skipping {ticker}: {e}")
                    continue 
            
            cycle_count += 1
            
            # 5. HEARTBEAT (Minimum Rest)
            elapsed = time.time() - cycle_start_time
            sleep_time = max(10, CHECK_INTERVAL_SECONDS - elapsed)
            
            print(f"Cycle took {elapsed:.1f}s. Sleeping for {sleep_time:.1f}s...")
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\nEngine Stopped.")
        try:
            scraper.close()
        except:
            pass
    except Exception as e:
        print(f"Critical Runtime Error: {e}")
        try:
            scraper.close()
        except:
            pass

if __name__ == "__main__":
    main()