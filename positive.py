import os

from pathlib import Path
from dotenv import load_dotenv
import praw
from mastodon import Mastodon
from transformers import pipeline
import logging

# ==================== #
# 0. Load .env file    #
# ==================== #
# load_dotenv()

# ==================== #
# 1. Setup Logging      #
# ==================== #
logging.basicConfig(
    filename="positive_bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ==================== #
# 2. Setup Reddit      #
# ==================== #
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="PositiveContentBot"
)

subreddit = reddit.subreddit("UpliftingNews")

# ==================== #
# 3. Sentiment AI      #
# ==================== #
sentiment_model = pipeline("sentiment-analysis")

def is_positive(text):
    result = sentiment_model(text[:512])[0]
    return result["label"] == "POSITIVE" and result["score"] > 0.95

# ==================== #
# 4. Mastodon Auth     #
# ==================== #
mastodon = Mastodon(
    access_token=os.getenv("MASTODON_ACCESS_TOKEN"),
    api_base_url=os.getenv("MASTODON_API_BASE_URL")
)

# ==================== #
# 5. Duplicate Tracking#
# ==================== #
posted_file = Path("posted_urls.txt")
if not posted_file.exists():
    posted_file.touch()

with open(posted_file, "r") as f:
    posted_urls = set(line.strip() for line in f.readlines())

def save_posted_url(url):
    posted_urls.add(url)
    with open(posted_file, "a") as f:
        f.write(url + "\n")

# ==================== #
# 6. Bot Workflow       #
# ==================== #
def post_positive_story():
    for submission in subreddit.hot(limit=20):
        title = submission.title
        url = submission.url

        if url in posted_urls:
            logging.info(f"Skipped (already posted): {title} - {url}")
            continue

        if is_positive(title):
            toot_text = f"🌍 Good News: {title}\n{url}"
            if len(toot_text) > 500:  # Mastodon limit
                toot_text = toot_text[:497] + "..."
            
            try:
                mastodon.toot(toot_text)
                logging.info(f"Posted: {title} - {url}")
                save_posted_url(url)
            except Exception as e:
                logging.error(f"Failed to post: {title} - {url} - {e}")
            break
        else:
            logging.info(f"Skipped (not positive enough): {title} - {url}")

if __name__ == "__main__":
    post_positive_story()
