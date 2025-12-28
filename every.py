#!/usr/bin/env python3
"""
every.py - Robust Fire & Smoke Detection System Main Entry Point

Enhanced version with comprehensive error handling, recovery, and resilience features.
System continues running even when individual components fail.
"""

import threading
import time
import sys
import traceback
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import logging

# Import all our modular components
from adaptive_detection import validate_mac_address
from config_manager import (
    read_credentials, load_google_config, load_telegram_config, load_camera_streams
)
from file_utils import setup_logging, periodic_cleanup
from detection import load_models_safely
from alerting import send_startup_notification
from system_utils import continuous_internet_monitor, system_monitor
from camera_processing import process_camera_real_time
from telegram_helper import (
    send_telegram_message_multiple, is_multiple_chat_config, 
    format_telegram_config_for_legacy_compatibility
)
import config

class RobustFireDetectionSystem:
    """Main fire detection system with comprehensive error handling"""
    
    def __init__(self):
        self.camera_streams = {}
        self.email_config = None
        self.telegram_config = None
        self.camera_threads = []
        self.background_threads = []
        self.is_running = False
        self.system_start_time = time.time()
        self.error_counts = {'camera': 0, 'config': 0, 'system': 0}
        self.last_health_check = time.time()
        self.restart_attempts = 0
        self.max_restart_attempts = 3
        
        # Setup enhanced logging
        self.setup_enhanced_logging()
    
    def setup_enhanced_logging(self):
        """Setup comprehensive logging with rotation"""
        try:
            # Create logs directory if it doesn't exist
            logs_dir = "logs"
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
            
            # Setup main system logger
            log_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
            )
            
            # Main system log
            system_log = os.path.join(logs_dir, 'fire_detection_system.log')
            system_handler = RotatingFileHandler(
                system_log, maxBytes=20*1024*1024, backupCount=5
            )
            system_handler.setFormatter(log_formatter)
            system_handler.setLevel(logging.INFO)
            
            # Error log
            error_log = os.path.join(logs_dir, 'system_errors.log')
            error_handler = RotatingFileHandler(
                error_log, maxBytes=10*1024*1024, backupCount=3
            )
            error_handler.setFormatter(log_formatter)
            error_handler.setLevel(logging.ERROR)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(log_formatter)
            console_handler.setLevel(logging.INFO)
            
            # Setup root logger
            self.logger = logging.getLogger('FireDetectionSystem')
            self.logger.setLevel(logging.INFO)
            self.logger.addHandler(system_handler)
            self.logger.addHandler(error_handler)
            self.logger.addHandler(console_handler)
            
            self.logger.info("Enhanced logging system initialized")
            
        except Exception as e:
            print(f"Failed to setup enhanced logging: {e}")
            # Fallback to basic logging
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger('FireDetectionSystem')
    
    def safe_telegram_notification(self, message, is_error=False):
        """Safely send telegram notifications without crashing system"""
        try:
            if self.telegram_config and is_multiple_chat_config(self.telegram_config):
                bot_token, chat_ids = self.telegram_config
                prefix = "ERROR" if is_error else "INFO"
                send_telegram_message_multiple(
                    bot_token, chat_ids,
                    f"*{prefix}*\n\n{message}",
                    silent_fail=True
                )
        except Exception as e:
            self.logger.error(f"Failed to send telegram notification: {e}")
    
    def initialize_system(self):
        """Initialize the fire detection system with comprehensive error handling"""
        try:
            print("Fire & Smoke Detection System - Robust Version Starting...")
            print("=" * 70)
            
            self.logger.info("=== SYSTEM INITIALIZATION STARTED ===")
            
            # Step 1: Security validation with retry
            max_security_retries = 3
            for attempt in range(max_security_retries):
                try:
                    if validate_mac_address():
                        self.logger.info("MAC address validation successful")
                        break
                    else:
                        if attempt == max_security_retries - 1:
                            self.logger.error("MAC address validation failed after all retries")
                            return False
                        time.sleep(2)
                except Exception as e:
                    self.logger.error(f"Security validation error (attempt {attempt + 1}): {e}")
                    if attempt == max_security_retries - 1:
                        return False
                    time.sleep(2)
            
            # Step 2: Setup additional logging (already done in __init__)
            try:
                setup_logging()  # Original logging setup
                self.logger.info("Additional logging systems initialized")
            except Exception as e:
                self.logger.warning(f"Additional logging setup warning: {e}")
            
            # Step 3: Load AI models with multiple attempts
            print("Loading AI Models...")
            self.logger.info("Loading AI models...")
            
            for attempt in range(3):
                try:
                    fire_model, person_model = load_models_safely()
                    if fire_model and person_model:
                        config.FIRE_MODEL = fire_model
                        config.PERSON_MODEL = person_model
                        self.logger.info("AI models loaded successfully")
                        break
                    elif attempt == 2:
                        error_msg = "Failed to load required AI models after all attempts"
                        self.logger.error(error_msg)
                        self.safe_telegram_notification(error_msg, is_error=True)
                        return False
                    else:
                        self.logger.warning(f"Model loading attempt {attempt + 1} failed, retrying...")
                        time.sleep(5)
                except Exception as e:
                    if attempt == 2:
                        error_msg = f"AI model loading failed: {e}"
                        self.logger.error(error_msg)
                        self.safe_telegram_notification(error_msg, is_error=True)
                        return False
                    else:
                        self.logger.warning(f"Model loading exception (attempt {attempt + 1}): {e}")
                        time.sleep(5)
            
            # Step 4: Load configurations with error recovery
            print("Loading Configurations...")
            self.logger.info("Loading system configurations...")
            
            try:
                # Load email configuration with error handling
                try:
                    sender_email, sender_password, to_email = load_google_config()
                    self.email_config = (sender_email, sender_password, to_email) if all([sender_email, sender_password, to_email]) else None
                    self.logger.info(f"Email configuration: {'Loaded' if self.email_config else 'Not configured'}")
                except Exception as e:
                    self.logger.warning(f"Email configuration error: {e}")
                    self.email_config = None
                
                # Load Telegram configuration with error handling
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
                
                # Load camera streams with error handling
                try:
                    self.camera_streams = load_camera_streams()
                    if self.camera_streams:
                        self.logger.info(f"Camera streams loaded: {len(self.camera_streams)} cameras")
                    else:
                        error_msg = "No camera streams configured. Please check lan.txt file."
                        self.logger.error(error_msg)
                        self.safe_telegram_notification(error_msg, is_error=True)
                        return False
                except Exception as e:
                    error_msg = f"Failed to load camera streams: {e}"
                    self.logger.error(error_msg)
                    self.safe_telegram_notification(error_msg, is_error=True)
                    return False
                    
            except Exception as e:
                error_msg = f"Configuration loading failed: {e}"
                self.logger.error(error_msg)
                self.safe_telegram_notification(error_msg, is_error=True)
                return False
            
            # Log successful initialization
            print("System initialization complete!")
            print(f"Email alerts: {'Enabled' if self.email_config else 'Disabled'}")
            
            if self.telegram_config:
                bot_token, chat_ids = self.telegram_config
                if isinstance(chat_ids, list):
                    print(f"Telegram alerts: Enabled for {len(chat_ids)} chat(s)")
                    print(f"   Chat IDs: {', '.join(map(str, chat_ids))}")
                else:
                    print(f"Telegram alerts: Enabled for 1 chat")
            else:
                print("Telegram alerts: Disabled")
            
            print(f"Cameras configured: {len(self.camera_streams)}")
            
            # Send successful startup notification
            self.send_startup_notification()
            
            self.logger.info("=== SYSTEM INITIALIZATION COMPLETED SUCCESSFULLY ===")
            return True
            
        except Exception as e:
            error_msg = f"Critical initialization error: {e}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            print(f"CRITICAL ERROR: {error_msg}")
            return False
    
    def send_startup_notification(self):
        """Send comprehensive startup notification"""
        try:
            chat_info = "- Telegram: Not configured"
            if self.telegram_config:
                bot_token, chat_ids = self.telegram_config
                if isinstance(chat_ids, list):
                    chat_info = f"- Telegram: {len(chat_ids)} chat recipients configured"
                else:
                    chat_info = "- Telegram: 1 chat recipient configured"

            startup_message = f"""System successfully initialized with enhanced reliability:

AI Models: Loaded successfully
- Fire/Smoke Model: lumi.onnx
- Person/Object Model: person.onnx

Communication:
- Email: {'Configured' if self.email_config else 'Not configured'}
{chat_info}

Camera Streams: {len(self.camera_streams)} configured
{chr(10).join([f"- {name}: {url[:50]}..." for name, url in list(self.camera_streams.items())[:3]])}
{'...' if len(self.camera_streams) > 3 else ''}

Enhanced Features:
- Pixel-level fire tracking
- Orange clothing detection  
- Same-pixel suppression
- Adaptive brightness thresholds
- Object interference filtering
- Internet connectivity monitoring
- Automatic file cleanup
- Multiple Telegram chat support
- Comprehensive error recovery
- Auto-restart capabilities
- Enhanced logging system

System is now monitoring for fire and smoke detection with robust error handling."""

            # Send to all configured Telegram chats
            if self.telegram_config and is_multiple_chat_config(self.telegram_config):
                bot_token, chat_ids = self.telegram_config
                send_telegram_message_multiple(
                    bot_token, chat_ids,
                    f"SYSTEM STARTUP SUCCESS\n\n{startup_message}"
                )
            
            # Also send via legacy notification system for email
            send_startup_notification(
                "SYSTEM STARTUP SUCCESS",
                startup_message,
                is_success=True,
                email_config=self.email_config,
                telegram_config=format_telegram_config_for_legacy_compatibility(*self.telegram_config) if self.telegram_config else None
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send startup notification: {e}")
    
    def start_background_services(self):
        """Start all background monitoring services with error recovery"""
        try:
            print("Starting background services...")
            self.logger.info("Starting background services...")
            
            services_to_start = [
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
            
            for service in services_to_start:
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
                    self.logger.info(f"{service['description']} started successfully")
                    time.sleep(1)  # Small delay between service starts
                    
                except Exception as e:
                    self.logger.error(f"Failed to start {service['description']}: {e}")
                    print(f"Warning: Failed to start {service['description']}")
            
            print("Background services startup completed")
            self.logger.info(f"Background services started: {len(self.background_threads)} services running")
            return True
            
        except Exception as e:
            self.logger.error(f"Background services startup failed: {e}")
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
                    wait_time = min(30 * restart_count, 300)  # Max 5 minutes
                    self.logger.info(f"{service_name} service restarting in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"{service_name} service failed permanently after {max_restarts} attempts")
                    self.safe_telegram_notification(
                        f"{service_name} service failed permanently and will not restart",
                        is_error=True
                    )
                    break
    
    def start_camera_processing(self):
        """Start camera processing threads with comprehensive error handling"""
        try:
            print(f"Starting camera processing for {len(self.camera_streams)} cameras...")
            self.logger.info(f"Starting camera processing for {len(self.camera_streams)} cameras")
            
            for camera_name, camera_url in self.camera_streams.items():
                try:
                    print(f"Starting processing thread for camera: {camera_name}")
                    
                    camera_thread = threading.Thread(
                        target=self.safe_camera_wrapper,
                        args=(camera_name, camera_url),
                        daemon=True,
                        name=f"Camera-{camera_name}"
                    )
                    camera_thread.start()
                    self.camera_threads.append(camera_thread)
                    
                    self.logger.info(f"Camera thread started for {camera_name}")
                    time.sleep(2)  # Delay between camera starts
                    
                except Exception as e:
                    self.logger.error(f"Failed to start camera thread for {camera_name}: {e}")
                    print(f"Warning: Failed to start camera {camera_name}")
            
            active_cameras = len(self.camera_threads)
            total_cameras = len(self.camera_streams)
            
            print(f"Camera processing started: {active_cameras}/{total_cameras} cameras active")
            self.logger.info(f"Camera processing initialization complete: {active_cameras}/{total_cameras} cameras")
            
            if active_cameras < total_cameras:
                warning_msg = f"Warning: Only {active_cameras}/{total_cameras} camera threads started successfully"
                print(warning_msg)
                self.logger.warning(warning_msg)
                self.safe_telegram_notification(warning_msg, is_error=True)
            
            return active_cameras > 0  # Success if at least one camera started
            
        except Exception as e:
            error_msg = f"Camera processing startup failed: {e}"
            self.logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return False
    
    def safe_camera_wrapper(self, camera_name, camera_url):
        """Wrapper for camera processing with error recovery"""
        max_restarts = 10  # More restarts for cameras
        restart_count = 0
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while restart_count < max_restarts:
            try:
                self.logger.info(f"Starting camera processing for {camera_name} (attempt {restart_count + 1})")
                
                # Call the original camera processing function
                process_camera_real_time(camera_name, camera_url, self.email_config, self.telegram_config)
                
                # If we reach here, the camera processing ended normally
                self.logger.info(f"Camera {camera_name} processing ended normally")
                break
                
            except KeyboardInterrupt:
                self.logger.info(f"Camera {camera_name} stopped by user")
                break
                
            except Exception as e:
                restart_count += 1
                consecutive_failures += 1
                
                self.logger.error(f"Camera {camera_name} error (attempt {restart_count}): {e}")
                
                # If too many consecutive failures, increase wait time
                if consecutive_failures >= max_consecutive_failures:
                    wait_time = min(60 * consecutive_failures, 600)  # Max 10 minutes
                    self.logger.warning(f"Camera {camera_name} has {consecutive_failures} consecutive failures, waiting {wait_time} seconds")
                else:
                    wait_time = 30
                
                if restart_count < max_restarts:
                    self.logger.info(f"Camera {camera_name} restarting in {wait_time} seconds...")
                    time.sleep(wait_time)
                    
                    # Reset consecutive failures if we've waited a long time
                    if wait_time >= 300:
                        consecutive_failures = 0
                else:
                    error_msg = f"Camera {camera_name} failed permanently after {max_restarts} attempts"
                    self.logger.error(error_msg)
                    self.safe_telegram_notification(error_msg, is_error=True)
                    break
    
    def monitor_system_health(self):
        """Enhanced system health monitoring"""
        try:
            while self.is_running:
                current_time = time.time()
                
                # Health check every 5 minutes
                if current_time - self.last_health_check > 300:
                    try:
                        self.perform_health_check()
                        self.last_health_check = current_time
                    except Exception as e:
                        self.logger.error(f"Health check error: {e}")
                
                time.sleep(30)  # Check every 30 seconds
                
        except Exception as e:
            self.logger.error(f"System health monitoring error: {e}")
    
    def perform_health_check(self):
        """Perform comprehensive system health check"""
        try:
            # Check camera threads
            active_cameras = sum(1 for thread in self.camera_threads if thread.is_alive())
            total_cameras = len(self.camera_streams)
            
            if active_cameras < total_cameras:
                warning_msg = f"Camera Health Alert: Only {active_cameras}/{total_cameras} camera threads active"
                self.logger.warning(warning_msg)
                print(warning_msg)
                self.safe_telegram_notification(warning_msg, is_error=True)
            
            # Check background services
            active_services = sum(1 for thread in self.background_threads if thread.is_alive())
            total_services = len(self.background_threads)
            
            if active_services < total_services:
                warning_msg = f"Service Health Alert: Only {active_services}/{total_services} background services active"
                self.logger.warning(warning_msg)
                print(warning_msg)
                self.safe_telegram_notification(warning_msg, is_error=True)
            
            # Log system uptime
            uptime_hours = (time.time() - self.system_start_time) / 3600
            self.logger.info(f"System health check: {uptime_hours:.1f}h uptime, {active_cameras}/{total_cameras} cameras, {active_services}/{total_services} services")
            
            # Periodic status report (every hour)
            if uptime_hours > 0 and int(uptime_hours) % 6 == 0:  # Every 6 hours
                status_msg = f"System Status Report - Uptime: {uptime_hours:.1f}h, Cameras: {active_cameras}/{total_cameras}, Services: {active_services}/{total_services}"
                self.safe_telegram_notification(status_msg)
                
        except Exception as e:
            self.logger.error(f"Health check performance error: {e}")
    
    def run(self):
        """Main system run method with comprehensive error handling"""
        try:
            # Initialize all system components
            if not self.initialize_system():
                self.logger.error("System initialization failed")
                return False
            
            # Start background monitoring services
            if not self.start_background_services():
                self.logger.warning("Some background services failed to start")
            
            # Start camera processing
            if not self.start_camera_processing():
                self.logger.error("Camera processing failed to start")
                return False
            
            self.is_running = True
            
            print("\n" + "=" * 70)
            print("FIRE & SMOKE DETECTION SYSTEM IS NOW ACTIVE")
            print("=" * 70)
            print("System Status:")
            print(f"  • AI Models: Loaded and ready")
            print(f"  • Background Services: {len(self.background_threads)} running")
            print(f"  • Camera Threads: {len(self.camera_threads)} active")
            print(f"  • Alert Systems: Email {'✓' if self.email_config else '✗'} | Telegram {'✓' if self.telegram_config else '✗'}")
            
            if self.telegram_config:
                bot_token, chat_ids = self.telegram_config
                if isinstance(chat_ids, list):
                    print(f"  • Telegram Recipients: {len(chat_ids)} chat(s)")
                else:
                    print(f"  • Telegram Recipients: 1 chat")
            
            print("=" * 70)
            print("Real-time monitoring active with error recovery. Press Ctrl+C to stop.")
            print("=" * 70)
            
            # Start health monitoring in separate thread
            health_thread = threading.Thread(
                target=self.monitor_system_health,
                daemon=True,
                name="HealthMonitor"
            )
            health_thread.start()
            
            # Main system loop with error recovery
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
            print("Shutting down Fire & Smoke Detection System...")
            self.logger.info("=== SYSTEM SHUTDOWN INITIATED ===")
            
            self.is_running = False
            
            # Send shutdown notification
            try:
                shutdown_message = f"Fire Detection System shut down at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nUptime: {(time.time() - self.system_start_time)/3600:.1f} hours"
                
                if self.telegram_config and is_multiple_chat_config(self.telegram_config):
                    bot_token, chat_ids = self.telegram_config
                    print("Sending shutdown notification to Telegram...")
                    result = send_telegram_message_multiple(
                        bot_token, chat_ids,
                        f"SYSTEM SHUTDOWN\n\n{shutdown_message}",
                        silent_fail=True
                    )
                    if result['successful_sends'] > 0:
                        print(f"Shutdown notification sent to {result['successful_sends']}/{result['total_chats']} chat(s)")
                
                # Email notification
                if self.email_config:
                    try:
                        send_startup_notification(
                            "SYSTEM SHUTDOWN",
                            shutdown_message,
                            is_success=True,
                            force=True,
                            email_config=self.email_config,
                            telegram_config=format_telegram_config_for_legacy_compatibility(*self.telegram_config) if self.telegram_config else None
                        )
                    except Exception as e:
                        self.logger.error(f"Failed to send email shutdown notification: {e}")
                        
            except Exception as e:
                print(f"Could not send shutdown notification: {e}")
                self.logger.error(f"Shutdown notification failed: {e}")
            
            self.logger.info("=== SYSTEM SHUTDOWN COMPLETE ===")
            print("System shutdown complete")
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
            self.logger.error(f"Shutdown error: {e}")

def main():
    """Main function with system-level error recovery"""
    system = None
    
    try:
        system = RobustFireDetectionSystem()
        success = system.run()
        
        if not success:
            print("System failed to start properly")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nSystem shutdown requested by user")
        if system:
            system.logger.info("System shutdown requested by user")
    except Exception as e:
        error_msg = f"Fatal system error: {e}"
        print(f"FATAL ERROR: {error_msg}")
        if system:
            system.logger.error(error_msg)
            system.logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()