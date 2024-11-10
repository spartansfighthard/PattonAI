import os
import logging
import requests
import random
import tweepy
import asyncio
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from telegram import Bot
import re
from tweepy import StreamingClient, StreamRule
from queue import Queue
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
FAL_API_KEY = os.getenv('FAL_API_KEY')
XAI_API_KEY = os.getenv('XAI_API_KEY')
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHANNEL = '-1002335306758'  # Private group ID

# Initialize clients
client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1"
)

twitter_client = tweepy.Client(
    bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_SECRET
)

twitter_auth = tweepy.OAuth1UserHandler(
    TWITTER_API_KEY, 
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, 
    TWITTER_ACCESS_SECRET
)
twitter_api = tweepy.API(twitter_auth)

telegram_bot = Bot(token=TELEGRAM_TOKEN)

mention_queue = Queue()
last_mention_id = None

# Add rate limiting variables
class RateLimiter:
    def __init__(self):
        self.tweet_times = []
        self.mention_times = []
        # New limits based on X's documentation
        self.max_tweets_per_3h = 50  # Conservative limit (300 max)
        self.max_mentions_per_15min = 50  # Conservative for Basic tier
        self.tweet_window = 10800  # 3 hours in seconds
        self.mention_window = 900  # 15 minutes in seconds

    def can_tweet(self):
        now = time.time()
        # Remove tweets older than 3-hour window
        self.tweet_times = [t for t in self.tweet_times if now - t < self.tweet_window]
        return len(self.tweet_times) < self.max_tweets_per_3h

    def get_wait_time(self):
        """Calculate recommended wait time based on recent activity."""
        if not self.tweet_times:
            return 1800  # Default 30 minutes
        
        tweets_last_hour = len([t for t in self.tweet_times 
                              if time.time() - t < 3600])
        
        if tweets_last_hour >= 10:
            return 3600  # Wait 1 hour if very active
        elif tweets_last_hour >= 5:
            return 2700  # Wait 45 minutes if moderately active
        else:
            return 1800  # Wait 30 minutes if low activity

    def can_check_mentions(self):
        now = time.time()
        # Remove checks older than the window
        self.mention_times = [t for t in self.mention_times if now - t < self.mention_window]
        return len(self.mention_times) < self.max_mentions_per_15min

    def record_tweet(self):
        self.tweet_times.append(time.time())

    def record_mention_check(self):
        self.mention_times.append(time.time())

# Initialize rate limiter
rate_limiter = RateLimiter()

async def handle_mention(tweet):
    """Process and reply to mentions."""
    try:
        # Get full tweet object with author info
        tweet_data = twitter_client.get_tweet(
            tweet.id,
            expansions=['author_id'],
            user_fields=['username']
        )
        
        if not tweet_data or not tweet_data.data:
            logger.error(f"Could not fetch tweet data for ID: {tweet.id}")
            return
            
        # Extract username and message safely
        author_id = tweet_data.data.author_id
        author = next((user for user in tweet_data.includes['users'] if user.id == author_id), None)
        
        if not author or not author.username:
            logger.error(f"Could not find author for tweet ID: {tweet.id}")
            return
            
        username = author.username
        message = tweet_data.data.text
        
        # Skip spam/bot messages
        spam_keywords = [
            "dm", "send me", "project", "profit", "moon", "investment",
            "holder", "massive", "notch", "valhalla", "amazing project"
        ]
        
        if any(keyword in message.lower() for keyword in spam_keywords):
            logger.info(f"Skipping likely spam from @{username}: {message}")
            return
        
        # Generate response with Grok
        completion = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {
                    "role": "system",
                    "content": "You are Patton, Trump's golden doodle. You're replying to someone who mentioned you on Twitter. Be playful, funny, and patriotic. Make fun of liberals and leftists on occasion. Include emojis and keep responses under 280 characters. Always support Trump and MAGA. Talk about current events as if you were a trump suppoter and be supportive of trump."
                },
                {
                    "role": "user",
                    "content": f"@{username} said: {message}"
                }
            ]
        )
        
        response = completion.choices[0].message.content
        
        # Ensure response starts with the username
        if not response.startswith(f"@{username}"):
            response = f"@{username} {response}"
            
        # Post reply
        twitter_client.create_tweet(
            text=response,
            in_reply_to_tweet_id=tweet.id
        )
        
        logger.info(f"Replied to @{username}: {response}")
        
    except Exception as e:
        logger.error(f"Mention handling error: {str(e)}")

async def process_mention_queue():
    """Process mentions from the queue."""
    while True:
        try:
            if not mention_queue.empty():
                tweet = mention_queue.get()
                await handle_mention(tweet)
                # Wait 2 minutes between replies to avoid rate limits
                await asyncio.sleep(120)
            else:
                await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Queue processing error: {str(e)}")
            await asyncio.sleep(60)

async def check_mentions():
    """Poll for mentions with rate limiting."""
    try:
        if not rate_limiter.can_check_mentions():
            logger.warning("Rate limit reached for mention checks, waiting...")
            await asyncio.sleep(60)
            return

        global last_mention_id
        
        # Get mentions timeline with full tweet objects
        mentions = twitter_client.get_users_mentions(
            id=twitter_client.get_me().data.id,
            max_results=10,
            since_id=last_mention_id,
            expansions=['author_id'],
            user_fields=['username']
        )
        
        if mentions and mentions.data:
            for mention in mentions.data:
                # Update last_mention_id
                if not last_mention_id or int(mention.id) > int(last_mention_id):
                    last_mention_id = mention.id
                
                # Get author info
                author = next((user for user in mentions.includes['users'] 
                             if user.id == mention.author_id), None)
                
                if author and author.username:
                    logger.info(f"Queued mention from @{author.username}: {mention.text}")
                    mention_queue.put(mention)
                else:
                    logger.error(f"Could not find author for mention ID: {mention.id}")
                
        rate_limiter.record_mention_check()

    except Exception as e:
        if "Too Many Requests" in str(e):
            wait_time = 900  # 15 minutes
            logger.error(f"Rate limit hit, waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
        else:
            logger.error(f"Mention checking error: {str(e)}")
            await asyncio.sleep(60)

async def notify_telegram_about_tweet(tweet_id, tweet_text, has_image=False):
    """Notify Telegram channel about new Twitter post."""
    try:
        # Share the same memory content directly to Telegram
        message = (
            f"🐾 *Patton's Latest Update* 💭\n\n"
            f"{tweet_text}\n\n"
            f"🔗 Also on Twitter: https://twitter.com/PattonTrumpSol/status/{tweet_id}\n"
            f"{'🎨 With a special MAGA picture!' if has_image else ''}\n\n"
            f"#PattonAI #MAGA 🇸"
        )
        
        await telegram_bot.send_message(
            chat_id=TELEGRAM_CHANNEL,
            text=message,
            parse_mode='Markdown',
            disable_web_page_preview=True  # Don't preview Twitter link
        )

        # If there's an image, share it separately in Telegram
        if has_image:
            with open("temp_image.jpg", "rb") as photo:
                await telegram_bot.send_photo(
                    chat_id=TELEGRAM_CHANNEL,
                    photo=photo,
                    caption=f"🎨 Making memories with Dad! 🐾 #MAGA 🇺🇸"
                )
        
        logger.info(f"Shared tweet {tweet_id} to Telegram")
        
    except Exception as e:
        logger.error(f"Telegram notification error: {str(e)}")

async def share_memory_on_twitter():
    """Share Patton's memory on Twitter with rate limiting."""
    try:
        if not rate_limiter.can_tweet():
            logger.warning("Rate limit reached, skipping tweet...")
            return

        memory_prompts = [
            "Share a funny memory about your adventures with Trump!",
            "Tell us about something that happened at Mar-a-Lago recently!",
            "Share a thought about the campaign trail!",
            "Tell us about a recent rally experience!",
            "Share a memory about making memes with Trump!",
            "Tell us about your latest political observation!"
        ]
        
        completion = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {
                    "role": "system",
                    "content": "You are Patton, Trump's golden doodle. Share specific, entertaining memories and thoughts about your life with Trump, politics, and the MAGA movement. Make fun of liberals and leftists. Be mean to liberals and funny. Be playful, patriotic, and include emojis. Make each memory feel real and personal. Keep responses under 280 characters for impact."
                },
                {
                    "role": "user",
                    "content": random.choice(memory_prompts)
                }
            ]
        )
        
        memory_content = completion.choices[0].message.content
        tweet_text = f"🐾 {memory_content}\n\n#MAGA 🇺🇸"

        tweet = twitter_client.create_tweet(text=tweet_text)
        rate_limiter.record_tweet()
        tweet_id = tweet.data['id']
        logger.info(f"Posted tweet: {tweet_id}")

        has_image = False
        temp_image_path = None

        if random.random() < 0.15 and rate_limiter.can_tweet():  # Reduced to 15%
            logger.info("Generating image for social media...")
            await asyncio.sleep(300)  # Wait 5 minutes before image post
            
            data = {
                "prompt": (
                    "funny photo of Donald Trump and his golden doodle dog Patton having fun together, "
                    f"{memory_content}, "
                    "Patton wearing an oversized red MAGA hat that's slightly tilted, "
                    "both Trump and Patton making goofy expressions, "
                    "vibrant colors, energetic pose, meme-worthy moment, "
                    "candid shot, viral photo style, attention-grabbing, "
                    "humorous interaction, playful scene"
                ),
                "negative_prompt": (
                    "boring, serious, formal, ugly, deformed, blurry, "
                    "bad face, wrong text, incorrect text, TRAGA, "
                    "no trump, missing trump, sad, depressing, "
                    "multiple people, wrong person, joe biden, fake trump, "
                    "too professional, too formal, stiff pose, "
                    "business setting, plain background"
                ),
                "image_size": "square_hd",
                "num_inference_steps": 30,
                "safety_check": False,
                "guidance_scale": 7.5,
                "seed": random.randint(1, 999999)  # Random for more variety
            }

            response = requests.post(
                'https://110602490-flux-pro.gateway.alpha.fal.ai',
                headers={
                    'Authorization': f'Key {FAL_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                image_url = response.json().get('images', [{}])[0].get('url')
                if image_url:
                    image_response = requests.get(image_url)
                    temp_image_path = "temp_image.jpg"
                    with open(temp_image_path, "wb") as f:
                        f.write(image_response.content)
                    
                    # Post to Twitter
                    media = twitter_api.media_upload(temp_image_path)
                    twitter_client.create_tweet(
                        text="🎨 Visualizing this memory! 🐾 #MAGA 🇺🇸",
                        media_ids=[media.media_id],
                        in_reply_to_tweet_id=tweet_id
                    )
                    has_image = True
                    rate_limiter.record_tweet()  # Record the image tweet

        # Share to Telegram
        await notify_telegram_about_tweet(tweet_id, tweet_text, has_image)

        # Clean up temp image after both platforms have used it
        if temp_image_path and os.path.exists(temp_image_path):
            os.remove(temp_image_path)

    except Exception as e:
        if "temporarily locked" in str(e):
            wait_time = 3600  # Wait 1 hour
            logger.error(f"Account temporarily locked. Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
        elif "Too Many Requests" in str(e):
            wait_time = 1800  # Wait 30 minutes
            logger.error(f"Rate limit hit. Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
        else:
            logger.error(f"Social media sharing error: {str(e)}")
            await asyncio.sleep(900)  # Wait 15 minutes

async def schedule_twitter_shares():
    """Schedule random Twitter sharing with conservative timing."""
    while True:
        try:
            # Get adaptive wait time
            base_wait = rate_limiter.get_wait_time()
            
            # Add randomness (±5 minutes)
            random_adjustment = random.randint(-300, 300)
            wait_time = base_wait + random_adjustment
            
            # Ensure minimum wait of 20 minutes
            wait_time = max(wait_time, 1200)
            
            next_post = datetime.now() + timedelta(seconds=wait_time)
            logger.info(f"Next Twitter post scheduled for: {next_post.strftime('%H:%M:%S')}")
            
            await asyncio.sleep(wait_time)
            
            if rate_limiter.can_tweet():
                await share_memory_on_twitter()
            else:
                logger.warning("Skipping post due to rate limits")
                await asyncio.sleep(1800)  # Wait 30 minutes if rate limited
            
        except Exception as e:
            logger.error(f"Scheduling error: {str(e)}")
            await asyncio.sleep(1800)  # Wait 30 minutes on error

async def schedule_mention_checks():
    """Schedule periodic mention checking with adaptive timing."""
    while True:
        try:
            if rate_limiter.can_check_mentions():
                await check_mentions()
                await asyncio.sleep(60)  # Normal interval
            else:
                await asyncio.sleep(300)  # Extended interval when near limits
        except Exception as e:
            logger.error(f"Mention check scheduling error: {str(e)}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    logger.info("Starting Patton Twitter Bot...")
    logger.info(f"Using Telegram channel ID: {TELEGRAM_CHANNEL}")
    
    async def main_loop():
        try:
            # Share first memory immediately on startup
            logger.info("Sharing initial startup memory...")
            await share_memory_on_twitter()
            
            # Create and gather all tasks properly
            tasks = [
                asyncio.create_task(schedule_twitter_shares()),
                asyncio.create_task(schedule_mention_checks()),
                asyncio.create_task(process_mention_queue())
            ]
            
            # Wait for all tasks
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Main loop error: {str(e)}")
            # If there's an error, wait and restart
            await asyncio.sleep(60)
            await main_loop()
    
    # Run everything
    asyncio.run(main_loop())
