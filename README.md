# Market-Resonance: Social Sentiment Arbitrage Engine 🚀

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![NLP](https://img.shields.io/badge/AI-FinBERT-orange)
![Status](https://img.shields.io/badge/Status-Operational-green)

## 📊 Project Overview
Institutional investors often react to news before it hits traditional terminals. **Market-Resonance** is a Quantitative Engineering tool that ingests unstructured social data (Twitter/X), filters out bot noise, and uses a **Financial Large Language Model (FinBERT)** to generate real-time trading signals.

Unlike generic sentiment tools, this project uses **Session Injection** to bypass modern anti-bot defenses and **Context-Aware NLP** to distinguish between "Selling stock" (Neutral insider activity) vs "Selling off" (Bearish price action).

## 🏗 Architecture
1.  **Ingestion Layer (The Eyes):** * Uses `Playwright` for browser automation to handle dynamic JavaScript loading.
    * **Session Injection:** Bypasses login screens/CAPTCHAs by injecting pre-authenticated cookies (`state.json`).
2.  **Preprocessing Layer (The Filter):**
    * Removes "Ticker Spam" (tweets with >5 cashtags).
    * Filters non-English characters and Ad-bot patterns.
    * *Metric:* Typically removes ~80-90% of noise from raw feeds.
3.  **Inference Layer (The Brain):**
    * Model: `yiyanghkust/finbert-tone` (BERT model fine-tuned on financial reports).
    * Calculates a confidence-weighted Z-score (-1.0 to +1.0).

## 🛠 Tech Stack
* **Core:** Python 3.10+, Pandas, NumPy
* **AI/NLP:** PyTorch, HuggingFace Transformers (FinBERT)
* **Automation:** Playwright (Chromium Engine)

## 🚀 How to Run
1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    playwright install
    ```
2.  **Authenticate (One-Time Setup):**
    Run the login handler to generate your session ticket.
    ```bash
    python login_setup.py
    ```
3.  **Run the Engine:**
    ```bash
    python main.py
    ```

## 📉 Sample Output
```text
[NEUTRAL] (98%): $NVDA Nvidia Director sells $40 million worth of stock...
[POSITIVE] (100%): Yesterday $NVDA stayed elevated with tightening ranges...

FINAL SIGNAL: BULLISH
SENTIMENT SCORE: 0.5030

⚠️ Disclaimer
This tool is for educational purposes. Web scraping may violate terms of service. Use responsibly.