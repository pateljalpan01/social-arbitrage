import pandas as pd
import yfinance as yf
import time
import os
import csv
from datetime import datetime, timedelta
from threading import Lock # <--- IMPORT LOCK

# --- IMPORT THE DYNAMIC BRAIN ---
try:
    from config_manager import ConfigManager
except ImportError:
    ConfigManager = None

# --- CONFIGURATION ---
SIGNAL_FILE = "sentiment_signals.csv"
TRADE_LOG_FILE = "trade_log.csv"
POSITION_SIZE = 100000  
CHECK_INTERVAL = 10     
STOP_LOSS_PCT = 0.01    
TAKE_PROFIT_PCT = 0.05  
TIME_STOP_MINUTES = 30  
MIN_SCALP_PROFIT = 2.00 
TRAILING_ACTIVATION = 100.0  
TRAILING_CALLBACK = 0.05     

# --- THE TALKING STICK ---
print_lock = Lock() 

class PaperTrader:
    def __init__(self):
        self.positions = {} 
        self.trade_log = set() 
        self.realized_pnl = 0.0 
        
        if ConfigManager:
            self.cm = ConfigManager()
        else:
            self.cm = None
        
        if os.path.exists(SIGNAL_FILE):
            try:
                df = pd.read_csv(SIGNAL_FILE)
                for index, row in df.iterrows():
                    unique_id = f"{row['Timestamp']}_{row['Ticker']}"
                    self.trade_log.add(unique_id)
            except Exception:
                pass
        
        if not os.path.exists(TRADE_LOG_FILE):
            with open(TRADE_LOG_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Ticker', 'Action', 'Price', 'Shares', 'PnL_Realized'])

        print("--- PAPER TRADER V3.1 (Trailing Stop + Physics Filter) ---")

    def safe_print(self, message):
        """Thread-safe printing helper"""
        with print_lock:
            print(message)

    def log_transaction(self, ticker, action, price, shares, pnl=0.0):
        with open(TRADE_LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                ticker, action, price, shares, pnl
            ])

    def get_live_price(self, ticker):
        clean_ticker = ticker.replace('$', '')
        try:
            # We explicitly ask for regularMarketPrice to avoid '0.0' glitches in pre-market
            tick = yf.Ticker(clean_ticker)
            data = tick.fast_info
            price = data.last_price
            
            # SANITY CHECK: Price cannot be zero or negative
            if price is None or price <= 0.01:
                return None
                
            return price
        except Exception:
            # Fallback to slower method if fast_info fails
            try:
                data = yf.download(clean_ticker, period="1d", interval="1m", progress=False)
                if not data.empty:
                    price = data['Close'].iloc[-1].item()
                    if price > 0.01: return price
                return None
            except:
                return None

    def check_exits(self):
        for ticker, pos in list(self.positions.items()):
            current_price = self.get_live_price(ticker)
            if not current_price: continue

            if pos['type'] == 'LONG':
                pnl = (current_price - pos['entry']) * pos['shares']
                pct_change = (current_price - pos['entry']) / pos['entry']
            else: 
                pnl = (pos['entry'] - current_price) * pos['shares']
                pct_change = (pos['entry'] - current_price) / pos['entry']

            if pnl > pos['max_pnl']:
                pos['max_pnl'] = pnl

            # 1. TRAILING STOP
            if pos['max_pnl'] > TRAILING_ACTIVATION:
                drop_from_peak = pos['max_pnl'] - pnl
                allowed_drop = pos['max_pnl'] * TRAILING_CALLBACK
                if drop_from_peak > allowed_drop:
                    self.safe_print(f"   [TRAILING STOP] {ticker} Profit dropped from ${pos['max_pnl']:.2f} to ${pnl:.2f}. Locking gain.")
                    self.close_position(ticker, current_price, "TRAILING_STOP")
                    continue

            # 2. HARD STOP LOSS
            if pct_change < -STOP_LOSS_PCT:
                self.safe_print(f"   [STOP LOSS] {ticker} hit -{STOP_LOSS_PCT*100}% trigger.")
                self.close_position(ticker, current_price, "STOP_LOSS")
                continue

            # 3. TAKE PROFIT
            if pct_change > TAKE_PROFIT_PCT:
                self.safe_print(f"   [TAKE PROFIT] {ticker} hit +{TAKE_PROFIT_PCT*100}% trigger!")
                self.close_position(ticker, current_price, "TAKE_PROFIT")
                continue

            # 4. TIME DECAY
            time_held = datetime.now() - pos['time']
            if time_held > timedelta(minutes=TIME_STOP_MINUTES):
                if pnl > MIN_SCALP_PROFIT:
                    self.safe_print(f"   [TIME STOP] Held {ticker} > {TIME_STOP_MINUTES}m and Green. Exiting.")
                    self.close_position(ticker, current_price, "TIME_EXIT")

    def close_position(self, ticker, price, reason):
        if ticker in self.positions:
            pos = self.positions[ticker]
            if pos['type'] == 'LONG':
                pnl = (price - pos['entry']) * pos['shares']
            else: 
                pnl = (pos['entry'] - price) * pos['shares']
            
            self.realized_pnl += pnl
            self.safe_print(f"   [CLOSE {reason}] PnL: ${pnl:,.2f}")
            self.log_transaction(ticker, f"CLOSE_{reason}", price, pos['shares'], pnl)
            del self.positions[ticker]

            if self.cm:
                self.cm.update_dynamic_thresholds()

    def execute_trade(self, signal_row):
        ticker = signal_row['Ticker']
        action = signal_row['Signal']
        timestamp = signal_row['Timestamp']
        
        unique_id = f"{timestamp}_{ticker}"
        if unique_id in self.trade_log:
            return
        
        current_price = self.get_live_price(ticker)
        if not current_price: return

        # --- PHYSICS CHECK (Second Line of Defense) ---
        # If market_scanner failed to filter it, we filter it here.
        # We assume if it has a valid price > $5, it's at least not a complete penny stock.
        if current_price < 5.00:
             self.safe_print(f"   [REJECTED] {ticker} Price ${current_price} is too low (Penny Stock Risk).")
             self.trade_log.add(unique_id)
             return

        new_trade_type = "LONG" if "BUY" in action else "SHORT"
        
        if ticker in self.positions:
            current_pos = self.positions[ticker]
            if current_pos['type'] != new_trade_type:
                self.safe_print(f"   [FLIP] Reversing {ticker} from {current_pos['type']} to {new_trade_type}")
                self.close_position(ticker, current_price, "FLIP_SIGNAL")
            else:
                self.trade_log.add(unique_id) 
                return

        self.safe_print(f"\n>>> SIGNAL: {ticker} | {action} @ ${current_price:.4f}")

        shares = POSITION_SIZE / current_price
        self.positions[ticker] = {
            'type': new_trade_type,
            'shares': shares,
            'entry': current_price,
            'time': datetime.now(),
            'max_pnl': -99999.0 
        }
        self.safe_print(f"   [OPEN {new_trade_type}] {shares:.2f} shares")
        self.log_transaction(ticker, f"OPEN_{new_trade_type}", current_price, shares, 0.0)
        self.trade_log.add(unique_id)

    def print_dashboard(self):
        with print_lock: # <--- THE FIX FOR STUTTERING
            print("\n" + "="*80)
            print(f"PORTFOLIO DASHBOARD ({datetime.now().strftime('%H:%M:%S')})")
            print(f"{'TICKER':<8} | {'TYPE':<6} | {'ENTRY':<8} | {'CURRENT':<8} | {'PnL ($)':<10} | {'MAX PnL':<10}")
            print("-" * 80)
            
            total_unrealized = 0
            for ticker, pos in list(self.positions.items()):
                curr_price = self.get_live_price(ticker)
                if not curr_price: continue
                
                if pos['type'] == 'LONG':
                    pnl = (curr_price - pos['entry']) * pos['shares']
                else: 
                    pnl = (pos['entry'] - curr_price) * pos['shares']
                
                if pnl > pos['max_pnl']: pos['max_pnl'] = pnl
                    
                total_unrealized += pnl
                print(f"{ticker:<8} | {pos['type']:<6} | {pos['entry']:<8.4f} | {curr_price:<8.4f} | {pnl:>10,.2f} | {pos['max_pnl']:>10,.2f}")
                
            print("-" * 80)
            print(f"REALIZED PnL:   ${self.realized_pnl:,.2f}")
            print(f"UNREALIZED PnL: ${total_unrealized:,.2f}")
            print(f"TOTAL PROFIT:   ${self.realized_pnl + total_unrealized:,.2f}")
            print("="*80 + "\n")

    def run(self):
        while True:
            # 1. Read Signals
            if os.path.exists(SIGNAL_FILE):
                try:
                    df = pd.read_csv(SIGNAL_FILE)
                    for index, row in df.tail(5).iterrows():
                        self.execute_trade(row)
                except Exception as e:
                    self.safe_print(f"Error reading CSV: {e}")
            
            # 2. Check Exits
            self.check_exits()

            # 3. Print Status
            if self.positions:
                self.print_dashboard()
            else:
                self.safe_print(f"[{datetime.now().strftime('%H:%M:%S')}] No positions. Listening...")
                
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    bot = PaperTrader()
    bot.run()