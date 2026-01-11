import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# CONSTANTS
LOG_FILE = "trade_log.csv"
RISK_FREE_RATE = 0.045 # 4.5% Annual Risk Free Rate (Treasury Bills)
TRADING_DAYS = 252
MINUTES_PER_DAY = 390

def calculate_sharpe(df):
    """
    Calculates the 'High Frequency' Sharpe Ratio.
    """
    # 1. Calculate PnL per minute
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df.set_index('Timestamp', inplace=True)
    
    # Resample to 1-minute snapshots to standardize the timeframe
    minute_pnl = df['PnL_Realized'].resample('1min').sum().fillna(0)
    
    if len(minute_pnl) < 2:
        return 0.0
        
    # 2. Calculate Returns (Assuming $100k base per trade unit)
    # Ideally, you'd track total equity, but for PnL analysis:
    mean_pnl = minute_pnl.mean()
    std_pnl = minute_pnl.std()
    
    if std_pnl == 0:
        return 0.0
    
    # 3. Minute-based Sharpe
    minute_sharpe = mean_pnl / std_pnl
    
    # 4. Annualize it (Sqrt of minutes in a year)
    # N = 252 days * 390 minutes = 98,280 minutes
    annualized_sharpe = minute_sharpe * np.sqrt(TRADING_DAYS * MINUTES_PER_DAY)
    
    return annualized_sharpe

def generate_report():
    try:
        df = pd.read_csv(LOG_FILE)
        
        # Filter for closed trades to see realized gains
        closed_trades = df[df['Action'] == 'CLOSE']
        
        if closed_trades.empty:
            print("No closed trades to analyze yet.")
            return

        total_pnl = closed_trades['PnL_Realized'].sum()
        win_rate = (len(closed_trades[closed_trades['PnL_Realized'] > 0]) / len(closed_trades)) * 100
        sharpe = calculate_sharpe(closed_trades)

        print("\n" + "="*40)
        print(f"   QUANT PERFORMANCE METRICS")
        print("="*40)
        print(f"Total PnL:        ${total_pnl:,.2f}")
        print(f"Trade Count:      {len(closed_trades)}")
        print(f"Win Rate:         {win_rate:.1f}%")
        print("-" * 40)
        print(f"Sharpe Ratio:     {sharpe:.2f} (Annualized)")
        print("="*40)
        
        if sharpe > 3.0:
            print(">> RATING: INSTITUTIONAL GRADE (A+)")
        elif sharpe > 1.5:
            print(">> RATING: SOLID RETAIL STRATEGY (B)")
        else:
            print(">> RATING: NEEDS OPTIMIZATION (C)")

    except FileNotFoundError:
        print("No log file found. Run the Paper Trader first!")

if __name__ == "__main__":
    generate_report()