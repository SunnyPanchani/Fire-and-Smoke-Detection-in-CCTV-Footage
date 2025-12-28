# camera_snapshot.py - Camera Snapshot and Telegram Sender Module
import cv2
import os
import time
import threading
import logging
from datetime import datetime
from config_manager import load_camera_streams
from alerting import send_telegram_alert
from config import ALERTS_DIR

def capture_camera_snapshot(camera_name, camera_url, timeout=10):
    """
    Capture a single snapshot from a camera with robust error handling
    
    Args:
        camera_name (str): Name of the camera (e.g., 'Cam1')
        camera_url (str): RTSP URL of the camera
        timeout (int): Timeout in seconds for connection attempt
    
    Returns:
        tuple: (success, image_path, error_message)
    """
    cap = None
    temp_image_path = None
    
    try:
        # Create temporary filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_image_path = os.path.join(ALERTS_DIR, f"snapshot_{camera_name}_{timestamp}.jpg")
        
        # Initialize video capture with optimized settings
        cap = cv2.VideoCapture(camera_url)
        
        # Set timeout properties
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout * 1000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)  # 5 second read timeout
        
        if not cap.isOpened():
            return False, None, f"Connection failed to {camera_name}"
        
        # Optimized capture settings
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # Reduced for reliability
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 5)
        
        # Quick frame grab with minimal retries
        start_time = time.time()
        max_attempts = 5  # Reduced attempts for speed
        
        for attempt in range(max_attempts):
            if time.time() - start_time > timeout:
                return False, None, f"Timeout after {timeout}s"
            
            ret, frame = cap.read()
            
            if ret and frame is not None and frame.size > 0:
                # Quick validation
                if frame.shape[0] >= 100 and frame.shape[1] >= 100:
                    # Add camera name overlay
                    overlay_frame = add_camera_name_overlay(frame, camera_name)
                    
                    # Save with compression
                    success = cv2.imwrite(temp_image_path, overlay_frame, 
                                        [cv2.IMWRITE_JPEG_QUALITY, 85])
                    
                    if success and os.path.exists(temp_image_path):
                        file_size = os.path.getsize(temp_image_path)
                        if file_size > 500:  # Minimum 500 bytes
                            return True, temp_image_path, None
            
            time.sleep(0.1)  # Minimal delay
        
        return False, None, f"No valid frame captured after {max_attempts} attempts"
        
    except cv2.error as cv_error:
        return False, None, f"OpenCV error: {str(cv_error)}"
    except Exception as e:
        return False, None, f"Capture error: {str(e)}"
        
    finally:
        try:
            if cap:
                cap.release()
        except:
            pass
        try:
            cv2.destroyAllWindows()
        except:
            pass

def add_camera_name_overlay(frame, camera_name):
    """
    Add camera name overlay to the frame
    
    Args:
        frame: OpenCV frame
        camera_name: Name to overlay
    
    Returns:
        frame: Frame with overlay
    """
    try:
        # Create a copy to avoid modifying original
        overlay_frame = frame.copy()
        
        # Get frame dimensions
        height, width = overlay_frame.shape[:2]
        
        # Calculate text properties
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = max(0.8, min(2.0, width / 800))  # Scale based on image width
        thickness = max(2, int(font_scale * 2))
        
        # Get text size
        (text_width, text_height), baseline = cv2.getTextSize(camera_name, font, font_scale, thickness)
        
        # Position text in top-left corner with padding
        x = 20
        y = text_height + 30
        
        # Create background rectangle for text
        bg_x1 = x - 10
        bg_y1 = y - text_height - 10
        bg_x2 = x + text_width + 10
        bg_y2 = y + 10
        
        # Draw semi-transparent background
        overlay = overlay_frame.copy()
        cv2.rectangle(overlay, (bg_x1, bg_y1), (bg_x2, bg_y2), (0, 0, 0), -1)
        cv2.addWeighted(overlay_frame, 0.3, overlay, 0.7, 0, overlay_frame)
        
        # Draw white text
        cv2.putText(overlay_frame, camera_name, (x, y), font, font_scale, (255, 255, 255), thickness)
        
        # Add timestamp in bottom-right corner
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        (time_width, time_height), _ = cv2.getTextSize(timestamp, font, font_scale * 0.6, thickness - 1)
        
        time_x = width - time_width - 20
        time_y = height - 20
        
        # Background for timestamp
        cv2.rectangle(overlay, (time_x - 10, time_y - time_height - 5), 
                     (time_x + time_width + 10, time_y + 10), (0, 0, 0), -1)
        cv2.addWeighted(overlay_frame, 0.3, overlay, 0.7, 0, overlay_frame)
        
        cv2.putText(overlay_frame, timestamp, (time_x, time_y), font, 
                   font_scale * 0.6, (255, 255, 255), max(1, thickness - 1))
        
        return overlay_frame
        
    except Exception as e:
        print(f"Warning: Failed to add overlay to {camera_name}: {e}")
        return frame  # Return original frame if overlay fails

def send_snapshots_to_telegram(telegram_config=None, max_retries=2, silent_mode=False):
    """
    Capture snapshots from all cameras and send to Telegram with robust error handling
    
    Args:
        telegram_config (tuple): (bot_token, chat_id)
        max_retries (int): Maximum retry attempts for failed snapshots
        silent_mode (bool): If True, suppress detailed console output
    
    Returns:
        dict: Results summary
    """
    if not telegram_config or not all(telegram_config):
        if not silent_mode:
            print("Telegram configuration missing, skipping snapshots")
        return {"success": False, "error": "Telegram not configured"}
    
    bot_token, chat_id = telegram_config
    
    try:
        # Load camera streams from lan.txt
        camera_streams = load_camera_streams()
        
        if not camera_streams:
            return {"success": False, "error": "No cameras configured in lan.txt"}
        
        if not silent_mode:
            print(f"Starting snapshot capture for {len(camera_streams)} cameras...")
        
        results = {
            "total_cameras": len(camera_streams),
            "successful_snapshots": 0,
            "failed_snapshots": 0,
            "successful_sends": 0,
            "failed_sends": 0,
            "details": []
        }
        
        for camera_name, camera_url in camera_streams.items():
            camera_result = {
                "camera_name": camera_name,
                "snapshot_success": False,
                "send_success": False,
                "error_message": None,
                "attempts": 0
            }
            
            # Try to capture snapshot with retries
            snapshot_success = False
            image_path = None
            
            for attempt in range(1, max_retries + 1):
                camera_result["attempts"] = attempt
                
                success, img_path, error_msg = capture_camera_snapshot(camera_name, camera_url)
                
                if success:
                    snapshot_success = True
                    image_path = img_path
                    camera_result["snapshot_success"] = True
                    results["successful_snapshots"] += 1
                    if not silent_mode:
                        print(f"Snapshot captured from {camera_name}")
                    break
                else:
                    camera_result["error_message"] = error_msg
                    
                    if attempt < max_retries:
                        time.sleep(1)  # Shorter retry delay
            
            if not snapshot_success:
                if not silent_mode:
                    print(f"Failed to capture snapshot from {camera_name}: {camera_result['error_message']}")
                results["failed_snapshots"] += 1
                results["details"].append(camera_result)
                continue
            
            # Try to send to Telegram (no retries here, send_telegram_alert handles it)
            try:
                message = f"Camera Snapshot: {camera_name}\n"
                message += f"Captured: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                # Use existing telegram function which has built-in retries
                send_telegram_alert(message, image_path, bot_token, chat_id, retries=2)
                
                camera_result["send_success"] = True
                results["successful_sends"] += 1
                if not silent_mode:
                    print(f"{camera_name} snapshot sent to Telegram")
                
            except Exception as send_error:
                camera_result["send_success"] = False
                camera_result["error_message"] = f"Send failed: {str(send_error)}"
                results["failed_sends"] += 1
                if not silent_mode:
                    print(f"Failed to send {camera_name} snapshot: {send_error}")
            
            # Always delete image file immediately
            try:
                if image_path and os.path.exists(image_path):
                    os.remove(image_path)
            except Exception:
                pass  # Silent cleanup failure
            
            results["details"].append(camera_result)
        
        # Only send summary if there were successful sends
        if results["successful_sends"] > 0 and not silent_mode:
            summary_message = f"Camera Snapshot Summary\n"
            summary_message += f"Total: {results['total_cameras']} | "
            summary_message += f"Success: {results['successful_sends']} | "
            summary_message += f"Failed: {results['failed_snapshots'] + results['failed_sends']}\n"
            summary_message += f"Completed: {datetime.now().strftime('%H:%M:%S')}"
            
            try:
                send_telegram_alert(summary_message, None, bot_token, chat_id, retries=1)
            except Exception:
                pass  # Silent summary failure
        
        # Log the operation
        logging.info(f"Camera snapshots: {results['successful_sends']}/{results['total_cameras']} sent successfully")
        
        results["success"] = True
        return results
        
    except Exception as e:
        error_msg = f"Snapshot operation error: {str(e)}"
        if not silent_mode:
            print(f"Error in snapshot operation: {e}")
        logging.error(error_msg)
        return {"success": False, "error": error_msg}

def periodic_snapshot_service(telegram_config, interval_hours=6):
    """
    Background service that takes camera snapshots periodically
    
    Args:
        telegram_config (tuple): (bot_token, chat_id)
        interval_hours (int): Hours between snapshot captures
    """
    if not telegram_config:
        return
    
    interval_seconds = interval_hours * 3600  # Convert to seconds
    
    while True:
        try:
            # Wait for the interval
            time.sleep(interval_seconds)
            
            # Take snapshots
            print(f"Running periodic camera snapshots (every {interval_hours}h)...")
            result = send_snapshots_to_telegram(telegram_config, max_retries=2, silent_mode=True)
            
            if result["success"] and result["successful_sends"] > 0:
                print(f"Periodic snapshots sent: {result['successful_sends']}/{result['total_cameras']} cameras")
                logging.info(f"Periodic snapshots completed: {result['successful_sends']}/{result['total_cameras']} cameras")
            
        except Exception as e:
            print(f"Periodic snapshot error: {e}")
            logging.error(f"Periodic snapshot service error: {e}")
            time.sleep(300)  # Wait 5 minutes before retrying

def capture_and_send_snapshots_threaded(telegram_config=None):
    """
    Threaded version of snapshot capture and send
    This can be called without blocking the main detection system
    """
    def run_snapshot_task():
        try:
            print("Starting threaded snapshot capture...")
            result = send_snapshots_to_telegram(telegram_config)
            
            if result["success"]:
                print("Threaded snapshot operation completed successfully")
            else:
                print(f"Threaded snapshot operation failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"Exception in threaded snapshot task: {e}")
            logging.error(f"Exception in threaded snapshot task: {e}")
    
    # Start the snapshot task in a separate thread
    snapshot_thread = threading.Thread(
        target=run_snapshot_task,
        daemon=True,
        name="SnapshotCapture"
    )
    snapshot_thread.start()
    
    print("Snapshot capture started in background thread")
    return snapshot_thread

# Test function for standalone snapshot testing
def test_snapshot_system():
    """Test function to verify snapshot system works"""
    from config_manager import load_telegram_config
    
    print("Testing snapshot system...")
    
    try:
        # Load Telegram config
        telegram_config = load_telegram_config()
        
        if not telegram_config or not all(telegram_config):
            print("Test failed: Telegram not configured")
            return False
        
        # Run snapshot capture
        result = send_snapshots_to_telegram(telegram_config)
        
        if result["success"]:
            print("Test completed successfully!")
            return True
        else:
            print(f"Test failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"Test exception: {e}")
        return False

if __name__ == "__main__":
    # Test the snapshot system if run directly
    test_snapshot_system()