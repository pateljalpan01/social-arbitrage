import pandas as pd
from news_scraper import get_finviz_news, get_sentiment

print("--- NEWS BRAIN AUDIT ---")
ticker = "TSLA"

# 1. Get the Raw Headlines
print(f"Scraping {ticker}...")
df = get_finviz_news(ticker)

# 2. Score them one by one
print(f"\n{'SENTIMENT':<10} | {'SCORE':<6} | HEADLINE")
print("-" * 80)

for headline in df['Headline'].head(15):
    # Use the News Brain (ProsusAI)
    score = get_sentiment(headline, source_type='news')
    
    # Visual Label
    if score > 0.1: label = "BULLISH"
    elif score < -0.1: label = "BEARISH"
    else: label = "NEUTRAL"
    
    print(f"{label:<10} | {score:>6.2f} | {headline[:60]}...")