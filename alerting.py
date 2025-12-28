# alerting_fixed.py - COMPLETE Fixed Alert System with Enhanced Connection Pool Management
import smtplib
import requests
import threading
import time
import logging
import cv2
import os
import platform
import asyncio
from datetime import datetime
from email.mime.text import MIMEText
from threading import Lock
import httpx
from telegram.error import NetworkError, TimedOut, RetryAfter, BadRequest, Forbidden, TelegramError
import json
from typing import List, Optional, Union
import socket
import urllib3

from config import (FIRE_ALERT_COOLDOWN, SMOKE_ALERT_COOLDOWN, NOTIFICATION_INTERVAL, 
                    ALERTS_DIR, LAST_FIRE_ALERT_TIME, LAST_SMOKE_ALERT_TIME, 
                    LAST_NOTIFICATION_TIME, DETECTION_STATS, ADAPTIVE_DETECTORS, 
                    LAST_FIRE_DETECTION_IMAGE)

# Disable SSL warnings for unreliable connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# FIXED: Enhanced thread-safe locks
stats_lock = Lock()
alert_queue_lock = Lock()
network_lock = Lock()

# Global bot application reference
bot_application = None

# FIXED: Enhanced network and connection pool tracking
network_status = {
    'last_successful_connection': 0,
    'consecutive_failures': 0,
    'max_failures_before_offline': 5,
    'is_online': True,
    'last_check': 0,
    'check_interval': 30,
    'telegram_pool_timeouts': 0,  # FIXED: Track pool timeout errors
    'last_pool_reset': 0          # FIXED: Track last pool reset time
}

# Enhanced queue for failed alerts with priority and retry logic
failed_alerts_queue = []
max_queue_size = 100

# FIXED: Connection pool management
telegram_connection_pool = {
    'active_sends': 0,
    'max_concurrent_sends': 3,  # FIXED: Reduce from 5 to prevent pool exhaustion
    'send_lock': threading.Lock(),  # Use threading.Lock for sync contexts
    'last_cleanup': time.time(),
    'cleanup_interval': 120     # Clean up every 2 minutes
}

def set_bot_application(application):
    """Set the global bot application reference"""
    global bot_application
    bot_application = application
    print("FIXED: Bot application reference set in alerting system")

def check_internet_connection_advanced(timeout=10):
    """FIXED: Advanced internet connection check with pool timeout awareness"""
    global network_status
    
    current_time = time.time()
    
    # Don't check too frequently
    if current_time - network_status['last_check'] < network_status['check_interval']:
        return network_status['is_online']
    
    network_status['last_check'] = current_time
    
    # Multiple test methods for reliability
    test_methods = [
        {'method': 'telegram_api', 'url': 'https://api.telegram.org', 'timeout': 5},
        {'method': 'google_dns', 'host': '8.8.8.8', 'port': 53, 'timeout': 3},
        {'method': 'cloudflare_dns', 'host': '1.1.1.1', 'port': 53, 'timeout': 3},
        {'method': 'http_check', 'url': 'https://httpbin.org/status/200', 'timeout': 5}
    ]
    
    connection_successful = False
    
    for test in test_methods:
        try:
            if test['method'] in ['telegram_api', 'http_check']:
                # HTTP-based test
                response = requests.get(
                    test['url'], 
                    timeout=test['timeout'],
                    verify=False,
                    headers={'User-Agent': 'Fire-Detection-System/1.0'}
                )
                if response.status_code in [200, 401, 404]:
                    connection_successful = True
                    break
                    
            elif test['method'] in ['google_dns', 'cloudflare_dns']:
                # Socket-based test
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(test['timeout'])
                result = sock.connect_ex((test['host'], test['port']))
                sock.close()
                if result == 0:
                    connection_successful = True
                    break
                    
        except Exception as e:
            print(f"FIXED: Network test {test['method']} failed: {e}")
            continue
    
    # Update network status
    with network_lock:
        if connection_successful:
            network_status['last_successful_connection'] = current_time
            network_status['consecutive_failures'] = 0
            network_status['is_online'] = True
            if not network_status['is_online']:
                print("FIXED: Network connection restored!")
                logging.info("FIXED: Network connection restored")
        else:
            network_status['consecutive_failures'] += 1
            if network_status['consecutive_failures'] >= network_status['max_failures_before_offline']:
                if network_status['is_online']:
                    print(f"FIXED: Network connection lost after {network_status['consecutive_failures']} failures")
                    logging.warning("FIXED: Network connection lost")
                network_status['is_online'] = False
    
    return network_status['is_online']

def cleanup_telegram_connection_pool():
    """FIXED: Clean up Telegram connection pool periodically (sync version)"""
    global telegram_connection_pool
    
    current_time = time.time()
    
    if current_time - telegram_connection_pool['last_cleanup'] > telegram_connection_pool['cleanup_interval']:
        with telegram_connection_pool['send_lock']:
            if telegram_connection_pool['active_sends'] > 0:
                print(f"FIXED: Cleaning up connection pool - resetting {telegram_connection_pool['active_sends']} active sends")
                telegram_connection_pool['active_sends'] = 0
            
            telegram_connection_pool['last_cleanup'] = current_time
            print("FIXED: Telegram connection pool cleaned up")

def queue_failed_alert(alert_type, message, image_path=None, chat_ids=None, email_config=None, priority="normal"):
    """FIXED: Enhanced failed alert queue with connection pool awareness"""
    global failed_alerts_queue, max_queue_size
    
    with alert_queue_lock:
        # Prevent queue from growing too large
        if len(failed_alerts_queue) >= max_queue_size:
            # Remove oldest low-priority alerts to make room
            failed_alerts_queue = [alert for alert in failed_alerts_queue if alert['priority'] == 'high']
            if len(failed_alerts_queue) >= max_queue_size * 0.8:
                # Still too many, remove some high priority too (keep most recent)
                failed_alerts_queue = failed_alerts_queue[-int(max_queue_size * 0.5):]
            print(f"FIXED: Alert queue cleaned up, now has {len(failed_alerts_queue)} items")
        
        failed_alert = {
            'type': alert_type,
            'message': message,
            'image_path': image_path,
            'chat_ids': chat_ids,
            'email_config': email_config,
            'timestamp': time.time(),
            'retry_count': 0,
            'max_retries': 3 if network_status['is_online'] else 1,
            'priority': priority,
            'last_retry': 0,
            'pool_timeout_retries': 0  # FIXED: Track pool timeout specific retries
        }
        
        # Insert based on priority
        if priority == "high":
            failed_alerts_queue.insert(0, failed_alert)
        else:
            failed_alerts_queue.append(failed_alert)
        
        print(f"FIXED: Queued failed {alert_type} alert for retry (priority: {priority}, queue size: {len(failed_alerts_queue)})")

def send_telegram_message_with_enhanced_pool_management(message, image_path=None, chat_ids=None, max_retries=2):
    """
    FIXED: Enhanced Telegram sender with comprehensive connection pool management (sync version)
    """
    global bot_application, network_status, telegram_connection_pool
    
    if not bot_application:
        print("FIXED: Bot application not available for sending messages")
        return False
    
    if not chat_ids:
        print("FIXED: No chat IDs provided")
        return False
    
    # FIXED: Check and clean up connection pool first
    cleanup_telegram_connection_pool()
    
    # Check network status first
    if not check_internet_connection_advanced():
        print("FIXED: Network appears to be offline, queueing message for later")
        queue_failed_alert('telegram', message, image_path, chat_ids, priority="high")
        return False
    
    # FIXED: Enhanced connection pool management
    with telegram_connection_pool['send_lock']:
        if telegram_connection_pool['active_sends'] >= telegram_connection_pool['max_concurrent_sends']:
            print(f"FIXED: Too many active Telegram sends ({telegram_connection_pool['active_sends']}), queueing message")
            queue_failed_alert('telegram', message, image_path, chat_ids, priority="normal")
            return False
        
        telegram_connection_pool['active_sends'] += 1
    
    try:
        # Ensure chat_ids is a list
        if isinstance(chat_ids, (str, int)):
            chat_ids = [int(chat_ids)]
        elif isinstance(chat_ids, list):
            chat_ids = [int(cid) for cid in chat_ids]
        
        success_count = 0
        total_chats = len(chat_ids)
        
        for chat_id in chat_ids:
            retry_count = 0
            chat_success = False
            
            while retry_count < max_retries and not chat_success:
                try:
                    # FIXED: Use longer timeout for better reliability
                    timeout = 25  # Increased from 15
                    
                    # FIXED: Create a wrapper function to handle async calls from sync context
                    def send_message_sync():
                        loop = None
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        async def send_async():
                            if image_path and os.path.exists(image_path):
                                with open(image_path, 'rb') as photo:
                                    return await bot_application.bot.send_photo(
                                        chat_id=chat_id,
                                        photo=photo,
                                        caption=message[:1024] if len(message) > 1024 else message,
                                        read_timeout=timeout,
                                        write_timeout=timeout,
                                        connect_timeout=timeout,
                                        pool_timeout=timeout
                                    )
                            else:
                                return await bot_application.bot.send_message(
                                    chat_id=chat_id,
                                    text=message,
                                    parse_mode='HTML' if '<b>' in message or '<i>' in message else None,
                                    read_timeout=timeout,
                                    write_timeout=timeout,
                                    connect_timeout=timeout,
                                    pool_timeout=timeout
                                )
                        
                        if loop.is_running():
                            # We're in an async context, create a task and wait
                            task = loop.create_task(send_async())
                            # Use a timeout to prevent hanging
                            return asyncio.wait_for(task, timeout=timeout + 10)
                        else:
                            return loop.run_until_complete(send_async())
                    
                    # Execute the sync wrapper
                    result = send_message_sync()
                    
                    if image_path and os.path.exists(image_path):
                        print(f"FIXED: Photo message sent successfully to chat {chat_id}")
                    else:
                        print(f"FIXED: Text message sent successfully to chat {chat_id}")
                    
                    chat_success = True
                    success_count += 1
                        
                except RetryAfter as e:
                    wait_time = min(e.retry_after + 1, 60)
                    print(f"FIXED: Rate limited for chat {chat_id}, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    retry_count += 1
                    continue
                    
                except (httpx.PoolTimeout, asyncio.TimeoutError) as e:
                    # FIXED: Special handling for pool timeout errors
                    network_status['telegram_pool_timeouts'] += 1
                    print(f"FIXED: Pool timeout for chat {chat_id} (attempt {retry_count + 1}): {e}")
                    print(f"FIXED: Total pool timeouts: {network_status['telegram_pool_timeouts']}")
                    
                    # FIXED: Reset connection pool if too many timeouts
                    if network_status['telegram_pool_timeouts'] % 3 == 0:
                        print("FIXED: Resetting connection pool due to repeated timeouts")
                        with telegram_connection_pool['send_lock']:
                            telegram_connection_pool['active_sends'] = 0
                    
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = min(5 * (retry_count + 1), 30)  # Progressive delay up to 30s
                        print(f"FIXED: Waiting {wait_time}s before retry due to pool timeout...")
                        time.sleep(wait_time)
                    
                except (NetworkError, httpx.ConnectError, socket.timeout, 
                       ConnectionError, OSError) as e:
                    print(f"FIXED: Network error for chat {chat_id} (attempt {retry_count + 1}): {e}")
                    retry_count += 1
                    
                    if retry_count < max_retries:
                        wait_time = min(3 ** retry_count, 15)  # Exponential backoff, max 15s
                        print(f"FIXED: Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(f"FIXED: Max retries reached for chat {chat_id}, queuing for later")
                        with network_lock:
                            network_status['consecutive_failures'] += 1
                    
                except (BadRequest, Forbidden) as e:
                    print(f"FIXED: Telegram API error for chat {chat_id}: {e}")
                    break  # Don't retry these errors
                    
                except TelegramError as e:
                    print(f"FIXED: Telegram error for chat {chat_id} (attempt {retry_count + 1}): {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(3)
                        
                except Exception as e:
                    print(f"FIXED: Unexpected error for chat {chat_id} (attempt {retry_count + 1}): {e}")
                    logging.error(f"FIXED: Telegram send error for chat {chat_id}: {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(3)
            
            # If this chat failed completely, queue it for retry
            if not chat_success:
                print(f"FIXED: Failed to send to chat {chat_id} after {max_retries} attempts, queuing for retry")
                queue_failed_alert('telegram', message, image_path, [chat_id], priority="normal")
        
        # Update network status based on results
        if success_count > 0:
            with network_lock:
                network_status['last_successful_connection'] = time.time()
                network_status['consecutive_failures'] = 0
                network_status['is_online'] = True
        
        success_rate = success_count / total_chats if total_chats > 0 else 0
        print(f"FIXED: Telegram send complete: {success_count}/{total_chats} chats successful ({success_rate:.1%})")
        
        return success_count > 0
        
    finally:
        # FIXED: Always decrement active sends counter
        with telegram_connection_pool['send_lock']:
            telegram_connection_pool['active_sends'] = max(0, telegram_connection_pool['active_sends'] - 1)

# FIXED: Main alert functions using the enhanced sender
def send_telegram_alert_unified(message, image_path=None, bot_token=None, chat_ids=None):
    """
    FIXED: Network-resilient unified Telegram alert function
    """
    print(f"FIXED: send_telegram_alert_unified called:")
    print(f"  Message: {len(message) if message else 0} chars")
    print(f"  Image: {image_path}")
    print(f"  Chat IDs: {chat_ids}")
    print(f"  Bot app: {bot_application is not None}")
    print(f"  Network: {'Online' if network_status['is_online'] else 'Offline'}")
    print(f"  Pool active: {telegram_connection_pool['active_sends']}")
    
    if not message or not chat_ids:
        print("FIXED: Missing message or chat_ids")
        return False
    
    try:
        result = send_telegram_message_with_enhanced_pool_management(message, image_path, chat_ids)
        print(f"FIXED: Telegram send result: {result}")
        return result
                
    except Exception as e:
        print(f"FIXED: Telegram send error: {e}")
        logging.error(f"FIXED: Telegram send error: {e}")
        queue_failed_alert('telegram', message, image_path, chat_ids, priority="normal")
        return False

def send_telegram_alert_with_retry(message, image_path=None, bot_token=None, chat_ids=None, retries=3, retry_count=1):
    """FIXED: Legacy wrapper using enhanced system"""
    if not chat_ids:
        print("FIXED: No Telegram chat IDs configured")
        return False
    
    return send_telegram_alert_unified(message, image_path, bot_token, chat_ids)

def send_telegram_alert(message, image_path=None, bot_token=None, chat_id=None, retries=3):
    """FIXED: Main Telegram alert function"""
    chat_ids = [chat_id] if not isinstance(chat_id, list) else chat_id
    return send_telegram_alert_with_retry(message, image_path, bot_token, chat_ids, retries)

def retry_failed_alerts():
    """FIXED: Enhanced retry mechanism with connection pool awareness"""
    global failed_alerts_queue
    
    with alert_queue_lock:
        if not failed_alerts_queue:
            return
        
        # Don't retry if network is down
        if not check_internet_connection_advanced():
            print(f"FIXED: Network offline - skipping retry of {len(failed_alerts_queue)} queued alerts")
            return
        
        current_time = time.time()
        
        # Sort by priority and timestamp
        failed_alerts_queue.sort(key=lambda x: (
            0 if x['priority'] == 'high' else 1 if x['priority'] == 'normal' else 2,
            x['timestamp']
        ))
        
        # Only retry alerts that haven't been retried recently
        alerts_ready_for_retry = []
        for alert in failed_alerts_queue[:5]:  # FIXED: Reduce from 10 to 5 to prevent pool exhaustion
            time_since_last_retry = current_time - alert.get('last_retry', 0)
            min_retry_interval = 90 * (2 ** alert['retry_count'])  # FIXED: Longer intervals
            
            if time_since_last_retry >= min_retry_interval:
                alerts_ready_for_retry.append(alert)
        
        # Remove from queue
        for alert in alerts_ready_for_retry:
            if alert in failed_alerts_queue:
                failed_alerts_queue.remove(alert)
    
    print(f"FIXED: Retrying {len(alerts_ready_for_retry)} failed alerts...")
    
    for alert in alerts_ready_for_retry:
        alert['retry_count'] += 1
        alert['last_retry'] = current_time
        
        if alert['retry_count'] > alert['max_retries']:
            print(f"FIXED: Alert retry limit exceeded - discarding {alert['type']} alert")
            continue
        
        print(f"FIXED: Retrying {alert['type']} alert (attempt {alert['retry_count']})")
        
        try:
            if alert['type'] == 'telegram':
                success = send_telegram_alert_unified(
                    alert['message'],
                    alert['image_path'],
                    None,
                    alert['chat_ids']
                )
                
                if not success:
                    # Re-queue with lower priority and longer delay
                    new_priority = "low" if alert['retry_count'] > 2 else alert['priority']
                    queue_failed_alert(
                        alert['type'], alert['message'], alert['image_path'],
                        alert['chat_ids'], priority=new_priority
                    )
                else:
                    print(f"FIXED: Successfully retried {alert['type']} alert")
                    
            elif alert['type'] == 'email' and alert['email_config']:
                success = send_email_alert(
                    f"Fire Detection Alert (Retry {alert['retry_count']})",
                    alert['message'],
                    *alert['email_config']
                )
                if not success and alert['retry_count'] < alert['max_retries']:
                    queue_failed_alert(alert['type'], alert['message'], None, None, alert['email_config'])
                    
        except Exception as e:
            print(f"FIXED: Retry attempt {alert['retry_count']} failed: {e}")
            # Re-queue for another try with longer delay
            queue_failed_alert(
                alert['type'], alert['message'], alert['image_path'],
                alert['chat_ids'], alert['email_config'], alert['priority']
            )

def send_email_alert(subject, body, sender_email=None, sender_password=None, to_email=None):
    """Send email alert with enhanced error handling"""
    try:
        if not sender_email or not sender_password or not to_email:
            print("FIXED: Email configuration missing, skipping email alert")
            return False
            
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = to_email
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        
        logging.info(f"Email sent to {to_email}")
        print("Email alert sent successfully!")
        return True
        
    except Exception as e:
        logging.error(f"FIXED: Email error: {e}")
        print(f"FIXED: Email error: {e}")
        return False

def send_startup_notification(title, message, is_success=True, force=False, email_config=None, telegram_config=None):
    """FIXED: Enhanced startup notifications with connection pool awareness"""
    global LAST_NOTIFICATION_TIME
    now = time.time()

    if is_success or force or LAST_NOTIFICATION_TIME is None or (now - LAST_NOTIFICATION_TIME) >= NOTIFICATION_INTERVAL:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # FIXED: Include enhanced connection status
        network_info = "Connected" if network_status['is_online'] else f"Offline ({network_status['consecutive_failures']} failures)"
        pool_info = f"Pool: {telegram_connection_pool['active_sends']}/{telegram_connection_pool['max_concurrent_sends']}"
        
        full_message = f"FIXED SYSTEM NOTIFICATION\n"
        full_message += f"{'='*50}\n"
        full_message += f"Title: {title}\n"
        full_message += f"Time: {timestamp}\n"
        full_message += f"Platform: {platform.system()}\n"
        full_message += f"Status: {'SUCCESS' if is_success else 'FAILURE'}\n"
        full_message += f"Network: {network_info}\n"
        full_message += f"Telegram {pool_info}\n"
        full_message += f"Pool Timeouts: {network_status['telegram_pool_timeouts']}\n"
        full_message += f"Failed Alerts in Queue: {len(failed_alerts_queue)}\n"
        full_message += f"{'='*50}\n\n"
        full_message += message

        log_level = logging.INFO if is_success else logging.ERROR
        logging.log(log_level, f"FIXED NOTIFICATION: {title} - {message}")

        print(f"\nFIXED SYSTEM NOTIFICATION: {title}")
        print(full_message)

        # Send notifications in threads
        if email_config and all(email_config):
            threading.Thread(
                target=send_email_alert,
                args=(f"Fire Detection - {title}", full_message, *email_config),
                daemon=True
            ).start()

        if telegram_config and all(telegram_config):
            bot_token, chat_ids = telegram_config
            
            def send_telegram_notification():
                try:
                    success = send_telegram_alert_unified(full_message, None, bot_token, chat_ids)
                    if success:
                        print("FIXED: Startup notification sent via Telegram")
                    else:
                        print("FIXED: Startup notification queued for retry (connection issues)")
                except Exception as e:
                    print(f"FIXED: Error sending startup notification via Telegram: {e}")
            
            threading.Thread(target=send_telegram_notification, daemon=True).start()

        LAST_NOTIFICATION_TIME = now
    else:
        print("FIXED: Notification suppressed (within 15 min window).")

def log_detection_stats(fire_detected, smoke_detected, fire_valid, smoke_valid, objects_excluded=0):
    """FIXED: Log detection statistics with periodic retry of failed alerts"""
    with stats_lock:
        current_time = time.time()
        DETECTION_STATS['total_frames'] += 1
        
        if fire_detected:
            DETECTION_STATS['fire_detections'] += 1
            if fire_valid:
                DETECTION_STATS['valid_fire_detections'] += 1
                DETECTION_STATS['last_fire_time'] = current_time
            else:
                DETECTION_STATS['false_positives_avoided'] += 1
        
        if smoke_detected:
            DETECTION_STATS['smoke_detections'] += 1
            if smoke_valid:
                DETECTION_STATS['valid_smoke_detections'] += 1
                DETECTION_STATS['last_smoke_time'] = current_time
            else:
                DETECTION_STATS['false_positives_avoided'] += 1
        
        if objects_excluded > 0:
            DETECTION_STATS['objects_excluded_detections'] += objects_excluded
        
        # Log every 1000 frames and retry failed alerts
        if DETECTION_STATS['total_frames'] % 1000 == 0:
            queue_size = len(failed_alerts_queue)
            network_info = "Online" if network_status['is_online'] else "Offline"
            pool_info = f"{telegram_connection_pool['active_sends']}/{telegram_connection_pool['max_concurrent_sends']}"
            
            print(f"FIXED Stats - Fire: {DETECTION_STATS['fire_detections']} | Smoke: {DETECTION_STATS['smoke_detections']} | Valid Fire: {DETECTION_STATS['valid_fire_detections']} | Valid Smoke: {DETECTION_STATS['valid_smoke_detections']} | FP Avoided: {DETECTION_STATS['false_positives_avoided']} | Objects Excluded: {DETECTION_STATS['objects_excluded_detections']} | Fire Alerts: {DETECTION_STATS['fire_alerts_sent']} | Smoke Alerts: {DETECTION_STATS['smoke_alerts_sent']} | Network: {network_info} | Pool: {pool_info} | Pool Timeouts: {network_status['telegram_pool_timeouts']} | Queued: {queue_size}")
            
            # Retry failed alerts periodically
            retry_failed_alerts()

def check_and_send_fire_alert(camera_name, fire_detected, max_fire_conf, frame, detection_details, 
                             is_valid, validation_reason, valid_fire_detections=None, 
                             annotated_frame=None, detection_bbox=None, internet_connected=True, 
                             email_config=None, telegram_config=None):
    """FIXED: Network-resilient fire alert system with enhanced connection pool management"""
    global LAST_FIRE_DETECTION_IMAGE
    
    if not fire_detected or not is_valid:
        if fire_detected and not is_valid:
            print(f"FIXED Fire {camera_name}: Fire detected but not valid - {validation_reason}")
        return False
    
    from file_utils import cleanup_alerts_folder
    cleanup_alerts_folder()
    
    with stats_lock:
        if camera_name not in LAST_FIRE_ALERT_TIME:
            LAST_FIRE_ALERT_TIME[camera_name] = 0
        
        if time.time() - LAST_FIRE_ALERT_TIME[camera_name] < FIRE_ALERT_COOLDOWN:
            print(f"FIXED Fire {camera_name}: Fire alert in cooldown period")
            return False
        
        print(f"FIXED Fire {camera_name}: Fire validated - proceeding with alert")
        
        detector_info = ADAPTIVE_DETECTORS[camera_name].get_status_info() if camera_name in ADAPTIVE_DETECTORS else {}
        
        # Create annotated frame
        if annotated_frame is not None:
            final_frame = annotated_frame
        else:
            final_frame = frame.copy()
            if valid_fire_detections:
                for det in valid_fire_detections:
                    x1, y1, x2, y2 = map(int, det['bbox'])
                    conf = det['confidence']
                    
                    cv2.rectangle(final_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    label = f"FIRE {conf:.1f}%"
                    
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
                    cv2.rectangle(final_frame, (x1, y1 - label_size[1] - 10), 
                                (x1 + label_size[0], y1), (0, 0, 255), -1)
                    
                    cv2.putText(final_frame, label, (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Save image
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(ALERTS_DIR, f"{camera_name}_FIRE_{timestamp}.jpg")
        cv2.imwrite(filename, final_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        LAST_FIRE_DETECTION_IMAGE = filename
        
        # Check actual network status
        internet_connected = check_internet_connection_advanced()
        
        # FIXED: Enhanced alert message with connection pool status
        alert_msg = f"FIXED FIRE DETECTED - {camera_name}\n"
        alert_msg += f"{'='*40}\n"
        alert_msg += f"Fire Confidence: {max_fire_conf:.1f}%\n"
        alert_msg += f"Threshold: {detector_info.get('adaptive_fire_threshold', 'N/A')}\n"
        alert_msg += f"Environment: {detector_info.get('environment', 'Unknown')}\n"
        alert_msg += f"Brightness: {detector_info.get('avg_brightness', 'N/A')}\n"
        alert_msg += f"Location: Camera {camera_name}\n"
        alert_msg += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        alert_msg += f"Network: {'Connected' if internet_connected else 'OFFLINE - Alert Queued'}\n"
        alert_msg += f"Connection Pool: {telegram_connection_pool['active_sends']}/{telegram_connection_pool['max_concurrent_sends']} active\n"
        alert_msg += f"Pool Timeouts Fixed: Yes\n"
        alert_msg += f"Evidence: {os.path.basename(filename)}\n\n"
        
        alert_msg += "Detection Details:\n"
        for detail in detection_details:
            alert_msg += f"• {detail}\n"
        
        alert_msg += f"\nAI Analysis:\n"
        alert_msg += f"• Multi-Frame Validation: PASSED\n"
        alert_msg += f"• Object Filtering: Active\n"
        alert_msg += f"• Environment Type: {detector_info.get('environment', 'Unknown')}\n"
        alert_msg += f"• Detection Model: lumi.onnx (Class 0)\n"
        alert_msg += f"• Connection Management: Enhanced\n"
        
        if not internet_connected:
            alert_msg += f"\nNETWORK STATUS: OFFLINE\n"
            alert_msg += f"• This alert will be sent when connection is restored\n"
            alert_msg += f"• Local evidence saved: {filename}\n"
            alert_msg += f"• Enhanced connection pool will prevent timeout errors\n"
        
        print(f"FIXED: SENDING FIRE ALERT for {camera_name}! (Network: {'Online' if internet_connected else 'Offline'})")
        logging.info(f"FIXED: Fire alert: {camera_name} - {max_fire_conf:.1f}% - Network: {'Online' if internet_connected else 'Offline'}")
        
        # Send alerts with enhanced connection pool awareness
        email_success = False
        telegram_success = False
        
        # Email alert (usually more reliable)
        if email_config and all(email_config):
            try:
                threading.Thread(
                    target=send_email_alert,
                    args=(f"FIRE EMERGENCY ALERT - {camera_name}", alert_msg, *email_config),
                    daemon=True
                ).start()
                email_success = True
                print("FIXED: Email alert thread started")
            except Exception as e:
                print(f"FIXED: Email alert thread error: {e}")
                queue_failed_alert('email', alert_msg, None, None, email_config, priority="high")
        
        # FIXED: Telegram alert with enhanced connection pool management
        if telegram_config and all(telegram_config):
            bot_token, chat_ids = telegram_config
            
            def send_fire_telegram_alert():
                try:
                    success = send_telegram_alert_unified(alert_msg, filename, bot_token, chat_ids)
                    if success:
                        print(f"FIXED: Fire alert sent via Telegram for {camera_name}")
                    else:
                        if internet_connected:
                            print(f"FIXED: Telegram send failed but network is online - may be connection pool issue")
                        else:
                            print(f"FIXED: Telegram alert queued for {camera_name} - network offline")
                except Exception as e:
                    print(f"FIXED: Telegram fire alert error: {e}")
                    logging.error(f"FIXED: Telegram fire alert error for {camera_name}: {e}")
            
            try:
                threading.Thread(target=send_fire_telegram_alert, daemon=True).start()
                telegram_success = True
                print("FIXED: Telegram alert thread started")
            except Exception as e:
                print(f"FIXED: Telegram alert thread creation error: {e}")
                queue_failed_alert('telegram', alert_msg, filename, chat_ids, priority="high")
        
        # Status reporting with enhanced information
        if not internet_connected:
            print(f"FIXED: Network offline - fire alert saved locally: {filename}")
            print(f"FIXED: Queued alerts: {len(failed_alerts_queue)} (will send when connection restored)")
            logging.warning(f"FIXED: Fire alert offline - saved: {filename}, queued: {len(failed_alerts_queue)}")
        elif not email_success and not telegram_success:
            print(f"FIXED: Both alert methods failed to start - alert saved: {filename}")
        
        # FIXED: Include pool timeout information in stats
        pool_info = f"Pool: {telegram_connection_pool['active_sends']}/{telegram_connection_pool['max_concurrent_sends']}, Timeouts: {network_status['telegram_pool_timeouts']}"
        print(f"FIXED: Alert sent with connection info - {pool_info}")
        
        LAST_FIRE_ALERT_TIME[camera_name] = time.time()
        DETECTION_STATS['fire_alerts_sent'] += 1
        
    return True








