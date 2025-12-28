# scheduled_camera_processor.py - FIXED Camera Schedule Manager with Proper Thread Control
import os
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from camera_processing import process_camera_real_time
from config import BASE_DIR
from telegram_bot_handler import bot_handler

class ScheduledCameraProcessor:
    def __init__(self, email_config=None, telegram_config=None):
        self.email_config = email_config
        self.telegram_config = telegram_config
        self.running_cameras = {}  # Track running camera threads
        self.camera_schedules = {}
        self.last_schedule_check = 0
        self.schedule_check_interval = 60  # Check every minute
        self.is_running = False
        
        # CRITICAL FIX: Enhanced thread control mechanism
        self.camera_stop_flags = {}  # Control flags for each camera thread
        self.camera_thread_locks = {}  # Locks for thread-safe operations
        self.detector_cleanup_required = set()  # Track cameras needing detector cleanup
        
        # Files for storing schedules
        self.camera_schedule_file = os.path.join(BASE_DIR, "camera_schedule.json")
        self.active_schedules_file = os.path.join(BASE_DIR, "active_schedules.json")
        
        print("FIXED Scheduled Camera Processor initialized with enhanced thread control")
        logging.info("FIXED Scheduled Camera Processor initialized with enhanced thread control")
    
    def load_camera_schedules(self):
        """Load camera schedules from JSON file"""
        if os.path.exists(self.camera_schedule_file):
            try:
                with open(self.camera_schedule_file, 'r') as f:
                    schedules = json.load(f)
                    print(f"Loaded {len(schedules)} camera schedules")
                    logging.info(f"Loaded {len(schedules)} camera schedules")
                    return schedules
            except Exception as e:
                logging.error(f"Error loading camera schedules: {e}")
                print(f"Error loading camera schedules: {e}")
        return {}
    
    def save_active_schedules(self, active_schedules):
        """Save currently active schedules with enhanced error handling"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.active_schedules_file), exist_ok=True)
            
            # Add metadata
            schedule_data = {
                'last_updated': datetime.now().isoformat(),
                'total_active': len(active_schedules),
                'schedules': active_schedules
            }
            
            with open(self.active_schedules_file, 'w') as f:
                json.dump(schedule_data, f, indent=2)
            
            print(f"Active schedules saved to {self.active_schedules_file}")
            return True
        except Exception as e:
            logging.error(f"Error saving active schedules: {e}")
            print(f"Error saving active schedules: {e}")
            return False
    
    def is_time_in_range(self, start_time_str, end_time_str):
        """Check if current time is within the specified range"""
        current_time = datetime.now().time()
        
        try:
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.strptime(end_time_str, "%H:%M").time()
        except ValueError as e:
            logging.error(f"Invalid time format: {e}")
            return False
        
        if start_time <= end_time:
            # Same day range (e.g., 09:00-17:00)
            return start_time <= current_time <= end_time
        else:
            # Overnight range (e.g., 22:00-06:00)
            return current_time >= start_time or current_time <= end_time
    
# Fixed should_camera_be_active method for scheduled_camera_processor.py

    def should_camera_be_active(self, camera_name, schedule):
        """Determine if a camera should be actively monitoring - FIXED for multiple schedules"""
        if not schedule.get('enabled', True):
            return False
        
        # Handle 24/7 schedule
        if schedule.get('time_range') == 'all':
            return True
        
        # Handle multiple time ranges (NEW FORMAT)
        if schedule.get('type') == 'multiple_ranges' and 'schedules' in schedule:
            current_time = datetime.now().time()
            
            for time_sched in schedule['schedules']:
                start_time_str = time_sched.get('start_time')
                end_time_str = time_sched.get('end_time')
                
                if start_time_str and end_time_str:
                    if self.is_time_in_range(start_time_str, end_time_str):
                        print(f"Camera {camera_name} should be active - time match: {start_time_str}-{end_time_str}")
                        return True
            
            print(f"Camera {camera_name} not in any scheduled time range")
            return False
        
        # Handle legacy single time range format
        start_time = schedule.get('start_time')
        end_time = schedule.get('end_time')
        
        if not start_time or not end_time:
            return False
        
        return self.is_time_in_range(start_time, end_time)
    
    def get_camera_url_from_config(self, camera_name):
        """Get camera URL from lan.txt configuration"""
        lan_file = os.path.join(BASE_DIR, "lan.txt")
        
        if not os.path.exists(lan_file):
            return None
        
        try:
            with open(lan_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        name, url = line.split('=', 1)
                        if name.strip() == camera_name:
                            return url.strip()
        except Exception as e:
            logging.error(f"Error reading camera configuration: {e}")
        
        return None
    
    def cleanup_camera_detector(self, camera_name):
        """CRITICAL FIX: Clean up detector state for a camera"""
        try:
            # Clear person detector state
            from person_detection import clear_camera_detector
            clear_camera_detector(camera_name)
            
            # Clear from cleanup tracking
            self.detector_cleanup_required.discard(camera_name)
            
            print(f"Detector cleanup completed for {camera_name}")
            logging.info(f"Detector cleanup completed for {camera_name}")
            
        except ImportError:
            print(f"Warning: Could not import detector cleanup for {camera_name}")
        except Exception as e:
            print(f"Error during detector cleanup for {camera_name}: {e}")
            logging.error(f"Error during detector cleanup for {camera_name}: {e}")
    
    def set_camera_stop_flag(self, camera_name, should_stop=True):
        """CRITICAL FIX: Thread-safe stop flag management"""
        # Create lock if doesn't exist
        if camera_name not in self.camera_thread_locks:
            self.camera_thread_locks[camera_name] = threading.Lock()
        
        with self.camera_thread_locks[camera_name]:
            self.camera_stop_flags[camera_name] = should_stop
            
        print(f"Set stop flag for {camera_name}: {should_stop}")
        logging.info(f"Set stop flag for {camera_name}: {should_stop}")
    
    def should_camera_stop(self, camera_name):
        """CRITICAL FIX: Thread-safe stop flag check"""
        if camera_name not in self.camera_thread_locks:
            return self.camera_stop_flags.get(camera_name, False)
        
        with self.camera_thread_locks[camera_name]:
            return self.camera_stop_flags.get(camera_name, False)
    
    def ensure_models_loaded_in_thread(self):
        """CRITICAL FIX: Ensure models are loaded in the current thread"""
        import config
        
        print(f"Checking models in thread: {threading.current_thread().name}")
        
        # Always try to reload models in scheduler threads
        try:
            from detection import load_models_safely
            fire_model, person_model = load_models_safely()
            
            if fire_model:
                config.FIRE_MODEL = fire_model
                print(f"FIRE_MODEL loaded in scheduler thread: {type(fire_model)}")
            else:
                print("WARNING: Failed to load FIRE_MODEL in scheduler thread")
            
            if person_model:
                config.PERSON_MODEL = person_model
                print(f"PERSON_MODEL loaded in scheduler thread: {type(person_model)}")
            else:
                print("WARNING: Failed to load PERSON_MODEL in scheduler thread")
                return False
            
            # Verify models are accessible
            if hasattr(person_model, 'predict') or hasattr(person_model, 'forward'):
                print("Person model verification: OK")
                return True
            else:
                print("Person model verification: FAILED - model not callable")
                return False
                
        except Exception as e:
            print(f"CRITICAL: Failed to load models in scheduler thread: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start_camera_monitoring(self, camera_name, camera_url, schedule):
        """CRITICAL FIX: Enhanced camera monitoring startup with better model handling"""
        if camera_name in self.running_cameras:
            print(f"Camera {camera_name} is already running - stopping first")
            self.stop_camera_monitoring(camera_name)
            time.sleep(3)  # Wait for cleanup
        
        print(f"Starting enhanced monitoring for {camera_name}")
        logging.info(f"Starting enhanced monitoring for {camera_name} with person detection")
        
        # CRITICAL FIX: Clean detector state before starting
        self.cleanup_camera_detector(camera_name)
        
        # CRITICAL FIX: Clear and set stop flag
        self.set_camera_stop_flag(camera_name, False)
        
        # Create a wrapper function with enhanced error handling
        def camera_wrapper():
            try:
                print(f"Camera thread started for {camera_name}: {threading.current_thread().name}")
                
                # CRITICAL FIX: Force model reload in this specific thread
                model_load_success = self.ensure_models_loaded_in_thread()
                if not model_load_success:
                    print(f"CRITICAL: Failed to load models for {camera_name}, cannot start monitoring")
                    return
                
                # Verify person model is accessible
                import config
                if not hasattr(config, 'PERSON_MODEL') or config.PERSON_MODEL is None:
                    print(f"CRITICAL: PERSON_MODEL is None after loading for {camera_name}")
                    return
                
                print(f"Models verified for {camera_name} - starting person detection")
                
                # Send start notification
                if self.telegram_config:
                    start_message = f"Camera {camera_name} person detection started\n"
                    if schedule.get('time_range') == 'all':
                        start_message += "Schedule: 24/7"
                    elif schedule.get('type') == 'multiple_ranges':
                        ranges = len(schedule.get('schedules', []))
                        start_message += f"Schedule: {ranges} time periods"
                    else:
                        start_message += f"Schedule: {schedule.get('start_time')} - {schedule.get('end_time')}"
                    start_message += "\nPerson detection alerts enabled"
                    
                    self.send_telegram_notification(start_message)
                
                # CRITICAL FIX: Create stop callback function
                def stop_check():
                    return self.should_camera_stop(camera_name)
                
                # CRITICAL FIX: Call camera processing with person detection only and stop control
                print(f"Calling process_camera_real_time for {camera_name} with person detection")
                
                # Import here to ensure fresh module state
                from camera_processing import process_camera_real_time
                
                process_camera_real_time(
                    name=camera_name,
                    url=camera_url,
                    email_config=self.email_config,
                    telegram_config=self.telegram_config,
                    person_detection_only=True,  # CRITICAL: Enable person detection only
                    stop_callback=stop_check     # CRITICAL: Pass stop callback
                )
                
            except Exception as e:
                logging.error(f"Error in camera {camera_name} monitoring thread: {e}")
                print(f"Error in camera {camera_name} monitoring thread: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # CRITICAL FIX: Enhanced cleanup
                print(f"Camera thread ending for {camera_name}")
                
                # Clean up tracking
                if camera_name in self.running_cameras:
                    del self.running_cameras[camera_name]
                
                # Mark detector for cleanup
                self.detector_cleanup_required.add(camera_name)
                
                # Clean up thread control
                if camera_name in self.camera_stop_flags:
                    del self.camera_stop_flags[camera_name]
                if camera_name in self.camera_thread_locks:
                    del self.camera_thread_locks[camera_name]
                
                print(f"Camera {camera_name} monitoring thread ended and cleaned up")
                logging.info(f"Camera {camera_name} monitoring thread ended and cleaned up")
        
        # Start camera thread
        camera_thread = threading.Thread(
            target=camera_wrapper,
            name=f"ScheduledCam-{camera_name}-{int(time.time())}",
            daemon=True
        )
        camera_thread.start()
        
        # Track the running camera
        self.running_cameras[camera_name] = {
            'thread': camera_thread,
            'start_time': datetime.now(),
            'schedule': schedule,
            'url': camera_url,
            'thread_id': camera_thread.ident
        }
        
        print(f"Camera monitoring thread started for {camera_name} (ID: {camera_thread.ident})")
        return True
    
    def stop_camera_monitoring(self, camera_name):
        """CRITICAL FIX: Enhanced camera monitoring stop"""
        if camera_name not in self.running_cameras:
            print(f"Camera {camera_name} is not currently running")
            return False
        
        print(f"Stopping enhanced monitoring for {camera_name}")
        logging.info(f"Stopping enhanced monitoring for {camera_name}")
        
        # CRITICAL FIX: Set stop flag to signal the camera thread to stop
        self.set_camera_stop_flag(camera_name, True)
        
        # Get camera info before removal
        camera_info = self.running_cameras.get(camera_name)
        
        # CRITICAL FIX: Wait for thread to respond to stop signal
        if camera_info and camera_info['thread'].is_alive():
            print(f"Waiting for {camera_name} thread to stop...")
            for i in range(10):  # Wait up to 10 seconds
                if not camera_info['thread'].is_alive():
                    print(f"Thread stopped for {camera_name}")
                    break
                time.sleep(1)
            
            if camera_info['thread'].is_alive():
                print(f"Warning: Thread for {camera_name} did not stop gracefully")
        
        # Remove from tracking
        if camera_name in self.running_cameras:
            del self.running_cameras[camera_name]
        
        # CRITICAL FIX: Clean up detector state
        self.cleanup_camera_detector(camera_name)
        
        # Send notification about camera stop
        if camera_info and self.telegram_config:
            duration = datetime.now() - camera_info['start_time']
            stop_message = f"Camera {camera_name} monitoring stopped\n"
            stop_message += f"Duration: {str(duration).split('.')[0]}"
            
            self.send_telegram_notification(stop_message)
        
        print(f"Enhanced stop completed for {camera_name}")
        return True
    
    def send_telegram_notification(self, message):
        """Send notification via Telegram"""
        try:
            if self.telegram_config and hasattr(bot_handler, 'application'):
                # Send notification using the bot
                import asyncio
                from telegram import Bot
                
                bot_token, chat_ids = self.telegram_config
                bot = Bot(token=bot_token)
                
                # Send to all configured chat IDs
                if isinstance(chat_ids, list):
                    for chat_id in chat_ids:
                        try:
                            asyncio.run(bot.send_message(chat_id=chat_id, text=f"CAMERA SCHEDULE\n\n{message}"))
                        except Exception as e:
                            logging.error(f"Error sending message to {chat_id}: {e}")
                else:
                    asyncio.run(bot.send_message(chat_id=chat_ids, text=f"CAMERA SCHEDULE\n\n{message}"))
                    
        except Exception as e:
            logging.error(f"Error sending Telegram notification: {e}")
    

    # Enhanced debugging for schedule updates in scheduled_camera_processor.py

    def check_and_update_schedules(self):
        """CRITICAL FIX: Enhanced schedule checking with proper cleanup and debugging"""
        current_time = time.time()
        
        # Only check schedules every minute
        if current_time - self.last_schedule_check < self.schedule_check_interval:
            return
        
        self.last_schedule_check = current_time
        current_datetime = datetime.now()
        
        print(f"=== SCHEDULE CHECK AT {current_datetime.strftime('%Y-%m-%d %H:%M:%S')} ===")
        
        # Load current schedules
        previous_schedules = self.camera_schedules.copy()
        self.camera_schedules = self.load_camera_schedules()
        
        if not self.camera_schedules:
            print("No schedules found - stopping all running cameras")
            for camera_name in list(self.running_cameras.keys()):
                print(f"No schedules found, stopping {camera_name}")
                self.stop_camera_monitoring(camera_name)
            return
        
        print(f"Loaded {len(self.camera_schedules)} camera schedules")
        for cam_name, sched in self.camera_schedules.items():
            if sched.get('type') == 'multiple_ranges':
                ranges = len(sched.get('schedules', []))
                print(f"  - {cam_name}: Multiple ranges ({ranges} periods)")
                for i, time_sched in enumerate(sched.get('schedules', []), 1):
                    print(f"    {i}. {time_sched.get('start_time')}-{time_sched.get('end_time')}")
            elif sched.get('time_range') == 'all':
                print(f"  - {cam_name}: 24/7 monitoring")
            else:
                print(f"  - {cam_name}: {sched.get('start_time')}-{sched.get('end_time')}")
        
        active_schedules = {}
        
        # CRITICAL FIX: Check for schedule changes
        schedule_changes = set()
        for camera_name in self.camera_schedules:
            if camera_name in previous_schedules:
                old_schedule = previous_schedules[camera_name]
                new_schedule = self.camera_schedules[camera_name]
                
                # Check if schedule actually changed
                if (old_schedule.get('time_range') != new_schedule.get('time_range') or
                    old_schedule.get('start_time') != new_schedule.get('start_time') or
                    old_schedule.get('end_time') != new_schedule.get('end_time') or
                    old_schedule.get('enabled') != new_schedule.get('enabled') or
                    old_schedule.get('type') != new_schedule.get('type') or
                    old_schedule.get('schedules') != new_schedule.get('schedules')):
                    
                    schedule_changes.add(camera_name)
                    print(f"Schedule change detected for {camera_name}")
        
        # CRITICAL FIX: Restart cameras with changed schedules
        for camera_name in schedule_changes:
            if camera_name in self.running_cameras:
                print(f"Restarting {camera_name} due to schedule change")
                self.stop_camera_monitoring(camera_name)
                time.sleep(2)  # Wait for cleanup
        
        # Check each scheduled camera
        for camera_name, schedule in self.camera_schedules.items():
            should_be_active = self.should_camera_be_active(camera_name, schedule)
            is_currently_running = camera_name in self.running_cameras
            
            print(f"Camera {camera_name}: should_be_active={should_be_active}, is_running={is_currently_running}")
            
            if should_be_active and not is_currently_running:
                # Start camera monitoring
                camera_url = self.get_camera_url_from_config(camera_name)
                if camera_url:
                    print(f"STARTING {camera_name} - should be active and not running")
                    success = self.start_camera_monitoring(camera_name, camera_url, schedule)
                    if success:
                        active_schedules[camera_name] = {
                            'schedule': schedule,
                            'started_at': current_datetime.isoformat(),
                            'status': 'active',
                            'schedule_type': schedule.get('type', 'single'),
                            'time_ranges': len(schedule.get('schedules', [1]))
                        }
                        print(f"SUCCESS: Started monitoring {camera_name} according to schedule")
                        logging.info(f"Started monitoring {camera_name} according to schedule")
                    else:
                        print(f"FAILED: Could not start monitoring {camera_name}")
                else:
                    print(f"ERROR: Camera {camera_name} URL not found in configuration")
                    logging.warning(f"Camera {camera_name} URL not found in configuration")
            
            elif not should_be_active and is_currently_running:
                # Stop camera monitoring when schedule ends
                print(f"STOPPING {camera_name} - schedule ended")
                success = self.stop_camera_monitoring(camera_name)
                if success:
                    print(f"SUCCESS: Stopped monitoring {camera_name} according to schedule")
                    logging.info(f"Stopped monitoring {camera_name} according to schedule")
                else:
                    print(f"FAILED: Could not stop monitoring {camera_name}")
            
            elif should_be_active and is_currently_running:
                # Camera is correctly running
                active_schedules[camera_name] = {
                    'schedule': schedule,
                    'started_at': self.running_cameras[camera_name]['start_time'].isoformat(),
                    'status': 'active',
                    'schedule_type': schedule.get('type', 'single'),
                    'time_ranges': len(schedule.get('schedules', [1]))
                }
                print(f"RUNNING: {camera_name} correctly active")
            else:
                print(f"INACTIVE: {camera_name} correctly not running")
        
        # Check for cameras that should be stopped but aren't in current schedules
        cameras_to_stop = []
        for camera_name in self.running_cameras.keys():
            if camera_name not in self.camera_schedules:
                cameras_to_stop.append(camera_name)
        
        for camera_name in cameras_to_stop:
            print(f"CLEANUP: Camera {camera_name} removed from schedule, stopping")
            self.stop_camera_monitoring(camera_name)
        
        # CRITICAL FIX: Clean up any remaining detector state
        for camera_name in self.detector_cleanup_required.copy():
            self.cleanup_camera_detector(camera_name)
        
        # Save current active schedules
        save_success = self.save_active_schedules(active_schedules)
        if save_success:
            print(f"SUCCESS: Saved {len(active_schedules)} active schedules to active_schedules.json")
        else:
            print("FAILED: Could not save active schedules")
        
        # Enhanced status logging
        active_count = len(self.running_cameras)
        total_count = len(self.camera_schedules)
        print(f"=== SCHEDULE CHECK COMPLETE ===")
        print(f"Active Cameras: {active_count}/{total_count}")
        print(f"Running: {list(self.running_cameras.keys())}")
        print(f"Active Schedules Saved: {len(active_schedules)}")
        logging.info(f"Enhanced Schedule Status: {active_count}/{total_count} cameras active - {list(self.running_cameras.keys())}")
    
    def get_schedule_status(self):
        """Get current schedule status for reporting"""
        status = {
            'total_schedules': len(self.camera_schedules),
            'active_cameras': len(self.running_cameras),
            'schedules': {},
            'running_cameras': {}
        }
        
        current_time = datetime.now()
        
        for camera_name, schedule in self.camera_schedules.items():
            should_be_active = self.should_camera_be_active(camera_name, schedule)
            is_running = camera_name in self.running_cameras
            
            status['schedules'][camera_name] = {
                'schedule': schedule,
                'should_be_active': should_be_active,
                'is_running': is_running,
                'status': 'active' if (should_be_active and is_running) else 
                         'scheduled' if should_be_active else 'inactive'
            }
        
        for camera_name, camera_info in self.running_cameras.items():
            duration = current_time - camera_info['start_time']
            status['running_cameras'][camera_name] = {
                'start_time': camera_info['start_time'].isoformat(),
                'duration': str(duration).split('.')[0],
                'schedule': camera_info['schedule'],
                'thread_id': camera_info.get('thread_id', 'unknown')
            }
        
        return status
    
    def run_schedule_monitor(self):
        """Main loop for monitoring and managing camera schedules"""
        print("Starting enhanced camera schedule monitor...")
        logging.info("Enhanced camera schedule monitor started")
        
        self.is_running = True
        
        while self.is_running:
            try:
                self.check_and_update_schedules()
                time.sleep(30)  # Check every 30 seconds for responsiveness
                
            except KeyboardInterrupt:
                print("Schedule monitor stopped by user")
                logging.info("Schedule monitor stopped by user")
                break
                
            except Exception as e:
                logging.error(f"Error in schedule monitor: {e}")
                print(f"Error in schedule monitor: {e}")
                time.sleep(60)  # Wait longer on error
        
        # Clean up running cameras
        for camera_name in list(self.running_cameras.keys()):
            self.stop_camera_monitoring(camera_name)
        
        print("Enhanced camera schedule monitor stopped")
        logging.info("Enhanced camera schedule monitor stopped")
    
    def stop_all_monitoring(self):
        """CRITICAL FIX: Enhanced stop all monitoring"""
        self.is_running = False
        
        # Stop all cameras with enhanced cleanup
        for camera_name in list(self.running_cameras.keys()):
            print(f"Stopping all monitoring - enhanced stop for {camera_name}")
            self.stop_camera_monitoring(camera_name)
        
        # Wait for threads to stop
        time.sleep(5)
        
        # Final cleanup
        for camera_name in list(self.detector_cleanup_required):
            self.cleanup_camera_detector(camera_name)
        
        print("All scheduled camera monitoring stopped with enhanced cleanup")
        logging.info("All scheduled camera monitoring stopped with enhanced cleanup")

# Global instance
scheduled_processor = None

def start_scheduled_camera_processor(email_config=None, telegram_config=None):
    """Start the enhanced scheduled camera processor in a separate thread"""
    global scheduled_processor
    
    scheduled_processor = ScheduledCameraProcessor(email_config, telegram_config)
    
    monitor_thread = threading.Thread(
        target=scheduled_processor.run_schedule_monitor,
        name="EnhancedScheduleMonitor",
        daemon=True
    )
    monitor_thread.start()
    
    print("Enhanced scheduled camera processor started")
    logging.info("Enhanced scheduled camera processor started")
    
    return scheduled_processor

def get_scheduled_processor():
    """Get the global scheduled processor instance"""
    return scheduled_processor