from news_scraper import get_sentiment, nlp_social

print("--- DEBUGGING SOCIAL BRAIN ---")

# Test a massively bullish phrase
text = "Tesla is going to the moon! 🚀 Buying more $TSLA"

# 1. Get Raw Output
raw_result = nlp_social(text)
print(f"Raw Model Output: {raw_result}")

# 2. Check how our function interprets it
score = get_sentiment(text, source_type='social')
print(f"Calculated Score: {score}")

if score == 0:
    print("\n>>> PROBLEM FOUND: The code is not recognizing the label name!")
else:
    print("\n>>> SUCCESS: Logic is working.")