import os
import re
from pathlib import Path
from dotenv import load_dotenv  # Optional for local runs
import praw
from mastodon import Mastodon
from transformers import pipeline
import logging

# ==================== #
# 0. Load .env file    #
# ==================== #
# Only load .env if running locally
if Path(".env").exists():
    load_dotenv()

# ==================== #
# 1. Setup Logging      #
# ==================== #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("positive_bot.log"),
        logging.StreamHandler()  # Prints logs to console
    ]
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
UPLIFTING_KEYWORDS = [
    "peace", "community", "help", "kindness", "charity",
    "nature", "achievement", "success",
    "support", "uplift", "hope", "joy", "cooperate", "cooperation", "love", "understanding"
]

def is_uplifting(text):
    """
    Returns True if the text contains at least one uplifting keyword.
    """
    text_lower = text.lower()
    return any(re.search(rf"\b{re.escape(keyword)}\b", text_lower) for keyword in UPLIFTING_KEYWORDS)

sentiment_model = pipeline("sentiment-analysis")

def is_positive(text):
    """
    Returns a combined score based on sentiment confidence and uplifting keywords.
    - Sentiment score contributes up to 1.0
    - Each keyword adds +0.03
    """
    try:
        result = sentiment_model(text[:512])[0]
    except Exception as e:
        logging.error(f"Sentiment analysis failed for: {text} - {e}")
        return 0.0

    sentiment_score = result["score"] if result["label"] == "POSITIVE" else 0.0

    # Keyword score
    text_lower = text.lower()
    keyword_matches = sum(
        1 for kw in UPLIFTING_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", text_lower)
    )
    keyword_score = keyword_matches * 0.03

    total_score = sentiment_score + keyword_score

    logging.info(
        f"Sentiment: {result['label']} ({result['score']:.2f}), "
        f"Keyword matches: {keyword_matches}, "
        f"Keyword score: {keyword_score:.2f}, "
        f"Total score: {total_score:.2f}"
    )

    return total_score





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
    # Write entire set to avoid duplicates
    with open(posted_file, "w") as f:
        f.write("\n".join(posted_urls) + "\n")

# ==================== #
# 6. Bot Workflow       #
# ==================== #
def post_positive_story():
    best_submission = None
    best_score = 0.0

    for submission in subreddit.hot(limit=20):
        title = submission.title
        url = submission.url

        if url in posted_urls:
            logging.info(f"Skipped (already posted): {title} - {url}")
            continue

        score = is_positive(title)

        if score >= 0.97 and score > best_score:
            best_submission = (submission, score)

        logging.info(f"Checked: {title} - {url}, Score: {score:.2f}")

    if best_submission:
        submission, score = best_submission
        toot_text = f"🌍 Good News: {submission.title}\n{submission.url}"
        if len(toot_text) > 500:
            toot_text = toot_text[:497] + "..."

        try:
            # mastodon.toot(toot_text)
            logging.info(f"Would post (score {score:.2f}): {submission.title} - {submission.url}")
            save_posted_url(submission.url)
        except Exception as e:
            logging.error(f"Failed to process: {submission.title} - {submission.url} - {e}")
    else:
        logging.info("No suitable positive story found.")


# ==================== #
# 7. Main entry point  #
# ==================== #
if __name__ == "__main__":
    post_positive_story()
