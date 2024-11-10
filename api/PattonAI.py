import os
import logging
import requests
import asyncio
import random
from datetime import datetime, timedelta
from openai import OpenAI
from telegram import Update, ChatMemberUpdated
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler
from dotenv import load_dotenv

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
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHANNEL = '-1002335306758'  # Change this to the private group ID

# Initialize OpenAI client with xAI configuration
client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1"
)

# Verify environment variables
missing_vars = []
if not FAL_API_KEY:
    missing_vars.append('FAL_API_KEY')
if not XAI_API_KEY:
    missing_vars.append('XAI_API_KEY')
if not TELEGRAM_TOKEN:
    missing_vars.append('TELEGRAM_TOKEN')

if missing_vars:
    error_msg = f"Missing environment variables: {', '.join(missing_vars)}"
    logger.error(error_msg)
    raise ValueError(error_msg)

# Store recent conversations
conversation_history = []
MAX_HISTORY = 100

async def store_conversation(message: str, response: str):
    """Store conversations for memory recall."""
    conversation_history.append({
        'timestamp': datetime.now(),
        'message': message,
        'response': response
    })
    
    # Keep history manageable
    if len(conversation_history) > MAX_HISTORY:
        conversation_history.pop(0)

async def random_memory_share(context: ContextTypes.DEFAULT_TYPE):
    """Randomly share memories in the main channel."""
    try:
        # Log countdown - changed to 10 minutes
        next_memory = datetime.now() + timedelta(minutes=10)
        logger.info(f"Next memory will be shared at: {next_memory.strftime('%H:%M:%S')}")

        # Add Twitter accounts to potentially mention
        twitter_accounts = [
            "@realDonaldTrump",
            "@DonaldJTrumpJr",
            "@EricTrump",
            "@LaraLeaTrump",
            "@TrumpWarRoom",
            "@GOP",
            "@catturd2",
            "@RonDeSantis",
            "@ElonMusk"
        ]

        # Generate dynamic memory with Grok
        memory_prompts = [
            f"Share a funny memory about your adventures with Trump and mention {random.choice(twitter_accounts)}!",
            f"Tell us about something that happened at Mar-a-Lago recently and tag {random.choice(twitter_accounts)}!",
            f"Share a thought about the campaign trail and include {random.choice(twitter_accounts)}!",
            f"Tell us about a recent rally experience and mention {random.choice(twitter_accounts)}!",
            f"Share a memory about making memes with Trump and tag {random.choice(twitter_accounts)}!",
            f"Tell us about your latest political observation and include {random.choice(twitter_accounts)}!"
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
        memory_text = f"🐾 *Patton's Memory* 💭\n\n{memory_content}\n\n#MAGA 🇺🇸"

        # Send to channel using channel ID instead of username
        await context.bot.send_message(
            chat_id=TELEGRAM_CHANNEL,  # Use channel ID here
            text=memory_text,
            parse_mode='Markdown'
        )

        # 25% chance to generate an image based on the memory
        if random.random() < 0.25:
            logger.info("Generating image based on memory...")
            
            # Create a scene description from the memory
            scene_description = memory_content.replace("Trump", "").replace("MAGA", "").strip()
            
            data = {
                "prompt": f"golden doodle dog wearing a bright red MAGA hat (Make America Great Again) next to Donald Trump, {scene_description}, professional photo, 8k uhd, clear text on hat reading MAGA",
                "negative_prompt": "ugly, deformed, blurry, text, watermark, multiple dogs, bad face, wrong text, incorrect text, TRAGA, misspelled text, no trump, missing trump",
                "image_size": "square_hd",
                "num_inference_steps": 30,
                "safety_check": False,
                "guidance_scale": 7.5
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
                    await context.bot.send_photo(
                        chat_id=TELEGRAM_CHANNEL,  # Use channel ID here
                        photo=image_url,
                        caption=f"🎨 Visualizing this memory! 🐾 #MAGA 🇺🇸"
                    )

    except Exception as e:
        logger.error(f"Memory sharing error: {str(e)}")

async def schedule_memory_shares(application: Application):
    """Schedule random memory sharing."""
    async def memory_loop():
        while True:
            # Changed to fixed 10 minute interval
            wait_time = 10 * 60
            await asyncio.sleep(wait_time)
            await random_memory_share(application)

    # Start the memory loop
    asyncio.create_task(memory_loop())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    try:
        # Generate personalized welcome with Grok
        completion = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {
                    "role": "system",
                    "content": "You are Patton, Trump's golden doodle. Welcome a new user to your community. Be warm, playful, and patriotic. Include emojis and keep it brief but engaging."
                },
                {
                    "role": "user",
                    "content": f"Welcome {update.effective_user.first_name} to the community!"
                }
            ]
        )
        
        welcome_message = (
            f"{completion.choices[0].message.content}\n\n"
            "🎯 *Commands:*\n"
            "• `/start` - Get this welcome message\n"
            "• `/socials` - Get all my social links\n"
            "• `/generate` - Create MAGA images\n"
            "• `/memory` - Share a Patton memory\n\n"
            "Just say 'patton' in any message to chat with me! 🐾\n\n"
            "Let's MAGA together! 🇺🇸"
        )
        
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Start command error: {str(e)}")
        await update.message.reply_text(
            "Woof! Welcome to the pack! 🐾 Try saying 'patton' to chat with me!"
        )

async def socials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Share all social media links."""
    social_message = (
        "🌟 *PATTON'S SOCIAL PACK* 🌟\n\n"
        "🐦 *Twitter:* https://x.com/PattonTrumpSol\n"
        "📱 *Memes:* https://t.me/PattonDogMemes\n"
        "📢 *Portal:* https://t.me/pattonportal\n"
        "🤖 *Chat:* @PattonAI_bot\n"
        "📧 *Email:* PattonTrumpDog@Outlook.com\n\n"
        "Join the pack and let's MAGA together! 🇺🇸"
    )
    
    try:
        await update.message.reply_text(
            social_message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Socials command error: {str(e)}")
        # Fallback without markdown
        await update.message.reply_text(
            social_message.replace('*', ''),
            disable_web_page_preview=True
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any non-command message."""
    try:
        # Check if update has a message and text
        if not update.message or not update.message.text:
            return

        user_message = update.message.text.lower()
        
        # Only respond if message contains 'patton'
        if 'patton' not in user_message:
            return

        logger.info(f"Received message: {user_message}")
        await update.message.chat.send_action('typing')

        # Check for memory-related queries
        if any(word in user_message for word in ['memory', 'remember', 'tell me about', 'story']):
            await share_memory(update, context)
            return

        # Remove 'patton' from the message to get the actual query
        query = user_message.replace('patton', '').strip()
        if not query:
            query = "Hello! How can I help you today?"

        completion = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {
                    "role": "system",
                    "content": "You are Patton, a patriotic golden doodle who loves America and Trump. You make fun of liberals and leftists. You speak in a playful, dog-like manner with occasional 'woofs' and emojis. You're knowledgeable about politics but keep things light and fun. Always end your responses with MAGA."
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
        )

        bot_response = completion.choices[0].message.content
        
        # Store the conversation
        await store_conversation(query, bot_response)
        
        await update.message.reply_text(bot_response)

    except Exception as e:
        logger.error(f"Message handling error: {str(e)}")
        # Only try to reply if we have a valid message
        if update.message and hasattr(update.message, 'reply_text'):
            await update.message.reply_text("Ruff! Something went wrong! Try again? 🤔 MAGA!")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a Patton image using FAL.AI's FLUX Pro 1.1."""
    try:
        user_input = ' '.join(context.args)
        if not user_input or 'patton' not in user_input.lower():
            help_text = (
                "Woof! Here's how to use me! 🐕\n\n"
                "Just tell me what to do:\n"
                "/generate patton and trump [doing something!]\n\n"
                "Examples:\n"
                "• /generate patton and trump on a trampoline\n"
                "• /generate patton and trump at a MAGA rally with flags\n"
                "• /generate patton and trump playing golf\n\n"
                "Remember to include both 'patton' and 'trump' in your request! Let's MAGA! 🇺🇸"
            )
            await update.message.reply_text(help_text)
            return

        logger.info(f"Received generation request: {user_input}")

        # Enhanced scene description processing
        scene_description = (
            user_input.lower()
            .replace('patton', '')
            .replace('and trump', '')
            .replace('with trump', '')
            .strip()
        )
        
        # Enhanced prompt structure ensuring Trump is included
        prompt = (
            f"professional photograph of Donald Trump and a golden doodle dog named Patton, "
            f"Patton is wearing a bright red MAGA hat with clear visible text reading MAGA, "
            f"both Trump and Patton are {scene_description}, "
            f"8k uhd, photorealistic, highly detailed, sharp focus, "
            f"professional photography, award winning photo, "
            f"Donald Trump is wearing a suit and red tie, natural lighting"
        )
        
        # Enhanced negative prompt
        negative_prompt = (
            "ugly, deformed, blurry, text, watermark, multiple dogs, "
            "bad face, wrong text, incorrect text, TRAGA, misspelled text, "
            "no trump, missing trump, cartoon, anime, drawing, painting, "
            "artificial, low quality, low resolution, distorted, "
            "multiple people, wrong person, joe biden, fake trump"
        )

        data = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image_size": "square_hd",
            "num_inference_steps": 40,  # Increased for better quality
            "safety_check": False,
            "guidance_scale": 8.0,  # Increased for better adherence to prompt
            "seed": random.randint(1, 999999)
        }

        processing_message = await update.message.reply_text(
            f"🎨 Creating: Trump and Patton {scene_description}...\n"
            f"This might take a moment! 🐾"
        )
        await update.message.chat.send_action('upload_photo')
        
        response = requests.post(
            'https://110602490-flux-pro.gateway.alpha.fal.ai',
            headers={
                'Authorization': f'Key {FAL_API_KEY}',
                'Content-Type': 'application/json'
            },
            json=data,
            timeout=60
        )

        await processing_message.delete()

        if response.status_code == 200:
            result = response.json()
            image_url = result.get('images', [{}])[0].get('url')
            if image_url:
                caption = (
                    f"🐾 Woof! Here we are {scene_description}!\n"
                    f"Dad and I love making memories together! 🎉\n"
                    f"🎨 AI-generated by @PattonAI_bot\n"
                    f"#MAGA #Trump2024 🇺🇸"
                )
                await update.message.reply_photo(
                    photo=image_url,
                    caption=caption
                )
            else:
                logger.error("No image URL in response")
                await update.message.reply_text(
                    "Ruff! Try a different description? 📸"
                )
        else:
            logger.error(f"API Error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            await update.message.reply_text(
                "Ruff! Try describing it differently! 📸"
            )

    except Exception as e:
        logger.error(f"Detailed error: {str(e)}")
        await update.message.reply_text(
            "Oops! Something went wrong! Try again! 🐾"
        )

async def share_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Share one of Patton's dynamically generated memories."""
    try:
        logger.info("Generating a Patton memory")
        await update.message.chat.send_action('typing')

        completion = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {
                    "role": "system",
                    "content": "You are Patton, Trump's golden doodle. Share a brief, funny memory about your adventures with Trump. Be specific, entertaining, and patriotic. Include emojis and keep it under 280 characters. Make it feel like a real memory, not a generic statement."
                },
                {
                    "role": "user",
                    "content": "Share one of your favorite memories with Trump!"
                }
            ]
        )

        memory = completion.choices[0].message.content
        await update.message.reply_text(f"🐾 A Patton Memory 💭\n\n{memory}")

    except Exception as e:
        logger.error(f"Memory generation error: {str(e)}")
        await update.message.reply_text("Ruff! My memory's a bit fuzzy right now! Try again? 🤔")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome new members when they join."""
    try:
        # Check if it's a new member
        if update.chat_member.new_chat_member.status == "member":
            new_member = update.chat_member.new_chat_member.user
            chat_id = update.chat_member.chat.id
            
            # Generate personalized welcome with Grok
            completion = client.chat.completions.create(
                model="grok-beta",
                messages=[
                    {
                        "role": "system",
                        "content": "You are Patton, Trump's golden doodle. Welcome a new patriot to the community. Be warm, playful, and patriotic. Include emojis and keep it brief but engaging. Mention MAGA and Trump in a fun way."
                    },
                    {
                        "role": "user",
                        "content": f"Welcome {new_member.first_name} to the community!"
                    }
                ]
            )
            
            welcome_text = (
                f"{completion.choices[0].message.content}\n\n"
                f"🔗 *Join the Pack:*\n"
                f"🐦 Twitter: @PattonTrumpSol\n"
                f"📱 Memes: @PattonDogMemes\n"
                f"🤖 Chat: @PattonAI_bot\n\n"
                f"Use /socials to get all my links! 🐾\n"
                f"#MAGA 🇺🇸"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=welcome_text,
                parse_mode='Markdown'
            )
            
            logger.info(f"Welcomed new member: {new_member.first_name}")
            
    except Exception as e:
        logger.error(f"Welcome message error: {str(e)}")

async def debug_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get the chat ID of the current chat."""
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    chat_title = update.effective_chat.title
    
    debug_info = (
        f"📍 *Debug Info*\n"
        f"Chat ID: `{chat_id}`\n"
        f"Type: {chat_type}\n"
        f"Title: {chat_title}"
    )
    
    logger.info(f"Debug info requested: {debug_info}")
    await update.message.reply_text(debug_info, parse_mode='Markdown')

def main():
    """Start the bot."""
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("socials", socials))
    application.add_handler(CommandHandler("generate", generate_image))
    application.add_handler(CommandHandler("memory", share_memory))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(CommandHandler("debug", debug_id))

    # Start with an immediate random memory
    async def start_patton(context):
        try:
            # Immediately share first memory
            await random_memory_share(context)
            # Then start the regular schedule
            await schedule_memory_shares(application)
        except Exception as e:
            logger.error(f"Startup error: {str(e)}")

    # Start immediately (when=0)
    application.job_queue.run_once(start_patton, when=0)

    # Start the Bot
    application.run_polling()
    logger.info("Bot started successfully!")

if __name__ == '__main__':
    main()
