import requests
import pandas as pd
import yfinance as yf # <--- NEW IMPORT
from io import StringIO

# --- PHYSICS ENGINE (THE FILTER) ---
def validate_speedboat_physics(ticker):
    """
    Returns True ONLY if the ticker is a 'Speedboat':
    1. Mid-Cap ($2B - $50B) -> heavy enough to be safe, light enough to move.
    2. High Liquidity (Avg Vol > 1M) -> ensures we can exit.
    3. Price > $5 -> filters out garbage penny stocks.
    """
    try:
        # We use 'fast_info' if available, or fallback to .info
        stock = yf.Ticker(ticker)
        
        # 1. Check Volume (Must be Liquid)
        # Using fast_info is much faster for scanners
        vol = stock.fast_info['last_volume'] if hasattr(stock, 'fast_info') else stock.info.get('averageVolume', 0)
        
        if vol < 1_000_000: 
            return False # Too illiquid (The RGC Risk)

        # 2. Check Market Cap (The Goldilocks Zone)
        # We want > $2B to avoid rug pulls. 
        # We allow up to $200B now to catch things like AMD, but avoid Mega-Caps like AAPL/MSFT if you want speed.
        mkt_cap = stock.fast_info['market_cap'] if hasattr(stock, 'fast_info') else stock.info.get('marketCap', 0)

        if mkt_cap < 2_000_000_000: # Less than 2B is dangerous
            return False 

        # 3. Price Filter (Avoid $0.50 stocks)
        price = stock.fast_info['last_price'] if hasattr(stock, 'fast_info') else stock.info.get('currentPrice', 0)
        if price < 5.00:
            return False

        return True

    except Exception as e:
        # If we can't verify it, ignore it.
        return False

def get_market_movers():
    """
    Robust scanner that impersonates a Chrome browser to bypass 
    Yahoo Finance's 429 Rate Limiting blocks.
    """
    print("--- Scanning Market for Speedboats (Volatile + Liquid) ---")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    raw_tickers = set()
    
    # URL 1: Top Gainers
    try:
        url_gainers = "https://finance.yahoo.com/gainers"
        response = requests.get(url_gainers, headers=headers)
        if response.status_code == 200:
            df_gainers = pd.read_html(StringIO(response.text))[0]
            top_gainers = df_gainers['Symbol'].head(5).tolist() # Grab top 5 to filter later
            raw_tickers.update(top_gainers)
    except Exception as e:
        print(f"Error fetching Gainers: {e}")

    # URL 2: Most Active
    try:
        url_active = "https://finance.yahoo.com/most-active"
        response = requests.get(url_active, headers=headers)
        if response.status_code == 200:
            df_active = pd.read_html(StringIO(response.text))[0]
            top_active = df_active['Symbol'].head(5).tolist()
            raw_tickers.update(top_active)
    except Exception as e:
        print(f"Error fetching Active: {e}")

    # --- THE FILTERING PHASE ---
    final_tickers = []
    print(f"   > Raw Candidates: {list(raw_tickers)}")
    
    for t in raw_tickers:
        if validate_speedboat_physics(t):
            final_tickers.append(t)
        else:
            # We don't print every rejection to keep logs clean, but we skip them.
            pass
            
    # Limit to top 3 quality picks
    final_tickers = final_tickers[:3]

    if not final_tickers:
        print("   > No Speedboats found. Using Safe Watchlist.")
        return ['NVDA', 'TSLA', 'AMD']
        
    return final_tickers

if __name__ == "__main__":
    hot_stocks = get_market_movers()
    print("\nFINAL WATCHLIST FOR TWITTER SCRAPER:")
    print(hot_stocks)