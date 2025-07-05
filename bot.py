from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import os
import logging
import asyncio
from datetime import datetime, timezone
import aiohttp
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
OWNER_CHAT_ID = int(os.environ.get('OWNER_CHAT_ID', 0))
WEB_LINK = "https://earn-dollars.vercel.app"
BACKEND_URL = "https://tg-back-2.onrender.com"
PORT = int(os.environ.get('PORT', 5000))

# Dictionary to track inviter-invitee relationships
invited_users = {}

# Global variables for graceful shutdown
shutdown_event = threading.Event()
bot_application = None

# Function to get formatted UTC date and time
def get_formatted_datetime():
    now = datetime.now(timezone.utc)
    return {
        'date': now.strftime('%d/%m/%y'),
        'time': now.strftime('%H:%M UTC')
    }

# Function to notify the owner
async def notify_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.message.from_user
        datetime_info = get_formatted_datetime()
        username = f"@{user.username}" if user.username else user.first_name

        notification = (
            f"New user joined:\n\n"
            f"Name: {username}\n"
            f"Date: {datetime_info['date']}\n"
            f"Time: {datetime_info['time']}\n"
            f"Location: IN \n"
        )

        # Create reminder button
        reminder_button = InlineKeyboardButton("Reminder", callback_data=f"reminder_{user.id}_{user.first_name}_{user.username or ''}")
        reply_markup = InlineKeyboardMarkup([[reminder_button]])

        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=notification,
            reply_markup=reply_markup
        )
        logger.info(f"Owner notified about new user: {username}")
    except Exception as e:
        logger.error(f"Error notifying owner: {e}")

# Function to save user data
async def save_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    first_name = user.first_name
    username = user.username

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{BACKEND_URL}/save_user_data",
                json={
                    "user_id": user_id,
                    "first_name": first_name,
                    "username": username
                }
            ) as response:
                if response.status == 200:
                    logger.info(f"Saved user data for user_id {user_id}")
                else:
                    logger.error(f"Failed to save user data for user_id {user_id}: {await response.text()}")
        except Exception as e:
            logger.error(f"Error saving user data for user_id {user_id}: {e}")

# Handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Save user data
        await save_user_data(update, context)

        user = update.message.from_user
        start_args = context.args
        inviter_id = start_args[0] if start_args else None
        user_id = user.id

        # Log the start command
        logger.info(f"Received /start command from user {user_id}")
        logger.info(f"Start args: {start_args}, Inviter ID: {inviter_id}")

        if inviter_id and inviter_id != str(user_id):
            logger.info(f"New user {user_id} started the bot using invite link from {inviter_id}")

            # Check if the user has already been invited by this inviter
            if inviter_id not in invited_users:
                invited_users[inviter_id] = set()

            if user_id not in invited_users[inviter_id]:
                invited_users[inviter_id].add(user_id)

                # Send congratulatory message to the inviter
                congratulatory_msg = f"Congratulations you invited {user.first_name}!"
                check_balance_button = InlineKeyboardButton("CHECK BALANCE", web_app=WebAppInfo(url=WEB_LINK))
                reply_markup = InlineKeyboardMarkup([[check_balance_button]])

                await context.bot.send_message(
                    chat_id=int(inviter_id),
                    text=congratulatory_msg,
                    reply_markup=reply_markup
                )
                logger.info(f"Sent congratulatory message to inviter {inviter_id}")

                # Update inviter stats
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.post(
                            f"{BACKEND_URL}/handle_invite",
                            json={
                                "inviter_id": inviter_id,
                                "invitee_id": user_id
                            }
                        ) as response:
                            if response.status == 200:
                                logger.info(f"Updated stats for inviter {inviter_id}")
                            else:
                                logger.error(f"Failed to update stats for inviter {inviter_id}: {await response.text()}")
                    except Exception as e:
                        logger.error(f"Error updating stats for inviter {inviter_id}: {e}")

        # Create welcome message
        username = f"@{user.username}" if user.username else user.first_name
        welcome_msg = (
            f"Welcome {username}\n\n"
            "Earn real money by inviting your friends.\n"
            "Withdraw your earnings instantly. \n"
            "Start inviting now and watch your balance grow!"
        )

        # Create connect button with web app
        web_app_url = f"{WEB_LINK}?start={inviter_id or ''}"
        connect_button = InlineKeyboardButton("START", web_app=WebAppInfo(url=web_app_url))
        reply_markup = InlineKeyboardMarkup([[connect_button]])

        # Send welcome message with button
        await update.message.reply_text(
            welcome_msg,
            reply_markup=reply_markup
        )
        logger.info(f"Sent welcome message to user {user_id}")

        # Notify owner
        await notify_owner(update, context)

    except Exception as e:
        logger.error(f"Error handling start command: {e}")

# Handle reminder button clicks
async def handle_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        if query.data.startswith("reminder_"):
            # Handle individual reminder
            try:
                user_id, first_name, username = query.data.split('_')[1:]
                user_id = int(user_id)

                # Create welcome message
                username_display = f"@{username}" if username else first_name
                welcome_msg = (
                    f"Welcome {username_display} \n\n"
                    "Earn real money by inviting your friends.\n"
                    "Withdraw your earnings instantly.\n "
                    "Start inviting now and watch your balance grow!"
                )

                # Create connect button with web app
                connect_button = InlineKeyboardButton("START", web_app=WebAppInfo(url=WEB_LINK))
                reply_markup = InlineKeyboardMarkup([[connect_button]])

                # Send reminder message
                await context.bot.send_message(
                    chat_id=user_id,
                    text=welcome_msg,
                    reply_markup=reply_markup
                )
                await query.answer("Reminder sent to the user!")
                logger.info(f"Sent reminder to user {user_id}")

            except Exception as individual_error:
                logger.error(f"Error sending individual reminder: {individual_error}")
                await query.answer("Failed to send reminder. User may have blocked the bot or data is invalid.")
        elif query.data == "reminder_all":
            await query.answer("Use /remindall command to remind all users.")

    except Exception as e:
        logger.error(f"Error in handle_reminder: {e}")
        await query.answer("An unexpected error occurred.")

# Handle /remindall command
async def remind_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_user.id == OWNER_CHAT_ID:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"{BACKEND_URL}/get_all_users"
                    ) as response:
                        if response.status == 200:
                            users = await response.json()
                            total_users = len(users)
                            reminder_all_button = InlineKeyboardButton("Reminder All", callback_data="send_reminder_all")
                            reply_markup = InlineKeyboardMarkup([[reminder_all_button]])
                            await update.message.reply_text(f"Total users: {total_users}\nClick the button to remind all users.", reply_markup=reply_markup)
                        else:
                            logger.error(f"Failed to get all users: {await response.text()}")
                            await update.message.reply_text("Failed to get user list from database.")
                except Exception as e:
                    logger.error(f"Error in remind_all request: {e}")
                    await update.message.reply_text("Failed to send reminders due to network error.")
        else:
            await update.message.reply_text("You are not authorized to use this command.")

    except Exception as e:
        logger.error(f"Error in remind_all: {e}")
        await update.message.reply_text("An unexpected error occurred.")

# Handle callback query for sending reminder to all users
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        if query.data == "send_reminder_all":
            # Handle reminder all button click
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"{BACKEND_URL}/get_all_users"
                    ) as response:
                        if response.status == 200:
                            users = await response.json()
                            sent_count = 0
                            failed_count = 0

                            for user in users:
                                try:
                                    user_id = user.get("user_id")
                                    first_name = user.get("first_name")
                                    username = user.get("username")

                                    # Skip if user_id is missing or invalid
                                    if not user_id:
                                        logger.warning(f"Skipping user with missing user_id: {user}")
                                        failed_count += 1
                                        continue

                                    # Ensure user_id is an integer
                                    try:
                                        user_id = int(user_id)
                                    except (ValueError, TypeError):
                                        logger.warning(f"Skipping user with invalid user_id: {user_id}")
                                        failed_count += 1
                                        continue

                                    username_display = f"@{username}" if username else first_name
                                    welcome_msg = (
                                        f"Welcome {username_display} \n\n"
                                        "Earn real money by inviting your friends.\n"
                                        "Withdraw your earnings instantly.\n "
                                        "Start inviting now and watch your balance grow!"
                                    )

                                    # Create connect button with web app
                                    connect_button = InlineKeyboardButton("START", web_app=WebAppInfo(url=WEB_LINK))
                                    reply_markup = InlineKeyboardMarkup([[connect_button]])

                                    # Send reminder message with individual error handling
                                    await context.bot.send_message(
                                        chat_id=user_id,
                                        text=welcome_msg,
                                        reply_markup=reply_markup
                                    )
                                    sent_count += 1
                                    logger.info(f"Sent reminder to user {user_id} ({username_display})")

                                    # Add small delay to avoid rate limiting
                                    await asyncio.sleep(0.1)

                                except Exception as user_error:
                                    failed_count += 1
                                    logger.error(f"Failed to send reminder to user {user_id}: {user_error}")
                                    # Continue with next user instead of stopping
                                    continue

                            # Send summary to owner
                            summary_msg = f"Reminder broadcast completed ✅\nTotal Users: {len(users)}\n Sent: {sent_count}\n Failed: {failed_count}"
                            await context.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=summary_msg
                            )
                            await query.answer("Reminders sent successfully.")
                            logger.info(f"Reminder All completed: {sent_count} sent, {failed_count} failed")

                        else:
                            logger.error(f"Failed to get all users: {await response.text()}")
                            await query.answer("Failed to get user list from database.")
                except Exception as e:
                    logger.error(f"Error in reminder_all request: {e}")
                    await query.answer("Failed to send reminders due to network error.")
        await query.answer()
    except Exception as e:
        logger.error(f"Error in handle_callback_query: {e}")

# Handle all other messages
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Save user data
        await save_user_data(update, context)

        user = update.message.from_user
        username = f"@{user.username}" if user.username else user.first_name

        welcome_msg = (
            f"Welcome {username}\n\n"
            "Earn real money by inviting your friends.\n"
            "Withdraw your earnings instantly.\n "
            "Start inviting now and watch your balance grow!"
        )

        # Create connect button with web app
        connect_button = InlineKeyboardButton("START", web_app=WebAppInfo(url=WEB_LINK))
        reply_markup = InlineKeyboardMarkup([[connect_button]])

        await update.message.reply_text(
            welcome_msg,
            reply_markup=reply_markup
        )
        logger.info(f"Sent welcome message to user {user.id}")

    except Exception as e:
        logger.error(f"Error handling message: {e}")

# Improved HTTP Request Handler
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = json.dumps({"status": "healthy", "service": "telegram-bot"})
        self.wfile.write(response.encode())

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = json.dumps({"status": "received"})
        self.wfile.write(response.encode())

    def log_message(self, format, *args):
        # Override to use our logger instead of default stderr logging
        logger.info(f"HTTP Request: {format % args}")

# Start HTTP server in a separate thread
def start_http_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logger.info(f"HTTP server starting on port {PORT}")
    
    # Keep the server running until shutdown
    while not shutdown_event.is_set():
        try:
            httpd.handle_request()
        except Exception as e:
            if not shutdown_event.is_set():
                logger.error(f"HTTP server error: {e}")
                break
    
    logger.info("HTTP server stopped")

# Signal handler for graceful shutdown
def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()
    
    # Stop the bot application
    if bot_application:
        logger.info("Stopping bot application...")
        asyncio.create_task(bot_application.stop())
    
    sys.exit(0)

# Main function
def main():
    global bot_application
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start HTTP server in a separate thread
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()
    logger.info("HTTP server thread started")

    # Build and configure the bot application
    bot_application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    bot_application.add_handler(CommandHandler("start", start))
    bot_application.add_handler(CommandHandler("remindall", remind_all))
    bot_application.add_handler(CallbackQueryHandler(handle_reminder, pattern="^reminder_"))
    bot_application.add_handler(CallbackQueryHandler(handle_callback_query, pattern="^send_reminder_all$"))
    bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    # Run the bot with error handling and restart capability
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries and not shutdown_event.is_set():
        try:
            logger.info(f"Starting bot (attempt {retry_count + 1}/{max_retries})...")
            bot_application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            break  # If we reach here, the bot stopped normally
        except Exception as e:
            retry_count += 1
            logger.error(f"Bot error (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries and not shutdown_event.is_set():
                logger.info("Retrying in 5 seconds...")
                import time
                time.sleep(5)
            else:
                logger.error("Max retries reached or shutdown requested")
                break
    
    logger.info("Bot stopped")

if __name__ == '__main__':
    main()
