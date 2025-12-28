# telegram_bot_snapshot.py - Robust version with comprehensive error handling
import os
import sys
import time
import logging
import asyncio
import traceback
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import NetworkError, TimedOut, BadRequest

# Import your existing snapshot functionality
from camera_snapshot import send_snapshots_to_telegram, capture_camera_snapshot
from config_manager import load_telegram_config, load_camera_streams
from config import ALERTS_DIR

# Configure logging with rotation to prevent large log files
from logging.handlers import RotatingFileHandler

# Setup robust logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_file = 'telegram_bot.log'

# Create file handler with rotation (max 10MB, keep 3 files)
file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=3)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class CameraSnapshotBot:
    def __init__(self):
        self.bot_token = None
        self.authorized_chat_ids = []
        self.is_running = False
        self.command_locks = {}  # Per-chat command locks to prevent concurrent operations
        self.error_counts = {}   # Track error counts per chat
        self.last_error_time = {}  # Track last error time per chat
        
    def load_config(self):
        """Load Telegram configuration with error handling"""
        try:
            telegram_config = load_telegram_config()
            if telegram_config and len(telegram_config) >= 2:
                self.bot_token, chat_ids = telegram_config[:2]
                
                if isinstance(chat_ids, list):
                    self.authorized_chat_ids = [int(chat_id) for chat_id in chat_ids]
                else:
                    self.authorized_chat_ids = [int(chat_ids)]
                    
                logger.info(f"Configuration loaded successfully. Authorized chats: {self.authorized_chat_ids}")
                return True
            else:
                logger.error("Invalid telegram configuration format")
                return False
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def is_authorized(self, chat_id):
        """Check if chat_id is authorized with error handling"""
        try:
            return int(chat_id) in self.authorized_chat_ids
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid chat_id format: {chat_id}, error: {e}")
            return False
    
    def get_command_lock(self, chat_id):
        """Get or create a lock for a specific chat to prevent concurrent commands"""
        if chat_id not in self.command_locks:
            self.command_locks[chat_id] = asyncio.Lock()
        return self.command_locks[chat_id]
    
    def should_rate_limit(self, chat_id):
        """Check if we should rate limit this chat due to recent errors"""
        current_time = time.time()
        
        # Reset error count if it's been more than 5 minutes since last error
        if chat_id in self.last_error_time:
            if current_time - self.last_error_time[chat_id] > 300:  # 5 minutes
                self.error_counts[chat_id] = 0
        
        # Rate limit if more than 3 errors in recent time
        return self.error_counts.get(chat_id, 0) > 3
    
    def record_error(self, chat_id):
        """Record an error for rate limiting"""
        self.error_counts[chat_id] = self.error_counts.get(chat_id, 0) + 1
        self.last_error_time[chat_id] = time.time()
    
    async def safe_reply(self, update, message, parse_mode='Markdown'):
        """Safely reply to a message with fallback options"""
        try:
            return await update.message.reply_text(message, parse_mode=parse_mode)
        except BadRequest:
            # Try without markdown if formatting fails
            try:
                return await update.message.reply_text(message)
            except Exception as e:
                logger.error(f"Failed to send reply: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to send reply: {e}")
            return None
    
    async def safe_edit(self, message_obj, text, parse_mode='Markdown'):
        """Safely edit a message with fallback options"""
        try:
            return await message_obj.edit_text(text, parse_mode=parse_mode)
        except BadRequest:
            # Try without markdown if formatting fails
            try:
                return await message_obj.edit_text(text)
            except Exception as e:
                logger.error(f"Failed to edit message: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            return None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with comprehensive error handling"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        try:
            if not self.is_authorized(chat_id):
                await self.safe_reply(update, "Access denied. This bot is restricted to authorized users.")
                logger.warning(f"Unauthorized access attempt from chat {chat_id}, user {user_id}")
                return
            
            welcome_message = """Camera Snapshot Bot

Available commands:
• /snapshot - Capture snapshots from all cameras
• /status - Check camera status
• /cameras - List configured cameras
• /help - Show this help message

Quick commands (just type):
• snapshot - Quick snapshot capture
• status - Quick status check

Note: Snapshots will be sent only to you.
Bot is running with error recovery enabled."""
            
            await self.safe_reply(update, welcome_message)
            logger.info(f"Bot started for chat {chat_id}, user {user_id}")
            
        except Exception as e:
            logger.error(f"Error in start_command for chat {chat_id}: {e}")
            logger.error(traceback.format_exc())
            await self.safe_reply(update, "An error occurred. Please try again.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        chat_id = update.effective_chat.id
        
        try:
            if not self.is_authorized(chat_id):
                await self.safe_reply(update, "Access denied.")
                return
            
            help_text = """Camera Snapshot Bot Help

Commands:
• /snapshot or 'snapshot' - Capture and send snapshots
• /status or 'status' - Check system and camera status
• /cameras - List all configured cameras
• /help - Show this help message

Features:
• Automatic retry for failed captures
• Error recovery and logging
• Per-user private responses
• Rate limiting protection
• Detailed status reports

The bot will continue running even if individual commands fail."""
            
            await self.safe_reply(update, help_text)
            
        except Exception as e:
            logger.error(f"Error in help_command for chat {chat_id}: {e}")
            await self.safe_reply(update, "Help information temporarily unavailable.")
    
    async def snapshot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle snapshot command with comprehensive error handling and recovery"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Check authorization first
        if not self.is_authorized(chat_id):
            await self.safe_reply(update, "Access denied.")
            return
        
        # Check rate limiting
        if self.should_rate_limit(chat_id):
            await self.safe_reply(update, 
                "Too many recent errors. Please wait a few minutes before trying again.")
            return
        
        # Get command lock to prevent concurrent snapshot operations for this chat
        async with self.get_command_lock(chat_id):
            status_msg = None
            
            try:
                # Send initial status message
                status_msg = await self.safe_reply(update, "Starting camera snapshot capture...")
                
                if not status_msg:
                    logger.error(f"Could not send initial message to chat {chat_id}")
                    return
                
                # Load camera streams with error handling
                try:
                    camera_streams = load_camera_streams()
                except Exception as e:
                    error_msg = f"Failed to load camera configuration: {str(e)}"
                    logger.error(f"Camera config error for chat {chat_id}: {error_msg}")
                    await self.safe_edit(status_msg, f"Error: {error_msg}")
                    self.record_error(chat_id)
                    return
                
                if not camera_streams:
                    await self.safe_edit(status_msg, "No cameras configured in lan.txt")
                    return
                
                # Update status
                await self.safe_edit(status_msg, f"Capturing snapshots from {len(camera_streams)} cameras...")
                
                # Create telegram config for this specific user
                requesting_user_telegram_config = (self.bot_token, chat_id)
                
                # Attempt snapshot capture with comprehensive error handling
                try:
                    result = send_snapshots_to_telegram(
                        requesting_user_telegram_config, 
                        max_retries=2, 
                        silent_mode=True
                    )
                except Exception as snapshot_error:
                    error_msg = f"Snapshot capture failed: {str(snapshot_error)}"
                    logger.error(f"Snapshot error for chat {chat_id}: {error_msg}")
                    logger.error(traceback.format_exc())
                    
                    await self.safe_edit(status_msg, 
                        f"Snapshot capture failed due to system error. "
                        f"Please try again in a moment. Error logged for investigation.")
                    
                    self.record_error(chat_id)
                    return
                
                # Process results
                if result and result.get("success"):
                    successful_sends = result.get('successful_sends', 0)
                    total_cameras = result.get('total_cameras', 0)
                    failed_snapshots = result.get('failed_snapshots', 0)
                    failed_sends = result.get('failed_sends', 0)
                    
                    summary = f"""Snapshot Capture Complete

Results:
• Total Cameras: {total_cameras}
• Successful: {successful_sends}
• Failed: {failed_snapshots + failed_sends}
• Time: {datetime.now().strftime('%H:%M:%S')}
• Sent to: This chat only"""
                    
                    # Add failed camera details if any
                    if failed_snapshots > 0 or failed_sends > 0:
                        failed_details = []
                        details = result.get('details', [])
                        
                        for detail in details:
                            if not detail.get('snapshot_success') or not detail.get('send_success'):
                                error_msg = detail.get('error_message', 'Unknown error')
                                camera_name = detail.get('camera_name', 'Unknown camera')
                                failed_details.append(f"• {camera_name}: {error_msg}")
                        
                        if failed_details:
                            summary += f"\n\nFailed Cameras:\n" + "\n".join(failed_details[:5])
                            if len(failed_details) > 5:
                                summary += f"\n... and {len(failed_details) - 5} more"
                    
                    await self.safe_edit(status_msg, summary)
                    logger.info(f"Snapshots completed for chat {chat_id}: {successful_sends}/{total_cameras} successful")
                    
                else:
                    error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                    await self.safe_edit(status_msg, f"Snapshot capture failed: {error_msg}")
                    logger.error(f"Snapshot failed for chat {chat_id}: {error_msg}")
                    self.record_error(chat_id)
                
            except Exception as e:
                error_msg = f"Unexpected error during snapshot operation: {str(e)}"
                logger.error(f"Snapshot command error for chat {chat_id}: {error_msg}")
                logger.error(traceback.format_exc())
                
                try:
                    if status_msg:
                        await self.safe_edit(status_msg, 
                            "An unexpected error occurred. The system is still running. Please try again.")
                    else:
                        await self.safe_reply(update, 
                            "An error occurred processing your request. Please try again.")
                except:
                    pass  # Don't let error handling errors crash the bot
                
                self.record_error(chat_id)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle status command with error recovery"""
        chat_id = update.effective_chat.id
        
        if not self.is_authorized(chat_id):
            await self.safe_reply(update, "Access denied.")
            return
        
        status_msg = None
        
        try:
            status_msg = await self.safe_reply(update, "Checking system status...")
            
            if not status_msg:
                return
            
            # Load camera streams safely
            try:
                camera_streams = load_camera_streams()
            except Exception as e:
                await self.safe_edit(status_msg, f"Error loading camera configuration: {str(e)}")
                return
            
            if not camera_streams:
                await self.safe_edit(status_msg, "No cameras configured in lan.txt")
                return
            
            total_cameras = len(camera_streams)
            online_cameras = 0
            camera_status = {}
            
            await self.safe_edit(status_msg, f"Testing {total_cameras} cameras...")
            
            # Test cameras with individual error handling
            for camera_name, camera_url in camera_streams.items():
                try:
                    success, _, error = capture_camera_snapshot(camera_name, camera_url, timeout=3)
                    camera_status[camera_name] = {
                        'online': success,
                        'error': error if not success else None
                    }
                    if success:
                        online_cameras += 1
                except Exception as e:
                    camera_status[camera_name] = {
                        'online': False,
                        'error': f"Test failed: {str(e)}"
                    }
            
            # Create status report
            success_rate = (online_cameras/total_cameras*100) if total_cameras > 0 else 0
            status_report = f"""System Status Report

Camera Summary:
• Total Cameras: {total_cameras}
• Online: {online_cameras}
• Offline: {total_cameras - online_cameras}
• Success Rate: {success_rate:.0f}%

Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Requested by: Chat {chat_id}"""
            
            # Add individual camera status for smaller lists
            if total_cameras <= 8:
                status_report += "\n\nCamera Status:\n"
                for camera_name, status in camera_status.items():
                    if status['online']:
                        status_report += f"• {camera_name}: Online\n"
                    else:
                        error_short = status['error'][:25] + "..." if len(status['error']) > 25 else status['error']
                        status_report += f"• {camera_name}: {error_short}\n"
            
            await self.safe_edit(status_msg, status_report)
            logger.info(f"Status check completed for chat {chat_id}: {online_cameras}/{total_cameras} cameras online")
            
        except Exception as e:
            error_msg = f"Status check error: {str(e)}"
            logger.error(f"Status command error for chat {chat_id}: {error_msg}")
            
            try:
                if status_msg:
                    await self.safe_edit(status_msg, "Status check failed. System is still running.")
                else:
                    await self.safe_reply(update, "Status check failed. Please try again.")
            except:
                pass
    
    async def cameras_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle cameras command with error recovery"""
        chat_id = update.effective_chat.id
        
        if not self.is_authorized(chat_id):
            await self.safe_reply(update, "Access denied.")
            return
        
        try:
            camera_streams = load_camera_streams()
            
            if not camera_streams:
                await self.safe_reply(update, "No cameras configured in lan.txt")
                return
            
            cameras_list = f"Configured Cameras ({len(camera_streams)}):\n\n"
            
            for i, (camera_name, camera_url) in enumerate(camera_streams.items(), 1):
                # Hide sensitive parts of URL
                try:
                    url_parts = camera_url.split('@')
                    if len(url_parts) > 1:
                        display_url = f"rtsp://***@{url_parts[-1]}"
                    else:
                        display_url = camera_url[:50] + "..." if len(camera_url) > 50 else camera_url
                except:
                    display_url = "URL parsing error"
                
                cameras_list += f"{i}. {camera_name}\n   {display_url}\n\n"
            
            cameras_list += "Loaded from lan.txt"
            
            await self.safe_reply(update, cameras_list)
            
        except Exception as e:
            logger.error(f"Cameras command error for chat {chat_id}: {str(e)}")
            await self.safe_reply(update, f"Failed to load cameras: {str(e)}")
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages with error recovery"""
        chat_id = update.effective_chat.id
        
        if not self.is_authorized(chat_id):
            await self.safe_reply(update, "Access denied.")
            return
        
        try:
            message_text = update.message.text.lower().strip()
            
            if message_text in ['snapshot', 'snap', 'capture']:
                await self.snapshot_command(update, context)
            elif message_text in ['status', 'check']:
                await self.status_command(update, context)
            elif message_text in ['cameras', 'list']:
                await self.cameras_command(update, context)
            elif message_text in ['help']:
                await self.help_command(update, context)
            else:
                await self.safe_reply(update, "Unknown command. Type /help to see available commands.")
                
        except Exception as e:
            logger.error(f"Text message handler error for chat {chat_id}: {str(e)}")
            await self.safe_reply(update, "Command processing error. Please try again.")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Global error handler to prevent bot crashes"""
        logger.error(f"Global error handler triggered: {context.error}")
        logger.error(traceback.format_exc())
        
        # Try to notify user if possible
        if update and hasattr(update, 'message') and update.message:
            try:
                await update.message.reply_text(
                    "A system error occurred, but the bot is still running. Please try again."
                )
            except Exception:
                pass  # Don't let error handler errors crash the bot
    
    def run(self):
        """Start the bot with comprehensive error handling"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if not self.load_config():
                    print("Failed to load configuration. Check your config files.")
                    logger.error("Configuration load failed")
                    return False
                
                if not self.bot_token:
                    print("Bot token not configured")
                    logger.error("Bot token missing")
                    return False
                
                logger.info(f"Starting bot (attempt {retry_count + 1}/{max_retries})")
                print(f"Bot starting for {len(self.authorized_chat_ids)} authorized chat(s)")
                
                # Create application with error recovery
                app = Application.builder().token(self.bot_token).build()
                
                # Add handlers
                app.add_handler(CommandHandler("start", self.start_command))
                app.add_handler(CommandHandler("help", self.help_command))
                app.add_handler(CommandHandler("snapshot", self.snapshot_command))
                app.add_handler(CommandHandler("status", self.status_command))
                app.add_handler(CommandHandler("cameras", self.cameras_command))
                app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
                
                # Global error handler
                app.add_error_handler(self.error_handler)
                
                logger.info(f"Bot started successfully! Authorized chats: {self.authorized_chat_ids}")
                print(f"Bot is running! Send /snapshot for camera images.")
                
                self.is_running = True
                
                # Run the bot with error recovery
                app.run_polling(
                    allowed_updates=['message'],
                    drop_pending_updates=True,  # Skip old updates on restart
                    stop_signals=None  # Handle shutdown gracefully
                )
                
                # If we get here, the bot stopped normally
                break
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                print("Bot stopped by user")
                break
                
            except Exception as e:
                retry_count += 1
                logger.error(f"Bot error (attempt {retry_count}/{max_retries}): {e}")
                logger.error(traceback.format_exc())
                
                if retry_count < max_retries:
                    print(f"Bot error occurred. Retrying in 10 seconds... (attempt {retry_count}/{max_retries})")
                    time.sleep(10)
                else:
                    print("Max retries reached. Bot shutting down.")
                    logger.error("Max retries reached")
                    return False
        
        logger.info("Bot shutdown complete")
        return True

def main():
    """Main function with system-level error recovery"""
    try:
        bot = CameraSnapshotBot()
        success = bot.run()
        
        if not success:
            print("Bot failed to start properly")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal bot error: {e}")
        logger.error(traceback.format_exc())
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()