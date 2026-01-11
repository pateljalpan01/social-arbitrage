import json
import os
import pandas as pd

# --- CONSTANTS ---
CONFIG_FILE = "trading_config.json"
TRADE_LOG = "trade_log.csv"

# Default settings (Neutral Stance)
DEFAULT_CONFIG = {
    "buy_threshold": 0.5,
    "sell_threshold": 0.5,
    "max_position_size": 100000,
    "mode": "NEUTRAL"  # Can be AGGRESSIVE, NEUTRAL, or DEFENSIVE
}

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        """Loads the JSON config or creates a default one if missing."""
        if not os.path.exists(CONFIG_FILE):
            print(f"   [Config] No config found. Creating default {CONFIG_FILE}...")
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return DEFAULT_CONFIG

    def save_config(self, new_config):
        """Saves the updated settings to JSON."""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(new_config, f, indent=4)
        self.config = new_config

    def get_thresholds(self):
        """Returns the current dynamic thresholds."""
        return self.config.get("buy_threshold", 0.5), self.config.get("sell_threshold", 0.5)

    def update_dynamic_thresholds(self):
        """
        THE REWARD / PUNISHMENT ENGINE
        Reads the trade log, calculates Win Rate, and adjusts thresholds.
        """
        if not os.path.exists(TRADE_LOG):
            return

        try:
            df = pd.read_csv(TRADE_LOG)
            
            # Filter for Closed Trades only
            closed_trades = df[df['Action'].str.contains('CLOSE')]
            
            # We need at least 5 trades to start learning
            if len(closed_trades) < 5:
                return

            # Analyze the last 10 trades (Short-term memory)
            recent_trades = closed_trades.tail(10)
            
            # Calculate Win Rate
            wins = len(recent_trades[recent_trades['PnL_Realized'] > 0])
            total = len(recent_trades)
            win_rate = wins / total if total > 0 else 0.0
            
            current_buy = self.config.get("buy_threshold", 0.5)
            
            # --- LOGIC GATES ---
            
            # SCENARIO 1: REWARD (Hot Streak)
            # If we are winning > 70% of trades, the bot is too picky.
            # We lower the threshold to let more trades in.
            if win_rate >= 0.70:
                new_buy = max(0.35, current_buy * 0.98) # Lower by 2%, floor at 0.35
                mode = "AGGRESSIVE"
                print(f"   [Learning] Win Rate is {win_rate*100:.0f}%. REWARDING system. (Thresh: {new_buy:.3f})")

            # SCENARIO 2: PUNISHMENT (Cold Streak)
            # If we are winning < 40%, the signals are garbage.
            # We raise the threshold to filter out noise.
            elif win_rate <= 0.40:
                new_buy = min(0.85, current_buy * 1.05) # Raise by 5%, cap at 0.85
                mode = "DEFENSIVE"
                print(f"   [Learning] Win Rate is {win_rate*100:.0f}%. PUNISHING system. (Thresh: {new_buy:.3f})")

            # SCENARIO 3: NEUTRAL (Stability)
            else:
                new_buy = current_buy
                mode = "NEUTRAL"
            
            # Save Logic
            self.config["buy_threshold"] = round(new_buy, 3)
            self.config["sell_threshold"] = round(new_buy, 3) # Symmetric for now
            self.config["mode"] = mode
            self.save_config(self.config)

        except Exception as e:
            print(f"   [Config Error] Could not update thresholds: {e}")

# Test code to run if you execute this file directly
if __name__ == "__main__":
    cm = ConfigManager()
    print("Current Config:", cm.config)
    print("Attempting to learn from logs...")
    cm.update_dynamic_thresholds()
    print("New Config:", cm.config)