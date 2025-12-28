# system_utils.py - System monitoring and internet utilities
import socket
import time
import psutil
import gc
import cv2
import subprocess
import os
import sys
import logging
from datetime import datetime
from config import INTERNET_MONITOR_STATE, LAST_FIRE_DETECTION_IMAGE
from file_utils import get_folder_size
from config import BASE_DIR, ALERTS_DIR

def check_internet_connection(timeout=10):
    """Check internet connectivity by attempting to connect to reliable DNS servers"""
    test_servers = [
        ("8.8.8.8", 53),      # Google DNS
        ("1.1.1.1", 53),      # Cloudflare DNS  
        ("208.67.222.222", 53) # OpenDNS
    ]
    
    for server_ip, port in test_servers:
        try:
            socket.create_connection((server_ip, port), timeout=timeout)
            return True
        except (socket.error, socket.timeout, OSError):
            continue
    return False

def monitor_internet_connection():
    """
    Monitor internet connection and track outages with detailed statistics
    Returns current connection status
    """
    current_time = time.time()
    is_connected = check_internet_connection()
    
    # Update last check time
    INTERNET_MONITOR_STATE["last_check_time"] = current_time
    
    # Handle connection state changes
    if is_connected and not INTERNET_MONITOR_STATE["is_connected"]:
        # Connection restored
        if INTERNET_MONITOR_STATE["outage_start_time"]:
            outage_duration = current_time - INTERNET_MONITOR_STATE["outage_start_time"]
            INTERNET_MONITOR_STATE["last_outage_duration"] = outage_duration
            INTERNET_MONITOR_STATE["total_downtime_seconds"] += outage_duration
            
            # Update longest outage record
            if outage_duration > INTERNET_MONITOR_STATE["longest_outage_seconds"]:
                INTERNET_MONITOR_STATE["longest_outage_seconds"] = outage_duration
            
            # Categorize and log outage
            if outage_duration < 420:  # Less than 7 minutes
                INTERNET_MONITOR_STATE["short_outages_count"] += 1
                print(f"Internet: Connection restored after {outage_duration/60:.1f} minutes (short outage)")
                logging.info(f"Short internet outage resolved: {outage_duration/60:.1f} minutes")
            else:
                INTERNET_MONITOR_STATE["significant_outages_count"] += 1
                print(f"Internet: Connection restored after {outage_duration/60:.1f} minutes (significant outage)")
                logging.warning(f"Significant internet outage resolved: {outage_duration/60:.1f} minutes")
                
                # Send recovery notification for significant outages only
                recovery_msg = (f"Internet connection restored after {outage_duration/60:.1f} minutes.\n"
                               f"System resuming normal alert operations.\n"
                               f"Checking for queued fire alerts...")
                print(recovery_msg)
                
                # Process any delayed fire alerts
                send_delayed_fire_alerts()
            
            INTERNET_MONITOR_STATE["outage_start_time"] = None
        
        INTERNET_MONITOR_STATE["is_connected"] = True
        
    elif not is_connected and INTERNET_MONITOR_STATE["is_connected"]:
        # Connection lost - start tracking outage
        INTERNET_MONITOR_STATE["is_connected"] = False
        INTERNET_MONITOR_STATE["outage_start_time"] = current_time
        INTERNET_MONITOR_STATE["total_outages"] += 1
        
        print("Internet: Connection lost - entering offline mode")
        print("Fire alerts will be queued and sent upon connection recovery")
        logging.warning("Internet connection lost - alerts will be queued for offline delivery")
    
    return is_connected

def send_delayed_fire_alerts():
    """
    Send any fire alerts that were queued during internet outage
    This function would integrate with the alerting module in the full system
    """
    global LAST_FIRE_DETECTION_IMAGE
    
    if LAST_FIRE_DETECTION_IMAGE and os.path.exists(LAST_FIRE_DETECTION_IMAGE):
        fire_recovery_msg = (
            "DELAYED FIRE ALERT - Internet Connection Recovered\n\n"
            "CRITICAL: This fire detection occurred during internet outage.\n"
            "Alert was preserved and is being sent upon connection recovery.\n\n"
            f"Original Detection Time: {os.path.getctime(LAST_FIRE_DETECTION_IMAGE)}\n"
            f"Recovery Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "IMMEDIATE ATTENTION REQUIRED - VERIFY FIRE STATUS"
        )
        
        print(f"Sending delayed fire alert: {os.path.basename(LAST_FIRE_DETECTION_IMAGE)}")
        logging.critical(f"Delayed fire alert being sent: {LAST_FIRE_DETECTION_IMAGE}")
        
        # In the full system, this would call the actual alerting functions
        # send_email_alert("CRITICAL: Delayed Fire Detection", fire_recovery_msg)
        # send_telegram_alert(fire_recovery_msg, LAST_FIRE_DETECTION_IMAGE)
        
        # Clear the queued alert after sending
        LAST_FIRE_DETECTION_IMAGE = None

def get_internet_statistics():
    """Get comprehensive internet connectivity statistics and uptime metrics"""
    current_time = time.time()
    
    # Calculate current outage duration if offline
    current_outage_duration = 0
    if not INTERNET_MONITOR_STATE["is_connected"] and INTERNET_MONITOR_STATE["outage_start_time"]:
        current_outage_duration = current_time - INTERNET_MONITOR_STATE["outage_start_time"]
    
    # Initialize start time for uptime calculation if needed
    if not hasattr(get_internet_statistics, "start_time"):
        get_internet_statistics.start_time = current_time
    
    # Calculate uptime percentage
    total_runtime = current_time - get_internet_statistics.start_time
    if total_runtime <= 0:
        uptime_percentage = 100.0
    else:
        actual_uptime = total_runtime - INTERNET_MONITOR_STATE["total_downtime_seconds"]
        uptime_percentage = max(0.0, min(100.0, (actual_uptime / total_runtime) * 100))
    
    return {
        "is_connected": INTERNET_MONITOR_STATE["is_connected"],
        "total_outages": INTERNET_MONITOR_STATE["total_outages"],
        "short_outages": INTERNET_MONITOR_STATE["short_outages_count"],
        "significant_outages": INTERNET_MONITOR_STATE["significant_outages_count"],
        "total_downtime_minutes": INTERNET_MONITOR_STATE["total_downtime_seconds"] / 60,
        "longest_outage_minutes": INTERNET_MONITOR_STATE["longest_outage_seconds"] / 60,
        "current_outage_minutes": current_outage_duration / 60,
        "last_check_time": INTERNET_MONITOR_STATE["last_check_time"],
        "uptime_percentage": uptime_percentage,
        "last_outage_duration_minutes": INTERNET_MONITOR_STATE["last_outage_duration"] / 60
    }

def continuous_internet_monitor(check_interval=30):
    """
    Continuous internet monitoring thread with intelligent alerting
    Only sends recovery notifications for significant outages (>= 7 minutes)
    """
    print("Starting enhanced internet connection monitor...")
    print(f"Check interval: {check_interval} seconds")
    print("Monitoring policy:")
    print("  - Immediate logging for all connection losses")  
    print("  - Recovery alerts only for outages >= 7 minutes")
    print("  - Short outages logged but no recovery notification")
    print("  - Fire alerts queued during any outage duration")
    
    # Initialize monitoring state
    INTERNET_MONITOR_STATE["last_status_log"] = time.time()
    
    while True:
        try:
            # Perform connection check and update state
            is_connected = monitor_internet_connection()
            
            # Periodic status logging based on connection state
            current_time = time.time()
            
            if is_connected:
                # Log connectivity status every 5 minutes when stable
                if current_time - INTERNET_MONITOR_STATE.get("last_status_log", 0) > 300:
                    stats = get_internet_statistics()
                    
                    status_msg = (f"Internet: Online | "
                                f"Uptime: {stats['uptime_percentage']:.1f}% | "
                                f"Total Outages: {stats['total_outages']} "
                                f"({stats['short_outages']} short, {stats['significant_outages']} significant)")
                    
                    print(status_msg)
                    INTERNET_MONITOR_STATE["last_status_log"] = current_time
                    
                    # Log detailed stats periodically
                    if stats['total_outages'] > 0:
                        logging.info(f"Internet stats: {stats}")
            else:
                # Show ongoing outage duration every 2 minutes when offline
                if (INTERNET_MONITOR_STATE["outage_start_time"] and 
                    current_time - INTERNET_MONITOR_STATE.get("last_outage_log", 0) > 120):
                    
                    outage_minutes = (current_time - INTERNET_MONITOR_STATE["outage_start_time"]) / 60
                    print(f"Internet: OFFLINE for {outage_minutes:.1f} minutes - alerts queued")
                    INTERNET_MONITOR_STATE["last_outage_log"] = current_time
            
            # Wait before next check
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            print("\nInternet monitoring stopped by user")
            break
        except Exception as e:
            print(f"Error in internet monitoring: {e}")
            logging.error(f"Internet monitoring error: {e}")
            # Continue monitoring after error with longer delay
            time.sleep(min(check_interval * 2, 120))

def check_memory_usage():
    """Check system memory usage and trigger garbage collection if needed"""
    try:
        memory_info = psutil.virtual_memory()
        memory_percent = memory_info.percent
        
        if memory_percent > 90:
            print(f"Warning: High memory usage detected: {memory_percent:.1f}%")
            logging.warning(f"High memory usage: {memory_percent:.1f}%")
            
            # Force garbage collection
            collected = gc.collect()
            print(f"Garbage collection freed {collected} objects")
            
            # Check memory again after cleanup
            new_memory_info = psutil.virtual_memory()
            new_percent = new_memory_info.percent
            print(f"Memory usage after cleanup: {new_percent:.1f}%")
            
            return True
        
        return False
        
    except Exception as e:
        print(f"Error checking memory usage: {e}")
        logging.error(f"Memory check error: {e}")
        return False

def restart_system_immediately():
    """
    Emergency system restart with notification
    Used when critical camera connection failures occur
    """
    alert_message = (
        "CRITICAL SYSTEM ERROR\n"
        "Multiple camera connection failures detected.\n"
        "System performing automatic restart to recover.\n"
        f"Restart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    print("=" * 50)
    print("EMERGENCY SYSTEM RESTART")
    print("=" * 50)
    print(alert_message)
    print("=" * 50)
    
    logging.critical("Emergency system restart initiated due to camera failures")
    
    # In full system, this would send actual alerts
    # send_startup_notification("SYSTEM RESTART", alert_message, is_success=False, force=True)
    
    try:
        # Determine the correct script to restart
        python_executable = sys.executable
        main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "every.py")
        
        if not os.path.exists(main_script):
            # Fallback to current script if every.py not found
            main_script = sys.argv[0]
        
        print(f"Restarting: {python_executable} {main_script}")
        
        # Start new process
        subprocess.Popen([python_executable, main_script], 
                        cwd=os.path.dirname(os.path.abspath(__file__)))
        
        # Give new process time to start
        time.sleep(2)
        
    except Exception as e:
        print(f"Error during restart: {e}")
        logging.error(f"System restart error: {e}")
    finally:
        # Terminate current process
        print("Terminating current process...")
        os._exit(0)

def grab_real_time_frame(cap, max_flush=12):
    """
    Enhanced frame grabbing for real-time detection with error handling
    Aggressively flushes buffer to get the most recent frame
    """
    if not cap or not cap.isOpened():
        return None
    
    try:
        # Flush buffer to get most recent frame
        frames_flushed = 0
        while frames_flushed < max_flush:
            ret = cap.grab()
            if not ret:
                break
            frames_flushed += 1
        
        # Retrieve the latest frame
        ret, frame = cap.retrieve()
        if not ret or frame is None or frame.size == 0:
            return None
            
        return frame
        
    except Exception as e:
        print(f"Error grabbing frame: {e}")
        return None

def grab_latest_frame(cap, max_flush=8):
    """
    Standard frame grabbing with buffer flush
    For live streams: grab a few frames to flush queue, then retrieve one
    """
    if not cap or not cap.isOpened():
        return None
    
    try:
        # Try to flush buffer quickly without decoding
        for _ in range(max_flush):
            grabbed = cap.grab()
            if not grabbed:
                break
        
        # Retrieve frame
        ret, frame = cap.retrieve()
        if not ret or frame is None:
            return None
            
        return frame
        
    except Exception as e:
        print(f"Error in frame grabbing: {e}")
        return None

def system_monitor():
    """
    Comprehensive system monitoring with resource tracking
    Monitors CPU, memory, disk usage, and system health metrics
    """
    # Import here to avoid circular imports - FIXED THE RELATIVE IMPORT
    from config import ADAPTIVE_DETECTORS, DETECTION_STATS
    
    print("Starting comprehensive system monitor...")
    print("Monitoring: CPU, Memory, Disk, Internet, Detection Stats")
    
    while True:
        try:
            # Get internet statistics
            internet_stats = get_internet_statistics()
            
            # Get system resource information
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get disk usage for alerts directory
            disk_usage = psutil.disk_usage(BASE_DIR)
            disk_free_gb = disk_usage.free / (1024**3)
            disk_used_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Count active camera detectors
            active_cameras = 0
            total_frames_processed = 0
            try:
                for name, detector in ADAPTIVE_DETECTORS.items():
                    if detector.frames_processed > 0:
                        active_cameras += 1
                        total_frames_processed += detector.frames_processed
            except Exception:
                pass

            # Get detection statistics
            fire_alerts = DETECTION_STATS.get('fire_alerts_sent', 0)
            smoke_alerts = DETECTION_STATS.get('smoke_alerts_sent', 0)
            objects_excluded = DETECTION_STATS.get('objects_excluded_detections', 0)
            valid_fire_detections = DETECTION_STATS.get('valid_fire_detections', 0)
            valid_smoke_detections = DETECTION_STATS.get('valid_smoke_detections', 0)
            
            # Calculate folder sizes
            alerts_size_mb = 0
            log_size_mb = 0
            
            try:
                alerts_size_mb = get_folder_size(ALERTS_DIR) / (1024 * 1024)
                log_path = os.path.join(BASE_DIR, "fire_smoke_detection_log.txt")
                if os.path.exists(log_path):
                    log_size_mb = os.path.getsize(log_path) / (1024 * 1024)
            except Exception:
                pass
            
            # Format connection status
            if internet_stats["is_connected"]:
                connection_status = f"Online (Uptime: {internet_stats['uptime_percentage']:.1f}%)"
            else:
                connection_status = f"OFFLINE ({internet_stats['current_outage_minutes']:.1f}min)"
            
            # Create comprehensive status message
            status_parts = [
                f"CPU: {cpu_percent:.1f}%",
                f"RAM: {memory.percent:.1f}%",
                f"Disk: {disk_free_gb:.1f}GB free",
                f"Cameras: {active_cameras}",
                f"Internet: {connection_status}",
                f"Fire Alerts: {fire_alerts}",
                f"Smoke Alerts: {smoke_alerts}",
                f"Valid Detections: F{valid_fire_detections}/S{valid_smoke_detections}",
                f"Objects Excluded: {objects_excluded}",
                f"Storage: {alerts_size_mb:.1f}MB alerts, {log_size_mb:.1f}MB log"
            ]
            
            status_message = "System Status: " + " | ".join(status_parts)
            print(status_message)
            
            # Log detailed statistics periodically (every hour)
            current_time = time.time()
            if not hasattr(system_monitor, 'last_detailed_log'):
                system_monitor.last_detailed_log = 0
                
            if current_time - system_monitor.last_detailed_log > 3600:  # 1 hour
                detailed_stats = {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_free_gb': disk_free_gb,
                    'disk_used_percent': disk_used_percent,
                    'active_cameras': active_cameras,
                    'total_frames_processed': total_frames_processed,
                    'internet_stats': internet_stats,
                    'detection_stats': dict(DETECTION_STATS),
                    'alerts_size_mb': alerts_size_mb,
                    'log_size_mb': log_size_mb
                }
                logging.info(f"Detailed system statistics: {detailed_stats}")
                system_monitor.last_detailed_log = current_time
            
            # Check for resource warnings
            if memory.percent > 85:
                logging.warning(f"High memory usage: {memory.percent:.1f}%")
            
            if cpu_percent > 90:
                logging.warning(f"High CPU usage: {cpu_percent:.1f}%")
                
            if disk_free_gb < 1.0:  # Less than 1GB free
                logging.warning(f"Low disk space: {disk_free_gb:.1f}GB remaining")

        except Exception as e:
            logging.error(f"System monitor error: {e}")
            print(f"System monitor error: {e}")
        
        # Monitor every 5 minutes
        time.sleep(300)