#!/usr/bin/env python3
"""
enhanced_every.py - Enhanced Fire & Smoke Detection System with Telegram Bot Integration

This version includes:
- Original fire and smoke detection
- Scheduled camera monitoring via Telegram bot
- Person detection alerts for scheduled cameras
- Comprehensive bot command interface
- Auto-welcome functionality for new users
"""

import threading
import time
import sys
import traceback
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import logging

# Import all existing modules
from adaptive_detection import validate_mac_address
from config_manager import (
    read_credentials, load_google_config, load_telegram_config, load_camera_streams
)
from file_utils import setup_logging, periodic_cleanup
from detection import load_models_safely
from alerting import send_startup_notification
from system_utils import continuous_internet_monitor, system_monitor
from camera_processing import process_camera_real_time

# Import new Telegram bot modules
from telegram_bot_handler import start_telegram_bot
from scheduled_camera_processor import start_scheduled_camera_processor

import config

class EnhancedFireDetectionSystem:
    """Enhanced fire detection system with Telegram bot integration and auto-welcome"""
    
    def __init__(self):
        self.camera_streams = {}
        self.email_config = None
        self.telegram_config = None
        self.camera_threads = []
        self.background_threads = []
        self.is_running = False
        self.system_start_time = time.time()
        
        # Bot and scheduler instances
        self.bot_handler = None
        self.scheduled_processor = None
        
        # Setup enhanced logging
        self.setup_enhanced_logging()
    
    def setup_enhanced_logging(self):
        """Setup comprehensive logging with rotation"""
        try:
            logs_dir = "logs"
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
            
            log_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
            )
            
            # Main system log
            system_log = os.path.join(logs_dir, 'enhanced_fire_detection.log')
            system_handler = RotatingFileHandler(
                system_log, maxBytes=10*1024*1024, backupCount=5
            )
            system_handler.setFormatter(log_formatter)
            system_handler.setLevel(logging.INFO)
            
            # Bot and schedule log
            bot_log = os.path.join(logs_dir, 'telegram_bot.log')
            bot_handler = RotatingFileHandler(
                bot_log, maxBytes=10*1024*1024, backupCount=3
            )
            bot_handler.setFormatter(log_formatter)
            bot_handler.setLevel(logging.INFO)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(log_formatter)
            console_handler.setLevel(logging.INFO)
            
            # Setup loggers
            self.logger = logging.getLogger('EnhancedFireDetectionSystem')
            self.logger.setLevel(logging.INFO)
            self.logger.addHandler(system_handler)
            self.logger.addHandler(console_handler)
            
            # Bot logger
            bot_logger = logging.getLogger('TelegramBot')
            bot_logger.setLevel(logging.INFO)
            bot_logger.addHandler(bot_handler)
            bot_logger.addHandler(console_handler)
            
            self.logger.info("Enhanced logging system initialized")
            
        except Exception as e:
            print(f"Failed to setup enhanced logging: {e}")
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger('EnhancedFireDetectionSystem')
    
    def initialize_system(self):
        """Initialize the enhanced fire detection system"""
        try:
            print("Enhanced Fire & Smoke Detection System with Telegram Bot Starting...")
            print("=" * 80)
            
            self.logger.info("=== ENHANCED SYSTEM INITIALIZATION STARTED ===")
            
            # Step 1: Security validation
            if not validate_mac_address():
                self.logger.error("MAC address validation failed")
                return False
            
            # Step 2: Setup logging
            try:
                setup_logging()
                self.logger.info("Additional logging systems initialized")
            except Exception as e:
                self.logger.warning(f"Additional logging setup warning: {e}")
            
            # Step 3: Load AI models
            print("Loading AI Models...")
            for attempt in range(3):
                try:
                    fire_model, person_model = load_models_safely()
                    if fire_model and person_model:
                        config.FIRE_MODEL = fire_model
                        config.PERSON_MODEL = person_model
                        self.logger.info("AI models loaded successfully")
                        
                        # ADD DEBUG VERIFICATION
                        print(f"DEBUG: Successfully set config.FIRE_MODEL = {config.FIRE_MODEL}")
                        print(f"DEBUG: Successfully set config.PERSON_MODEL = {config.PERSON_MODEL}")
                        print(f"DEBUG: FIRE_MODEL type: {type(config.FIRE_MODEL)}")
                        print(f"DEBUG: PERSON_MODEL type: {type(config.PERSON_MODEL)}")
                        break
                    elif attempt == 2:
                        error_msg = "Failed to load required AI models"
                        self.logger.error(error_msg)
                        return False
                except Exception as e:
                    if attempt == 2:
                        self.logger.error(f"AI model loading failed: {e}")
                        return False
                    time.sleep(5)
            
            # Step 4: Load configurations
            print("Loading Configurations...")
            
            # Email configuration
            try:
                sender_email, sender_password, to_email = load_google_config()
                self.email_config = (sender_email, sender_password, to_email) if all([sender_email, sender_password, to_email]) else None
                self.logger.info(f"Email configuration: {'Loaded' if self.email_config else 'Not configured'}")
            except Exception as e:
                self.logger.warning(f"Email configuration error: {e}")
                self.email_config = None
            
            # Telegram configuration
            try:
                bot_token, chat_ids = load_telegram_config()
                self.telegram_config = (bot_token, chat_ids) if bot_token and chat_ids else None
                if self.telegram_config:
                    chat_count = len(chat_ids) if isinstance(chat_ids, list) else 1
                    self.logger.info(f"Telegram configuration loaded for {chat_count} chat(s)")
                else:
                    self.logger.info("Telegram not configured")
            except Exception as e:
                self.logger.warning(f"Telegram configuration error: {e}")
                self.telegram_config = None
            
            # Camera streams
            try:
                self.camera_streams = load_camera_streams()
                if not self.camera_streams:
                    error_msg = "No camera streams configured. Please check lan.txt file."
                    self.logger.error(error_msg)
                    return False
                self.logger.info(f"Camera streams loaded: {len(self.camera_streams)} cameras")
            except Exception as e:
                error_msg = f"Failed to load camera streams: {e}"
                self.logger.error(error_msg)
                return False
            
            # Send startup notification
            self.send_startup_notification()
            
            self.logger.info("=== ENHANCED SYSTEM INITIALIZATION COMPLETED ===")
            return True
            
        except Exception as e:
            error_msg = f"Critical initialization error: {e}"
            self.logger.error(error_msg)
            print(f"CRITICAL ERROR: {error_msg}")
            return False
    
    def send_startup_notification(self):
        """Send enhanced startup notification with accurate auto-welcome information"""
        try:
            startup_message = f"""ENHANCED FIRE DETECTION SYSTEM READY!

SYSTEM STATUS: OPERATIONAL
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

FIRE DETECTION: 
✅ AI Models: Fire/Smoke (lumi.onnx) + Person/Object (person.onnx)
✅ Real-time monitoring with pixel-level tracking
✅ Adaptive brightness thresholds
✅ Object interference filtering
✅ Active on ALL {len(self.camera_streams)} cameras

TELEGRAM BOT: READY WITH AUTO-WELCOME
{chr(10).join([f"• {name}" for name in list(self.camera_streams.keys())[:5]])}
{'...' if len(self.camera_streams) > 5 else ''}

AVAILABLE COMMANDS:

/start - Welcome and detailed help
/schedule - Interactive camera scheduling  
/list - View all current schedules
/status - See active cameras right now
/cameras - List all available cameras
/stop CamName - Stop specific camera
/help - Show help message
/test - Test bot connection

INSTANT SCHEDULING (Just send these messages):
• "Cam1 00:00-06:00" - Schedule midnight to 6 AM
• "Cam1 all" - Schedule 24/7 monitoring
• "Cam1 off" - Stop monitoring

DETECTION TYPES:
• FIRE ALERTS: Always active (all cameras)
• PERSON ALERTS: Only on scheduled cameras

COMMUNICATION:
• Email: {'Configured' if self.email_config else 'Not configured'}
• Telegram: {'Active - Multiple chats' if self.telegram_config else 'Not configured'}

BOT FEATURES:
✅ Auto-welcome for new users - NO /start required
✅ Send any message to get instant welcome and help
✅ Commands work immediately on first interaction
✅ Casual greetings ("hello", "hi") show quick help
✅ Error handling with informative messages
✅ Connection monitoring and auto-recovery

USER EXPERIENCE:
• First-time users get auto-welcomed with quick help
• Existing users get immediate command processing
• Send "hello" or any text to get started instantly
• All commands work without preliminary setup
• Bot remembers welcomed users for smooth experience

SYSTEM READY! 
• Fire detection is running automatically on all cameras
• Send ANY message to bot to get started (no /start needed)
• Bot will auto-welcome and show available commands
• Example: Send "Cam1 all" to start 24/7 person monitoring

The bot is now truly ready for instant use without requiring /start command!"""

            # Send via existing notification system
            send_startup_notification(
                "ENHANCED SYSTEM READY - AUTO-WELCOME BOT ACTIVE",
                startup_message,
                is_success=True,
                email_config=self.email_config,
                telegram_config=self.telegram_config
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send startup notification: {e}")
    
    def start_background_services(self):
        """Start all background services including bot and scheduler"""
        try:
            print("Starting enhanced background services...")
            self.logger.info("Starting enhanced background services...")
            
            # Original services
            original_services = [
                {
                    'name': 'InternetMonitor',
                    'target': continuous_internet_monitor,
                    'args': (30,),
                    'description': 'Internet monitoring'
                },
                {
                    'name': 'FileCleanup', 
                    'target': periodic_cleanup,
                    'args': (),
                    'description': 'File cleanup service'
                },
                {
                    'name': 'SystemMonitor',
                    'target': system_monitor,
                    'args': (),
                    'description': 'System monitoring'
                }
            ]
            
            # Start original services
            for service in original_services:
                try:
                    thread = threading.Thread(
                        target=self.safe_service_wrapper,
                        args=(service['target'], service['args'], service['name']),
                        daemon=True,
                        name=service['name']
                    )
                    thread.start()
                    self.background_threads.append(thread)
                    print(f"{service['description']} started")
                    time.sleep(1)
                except Exception as e:
                    self.logger.error(f"Failed to start {service['description']}: {e}")
            
            # Start Telegram Bot with Auto-Welcome
            try:
                print("Starting Telegram Bot with Auto-Welcome...")
                self.bot_handler = start_telegram_bot()
                print("Telegram Bot with auto-welcome started successfully")
                self.logger.info("Telegram Bot with auto-welcome started successfully")
                time.sleep(2)
            except Exception as e:
                self.logger.error(f"Failed to start Telegram Bot: {e}")
                print(f"Warning: Telegram Bot failed to start: {e}")
            
            # Start Scheduled Camera Processor
            try:
                print("Starting Scheduled Camera Processor...")
                self.scheduled_processor = start_scheduled_camera_processor(
                    self.email_config, 
                    self.telegram_config
                )
                print("Scheduled Camera Processor started successfully")
                self.logger.info("Scheduled Camera Processor started successfully")
                time.sleep(2)
            except Exception as e:
                self.logger.error(f"Failed to start Scheduled Camera Processor: {e}")
                print(f"Warning: Scheduled Camera Processor failed to start: {e}")
            
            print("Enhanced background services startup completed")
            self.logger.info(f"Enhanced services started: {len(self.background_threads)} + Bot + Scheduler")
            return True
            
        except Exception as e:
            self.logger.error(f"Enhanced background services startup failed: {e}")
            return False
    
    def safe_service_wrapper(self, target_function, args, service_name):
        """Wrapper for background services with error recovery"""
        max_restarts = 5
        restart_count = 0
        
        while restart_count < max_restarts:
            try:
                self.logger.info(f"Starting {service_name} service (attempt {restart_count + 1})")
                target_function(*args)
                
            except KeyboardInterrupt:
                self.logger.info(f"{service_name} service stopped by user")
                break
                
            except Exception as e:
                restart_count += 1
                self.logger.error(f"{service_name} service error (attempt {restart_count}): {e}")
                
                if restart_count < max_restarts:
                    wait_time = min(30 * restart_count, 300)
                    self.logger.info(f"{service_name} service restarting in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"{service_name} service failed permanently")
                    break
    
    def start_fire_detection_cameras(self):
        """Start original fire detection for all cameras"""
        try:
            print(f"Starting fire detection for {len(self.camera_streams)} cameras...")
            
            for camera_name, camera_url in self.camera_streams.items():
                try:
                    print(f"Starting fire detection for camera: {camera_name}")
                    
                    camera_thread = threading.Thread(
                        target=self.safe_camera_wrapper,
                        args=(camera_name, camera_url),
                        daemon=True,
                        name=f"FireDetection-{camera_name}"
                    )
                    camera_thread.start()
                    self.camera_threads.append(camera_thread)
                    
                    time.sleep(2)
                    
                except Exception as e:
                    self.logger.error(f"Failed to start fire detection for {camera_name}: {e}")
            
            active_cameras = len(self.camera_threads)
            print(f"Fire detection started: {active_cameras}/{len(self.camera_streams)} cameras")
            
            return active_cameras > 0
            
        except Exception as e:
            self.logger.error(f"Fire detection startup failed: {e}")
            return False
    
    def safe_camera_wrapper(self, camera_name, camera_url):
        """Wrapper for camera processing with error recovery"""
        max_restarts = 10
        restart_count = 0
        
        while restart_count < max_restarts:
            try:
                self.logger.info(f"Starting fire detection for {camera_name} (attempt {restart_count + 1})")
                
                # Original fire detection processing
                process_camera_real_time(camera_name, camera_url, self.email_config, self.telegram_config)
                break
                
            except KeyboardInterrupt:
                self.logger.info(f"Fire detection for {camera_name} stopped by user")
                break
                
            except Exception as e:
                restart_count += 1
                self.logger.error(f"Fire detection {camera_name} error (attempt {restart_count}): {e}")
                
                if restart_count < max_restarts:
                    wait_time = 30
                    self.logger.info(f"Fire detection {camera_name} restarting in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Fire detection {camera_name} failed permanently")
                    break
    
    def run(self):
        """Main system run method with enhanced functionality"""
        try:
            # Initialize all system components
            if not self.initialize_system():
                self.logger.error("Enhanced system initialization failed")
                return False
            
            # Start background services (including bot and scheduler)
            if not self.start_background_services():
                self.logger.warning("Some enhanced background services failed to start")
            
            # Start fire detection cameras
            print("Starting fire detection on all cameras...")
            if not self.start_fire_detection_cameras():
                self.logger.warning("Fire detection cameras failed to start")
            
            self.is_running = True
            
            print("\n" + "=" * 80)
            print("ENHANCED FIRE & SMOKE DETECTION SYSTEM WITH AUTO-WELCOME BOT IS ACTIVE")
            print("=" * 80)
            print("System Status:")
            print(f"  • AI Models: Fire/Smoke + Person detection loaded")
            print(f"  • Background Services: {len(self.background_threads)} running")
            print(f"  • Fire Detection: {len(self.camera_threads)} cameras active")
            print(f"  • Telegram Bot: {'Active with Auto-Welcome' if self.bot_handler else 'Failed'}")
            print(f"  • Schedule Processor: {'Active' if self.scheduled_processor else 'Failed'}")
            print(f"  • Alert Systems: Email {'✓' if self.email_config else '✗'} | Telegram {'✓' if self.telegram_config else '✗'}")
            
            if self.telegram_config:
                bot_token, chat_ids = self.telegram_config
                if isinstance(chat_ids, list):
                    print(f"  • Telegram Recipients: {len(chat_ids)} chat(s)")
                    print(f"  • Chat IDs: {', '.join(map(str, chat_ids))}")
                else:
                    print(f"  • Telegram Recipients: 1 chat ({chat_ids})")
            
            print(f"  • Available Cameras: {len(self.camera_streams)}")
            for name in list(self.camera_streams.keys())[:3]:
                print(f"    - {name}")
            if len(self.camera_streams) > 3:
                print(f"    - ... and {len(self.camera_streams) - 3} more")
            
            print("=" * 80)
            print("TELEGRAM BOT - AUTO-WELCOME FEATURES:")
            print("  ✅ New users auto-welcomed (no /start required)")
            print("  ✅ Send any message to get instant help")
            print("  ✅ Casual greetings ('hello', 'hi') show quick help")
            print("  ✅ Commands work immediately on first interaction")
            print("  ✅ Error handling with informative messages")
            print("  ✅ Connection monitoring and recovery")
            print("")
            print("AVAILABLE COMMANDS:")
            print("  /start - Welcome and help")
            print("  /schedule - Interactive camera scheduling")
            print("  /list - View all schedules")
            print("  /status - Current active cameras")
            print("  /cameras - Available cameras")
            print("  /stop CamName - Stop specific camera")
            print("  /test - Test bot connection")
            print("")
            print("QUICK SCHEDULING:")
            print("  Send: 'Cam1 00:00-06:00' (midnight to 6 AM)")
            print("  Send: 'Cam2 all' (24/7 monitoring)")
            print("  Send: 'Cam1 off' (stop monitoring)")
            print("=" * 80)
            print("SYSTEM STATUS:")
            print("  FIRE DETECTION: Active on all cameras automatically")
            print("  PERSON DETECTION: Use Telegram bot to schedule cameras")
            print("  BOT AUTO-WELCOME: Send any message to get started")
            print("Press Ctrl+C to stop.")
            print("=" * 80)
            
            # Main system loop
            while self.is_running:
                try:
                    time.sleep(10)
                    
                except KeyboardInterrupt:
                    print("\nShutdown signal received...")
                    self.logger.info("Shutdown signal received")
                    break
                    
        except Exception as e:
            self.logger.error(f"Critical system error in main loop: {e}")
            self.logger.error(traceback.format_exc())
            print(f"CRITICAL ERROR: {e}")
            return False
            
        finally:
            self.shutdown_system()
        
        return True
    
    def shutdown_system(self):
        """Graceful system shutdown with notifications"""
        try:
            print("Shutting down Enhanced Fire & Smoke Detection System...")
            self.logger.info("=== ENHANCED SYSTEM SHUTDOWN INITIATED ===")
            
            self.is_running = False
            
            # Stop scheduled processor
            if self.scheduled_processor:
                try:
                    self.scheduled_processor.stop_all_monitoring()
                    print("Scheduled camera monitoring stopped")
                except Exception as e:
                    self.logger.error(f"Error stopping scheduled processor: {e}")
            
            # Send shutdown notification
            try:
                uptime_hours = (time.time() - self.system_start_time) / 3600
                shutdown_message = f"Enhanced Fire Detection System shutdown at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                shutdown_message += f"Uptime: {uptime_hours:.1f} hours\n"
                shutdown_message += f"Bot with auto-welcome and scheduling services stopped"
                
                # Send via Telegram if available
                if self.telegram_config:
                    try:
                        send_startup_notification(
                            "ENHANCED SYSTEM SHUTDOWN",
                            shutdown_message,
                            is_success=True,
                            force=True,
                            email_config=self.email_config,
                            telegram_config=self.telegram_config
                        )
                        print("Shutdown notification sent")
                    except Exception as e:
                        self.logger.error(f"Failed to send shutdown notification: {e}")
                        
            except Exception as e:
                print(f"Could not send shutdown notification: {e}")
                self.logger.error(f"Shutdown notification failed: {e}")
            
            self.logger.info("=== ENHANCED SYSTEM SHUTDOWN COMPLETE ===")
            print("Enhanced system shutdown complete")
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
            self.logger.error(f"Shutdown error: {e}")

def main():
    """Main function with system-level error recovery"""
    system = None
    
    try:
        system = EnhancedFireDetectionSystem()
        success = system.run()
        
        if not success:
            print("Enhanced system failed to start properly")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nEnhanced system shutdown requested by user")
        if system:
            system.logger.info("Enhanced system shutdown requested by user")
    except Exception as e:
        error_msg = f"Fatal enhanced system error: {e}"
        print(f"FATAL ERROR: {error_msg}")
        if system:
            system.logger.error(error_msg)
            system.logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()