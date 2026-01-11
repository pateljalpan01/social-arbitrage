import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import timedelta

def analyze_alpha():
    # 1. Load your Sentiment Data
    try:
        df = pd.read_csv("sentiment_signals.csv")
    except FileNotFoundError:
        print("Error: sentiment_signals.csv not found. Run main.py first!")
        return

    # Clean up the Ticker format (Remove '$' for Yahoo Finance)
    df['Clean_Ticker'] = df['Ticker'].str.replace('$', '')
    
    # Convert Timestamp to Datetime objects
    # Assuming your system is saving in local time, we might need to adjust timezones later.
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], dayfirst=True)
    
    print(f"Loaded {len(df)} sentiment data points.")
    
    results = []

    # 2. Loop through each unique ticker to fetch market data
    unique_tickers = df['Clean_Ticker'].unique()
    
    for ticker in unique_tickers:
        print(f"Fetching price data for {ticker}...")
        
        # Download 5-minute data for the last 5 days (to ensure we catch your csv dates)
        try:
            # We fetch 5 days to be safe. 5m interval is key.
            stock_data = yf.download(ticker, period="5d", interval="5m", progress=False)
            
            # Formatting Yahoo's index to be timezone-naive for easy comparison
            stock_data.index = stock_data.index.tz_localize(None)
            
        except Exception as e:
            print(f"  -> Could not fetch data for {ticker}: {e}")
            continue

        # 3. Match Sentiment to Price
        # Get all rows for this specific ticker
        ticker_sentiments = df[df['Clean_Ticker'] == ticker]
        
        for index, row in ticker_sentiments.iterrows():
            sent_time = row['Timestamp']
            
            # Find the price candle closest to this sentiment timestamp
            # We use 'get_indexer' to find the nearest timestamp in the stock data
            idx = stock_data.index.get_indexer([sent_time], method='nearest')[0]
            
            if idx == -1: continue # Time not found
            
            # Current Price (at time of tweet)
            price_t = stock_data.iloc[idx]['Close']
            
            # Future Price (10 minutes later = +2 candles)
            # We want to know: Did the price move AFTER the tweet?
            try:
                price_t_plus_10 = stock_data.iloc[idx + 2]['Close']
                
                # Calculate Return (%)
                # Note: .item() ensures we get a float, not a Series
                ret = ((price_t_plus_10 - price_t) / price_t) * 100
                
                results.append({
                    'Ticker': ticker,
                    'Sentiment_Score': row['Score'],
                    'Future_Return_10m': ret.item(),
                    'Signal': row['Signal']
                })
            except IndexError:
                # We might be at the end of the data (tweet just happened)
                continue

    # 4. The "Quant" Verdict
    if not results:
        print("Not enough historical data yet to calculate Alpha. Let the bot run longer!")
        return

    alpha_df = pd.DataFrame(results)
    
    print("\n" + "="*40)
    print("       ALPHA ANALYSIS REPORT")
    print("="*40)
    print(alpha_df.head())
    
    # Correlation Check: Does High Sentiment = High Return?
    correlation = alpha_df['Sentiment_Score'].corr(alpha_df['Future_Return_10m'])
    print(f"\nCorrelation Coefficient (Sentiment vs Price): {correlation:.4f}")
    
    if correlation > 0.1:
        print(">> STATUS: Positive Correlation detected! Your model has predictive power.")
    elif correlation < -0.1:
        print(">> STATUS: Negative Correlation. The market is trading against your signals.")
    else:
        print(">> STATUS: No Correlation yet. Needs more data (Noise dominates).")

    # 5. Visual Proof (Scatter Plot)
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=alpha_df, x='Sentiment_Score', y='Future_Return_10m', hue='Ticker', s=100)
    plt.axhline(0, color='grey', linestyle='--')
    plt.axvline(0, color='grey', linestyle='--')
    plt.title(f"Does Sentiment Predict Price? (Corr: {correlation:.2f})")
    plt.xlabel("FinBERT Sentiment Score (-1 to +1)")
    plt.ylabel("Next 10-min Price Return (%)")
    plt.grid(True, alpha=0.3)
    plt.show()

if __name__ == "__main__":
    analyze_alpha()