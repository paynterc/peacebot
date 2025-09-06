from dotenv import load_dotenv
import os

load_dotenv()  # this reads .env and sets environment variables

import os
import praw
from mastodon import Mastodon
from transformers import pipeline

# =============== #
# 1. Setup Reddit #
# =============== #
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="PositiveContentBot"
)

subreddit = reddit.subreddit("UpliftingNews")

# =============== #
# 2. Sentiment AI #
# =============== #
sentiment_model = pipeline("sentiment-analysis")

def is_positive(text):
    result = sentiment_model(text[:512])[0]
    return result["label"] == "POSITIVE" and result["score"] > 0.95

# =============== #
# 3. Mastodon Auth#
# =============== #
mastodon = Mastodon(
    access_token=os.getenv("MASTODON_ACCESS_TOKEN"),
    api_base_url=os.getenv("MASTODON_API_BASE_URL")
)

# =============== #
# 4. Bot Workflow #
# =============== #
def post_positive_story():
    for submission in subreddit.hot(limit=20):
        title = submission.title
        url = submission.url

        if is_positive(title):
            toot_text = f"🌍 Good News: {title}\n{url}"
            if len(toot_text) > 500:  # Mastodon limit is 500 chars
                toot_text = toot_text[:497] + "..."
            mastodon.toot(toot_text)
            print("Posted:", toot_text)
            break

if __name__ == "__main__":
    post_positive_story()
