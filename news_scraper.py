import pandas as pd
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from transformers import BertTokenizer, BertForSequenceClassification, pipeline
import torch

# --- SETUP: Initialize DUAL BRAINS ---
print("--- Initializing The Twin Engines (This takes RAM!) ---")

try:
    # 1. THE NEWS ANCHOR (ProsusAI) - For Formal Headlines
    print(" > Loading News Brain (ProsusAI)...")
    model_news = "ProsusAI/finbert"
    tokenizer_news = BertTokenizer.from_pretrained(model_news)
    nlp_news = pipeline("sentiment-analysis", model=model_news, tokenizer=tokenizer_news)

    # 2. THE TWITTER SPECIALIST (FinTwitBERT) - For Slang/Emojis
    print(" > Loading Social Brain (FinTwitBERT)...")
    model_social = "StephanAkkerman/FinTwitBERT-sentiment"
    tokenizer_social = BertTokenizer.from_pretrained(model_social)
    nlp_social = pipeline("sentiment-analysis", model=model_social, tokenizer=tokenizer_social)
    
    print("--- Dual Brains Ready ---")
    
except Exception as e:
    print(f"CRITICAL ERROR loading models: {e}")
    exit()

# --- VERITY WEIGHTS ---
VERITY_WEIGHTS = {
    'finance.yahoo.com': 0.9,
    'bloomberg.com': 0.95,
    'reuters.com': 0.95,
    'wsj.com': 0.95,
    'marketbeat.com': 0.7,
    'benzinga.com': 0.6,
    'motleyfool.com': 0.4,
    'seekingalpha.com': 0.6,
    'twitter.com': 0.2,
    'generic_default': 0.5
}

def get_sentiment(text, source_type='news'):
    """
    Analyzes text using the appropriate brain.
    source_type: 'news' (default) or 'social'
    """
    if not text: return 0.0
    
    try:
        # Select the correct brain
        if source_type == 'social':
            results = nlp_social(str(text), truncation=True, max_length=512)
        else:
            results = nlp_news(str(text), truncation=True, max_length=512)
            
        result = results[0]
        label = result['label'].lower()
        confidence = result['score']
        
        # --- MAPPING LABELS (THE FIX) ---
        # ProsusAI uses: 'positive', 'negative', 'neutral'
        # FinTwitBERT uses: 'bullish', 'bearish', 'neutral'
        
        if 'positive' in label or 'bullish' in label:
            return confidence        # e.g., +0.99
        elif 'negative' in label or 'bearish' in label:
            return -confidence       # e.g., -0.99
        else: # neutral
            return 0.0
            
    except Exception as e:
        print(f"Error analyzing '{text[:15]}...': {e}")
        return 0.0

def get_finviz_news(ticker):
    """
    Scrapes Finviz news.
    """
    url = f'https://finviz.com/quote.ashx?t={ticker}'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error connecting to Finviz for {ticker}: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, 'html.parser')
    news_table = soup.find(id='news-table')
    
    if not news_table:
        print(f"No news found for {ticker}")
        return pd.DataFrame()
    
    parsed_data = []
    rows = news_table.find_all('tr')
    
    current_date = None
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 2:
            continue
            
        date_text = cols[0].text.strip()
        link_tag = cols[1].find('a')
        
        if not link_tag:
            continue
            
        headline = link_tag.text.strip()
        url_link = link_tag['href']
        
        full_text = cols[1].text.strip()
        source_text = full_text.replace(headline, "").strip()
        
        if 'Today' in date_text:
            today_str = datetime.now().strftime('%b-%d-%y')
            date_text = date_text.replace('Today', today_str)
            
        if ' ' in date_text:
            date_part, time_part = date_text.split(' ')
            current_date = date_part
        else:
            time_part = date_text
            
        full_timestamp = f"{current_date} {time_part}"
        
        parsed_data.append([full_timestamp, headline, source_text, url_link])
        
    return pd.DataFrame(parsed_data, columns=['Timestamp', 'Headline', 'Source', 'URL'])

def calculate_metrics(df):
    if df.empty:
        return df, 0
        
    # USE NEWS BRAIN
    df['Sentiment_Score'] = df['Headline'].apply(lambda x: get_sentiment(x, source_type='news'))
    
    # Verity Logic
    def get_verity(row):
        source = str(row['Source']).lower().replace(" ", "")
        url = str(row['URL']).lower()
        for key in VERITY_WEIGHTS:
            if key.replace(".com", "") in source: return VERITY_WEIGHTS[key]
        for key in VERITY_WEIGHTS:
            if key in url: return VERITY_WEIGHTS[key]
        return VERITY_WEIGHTS['generic_default']
        
    df['Verity_Score'] = df.apply(get_verity, axis=1)
    df['Weighted_Signal'] = df['Sentiment_Score'] * df['Verity_Score']
    
    total_weight = df['Verity_Score'].sum()
    composite_score = df['Weighted_Signal'].sum() / total_weight if total_weight > 0 else 0
        
    return df, composite_score