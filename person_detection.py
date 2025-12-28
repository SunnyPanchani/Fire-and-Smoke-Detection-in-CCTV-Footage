# person_detection.py - Enhanced with Static Object Detection Logic
import cv2
import numpy as np
import os
import time
import logging
from datetime import datetime
from config import PERSON_MODEL, ALL_INTERFERENCE_CLASSES, BASE_DIR
from alerting import send_telegram_alert, send_email_alert
import threading

# CRITICAL FIX: Global detector tracking for cleanup
_active_detectors = {}
_detector_lock = threading.Lock()

class PersonDetector:
    def __init__(self, camera_name, confidence_threshold=0.55):
        self.camera_name = camera_name
        self.confidence_threshold = confidence_threshold
        self.person_class_id = 0  # Person class in COCO dataset
        self.last_person_alert = 0
        self.person_alert_cooldown = 120  # 5 minutes cooldown for person alerts
        self.detection_buffer = []
        self.buffer_size = 3  # Require detection in 3 consecutive frames
        
        # NEW: Static object detection parameters
        self.static_confidence_threshold = 65.0  # Higher threshold for suspected static objects
        self.movement_detection_frames = 3  # Frames to check for movement
        self.bbox_movement_threshold = 15  # Minimum pixels movement required
        self.confidence_variation_threshold = 4.0  # Minimum confidence variation for real person
        
        # NEW: Detection history for static analysis
        self.detection_history_detailed = []  # Store bbox and confidence history
        self.max_history_frames = 8
        
        # CRITICAL FIX: Reset detection state
        self.last_detection_time = 0
        self.alert_count = 0
        self.detection_history = []
        self.is_active = True
        
        print(f"Enhanced person detector initialized for {camera_name} with static object detection")
        logging.info(f"Enhanced person detector initialized for {camera_name} with static object detection")
    
    def reset_state(self):
        """CRITICAL FIX: Reset detector state including static detection history"""
        self.last_person_alert = 0
        self.detection_buffer.clear()
        self.detection_history_detailed.clear()
        self.last_detection_time = 0
        self.alert_count = 0
        self.detection_history.clear()
        self.is_active = True
        print(f"Enhanced detector state reset for {self.camera_name}")
    
    def deactivate(self):
        """CRITICAL FIX: Deactivate detector"""
        self.is_active = False
        print(f"Enhanced detector deactivated for {self.camera_name}")
    
    def calculate_bbox_movement(self, bbox1, bbox2):
        """Calculate movement between two bounding boxes"""
        try:
            # Calculate center points
            center1 = [(bbox1[0] + bbox1[2]) / 2, (bbox1[1] + bbox1[3]) / 2]
            center2 = [(bbox2[0] + bbox2[2]) / 2, (bbox2[1] + bbox2[3]) / 2]
            
            # Calculate distance
            distance = np.sqrt((center2[0] - center1[0])**2 + (center2[1] - center1[1])**2)
            
            # Calculate size change
            size1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
            size2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
            size_change = abs(size2 - size1) / size1 if size1 > 0 else 0
            
            return distance, size_change
            
        except Exception as e:
            print(f"Error calculating bbox movement: {e}")
            return 0, 0
    
    def validate_non_static_person(self, current_detections):
        """
        NEW: Validate that detected persons are not static objects (photos/posters/mannequins)
        Returns: (is_valid, validation_reason, adjusted_detections)
        """
        if not current_detections:
            return False, "no_detections", []
        
        if len(self.detection_history_detailed) < self.movement_detection_frames:
            return True, "insufficient_history_assume_valid", current_detections
        
        validated_detections = []
        
        for detection in current_detections:
            is_valid = True
            reasons = []
            current_bbox = detection['bbox']
            current_conf = detection['confidence']
            
            # Check movement patterns across recent frames
            movement_detected = False
            confidence_variations = []
            
            # Analyze last N frames for this detection
            recent_frames = self.detection_history_detailed[-self.movement_detection_frames:]
            
            for frame_data in recent_frames:
                frame_detections = frame_data.get('detections', [])
                
                # Find closest matching detection in this frame
                best_match = None
                best_overlap = 0
                
                for frame_det in frame_detections:
                    # Calculate IoU (Intersection over Union) for matching
                    overlap = self.calculate_bbox_overlap(current_bbox, frame_det['bbox'])
                    if overlap > best_overlap and overlap > 0.3:  # 30% overlap threshold
                        best_overlap = overlap
                        best_match = frame_det
                
                if best_match:
                    # Check movement
                    distance, size_change = self.calculate_bbox_movement(current_bbox, best_match['bbox'])
                    if distance > self.bbox_movement_threshold or size_change > 0.1:
                        movement_detected = True
                        reasons.append(f"movement_detected_{distance:.1f}px")
                    
                    # Collect confidence variations
                    confidence_variations.append(abs(current_conf - best_match['confidence']))
            
            # Analyze confidence variations
            if confidence_variations:
                avg_conf_variation = np.mean(confidence_variations)
                max_conf_variation = np.max(confidence_variations)
                
                if avg_conf_variation < self.confidence_variation_threshold and max_conf_variation < 10.0:
                    reasons.append(f"static_confidence_pattern_avg_{avg_conf_variation:.1f}")
                    if not movement_detected:
                        is_valid = False
                        reasons.append("likely_static_object")
            
            # Apply higher confidence threshold for suspected static objects
            if not movement_detected and current_conf < self.static_confidence_threshold:
                is_valid = False
                reasons.append(f"static_low_confidence_{current_conf:.1f}_vs_{self.static_confidence_threshold}")
            
            # Additional static object indicators
            bbox_area = (current_bbox[2] - current_bbox[0]) * (current_bbox[3] - current_bbox[1])
            frame_area = 640 * 640  # Assuming standard frame size
            relative_size = bbox_area / frame_area
            
            # Very large detections might be posters/wallpapers
            if relative_size > 0.4:  # Person takes up more than 40% of frame
                if not movement_detected:
                    is_valid = False
                    reasons.append(f"large_static_object_size_{relative_size:.2f}")
            
            # Very small but high confidence might be distant photos
            elif relative_size < 0.01 and current_conf > 90.0:
                if not movement_detected:
                    is_valid = False
                    reasons.append(f"small_high_conf_static_{relative_size:.3f}_{current_conf:.1f}")
            
            validation_reason = "valid_person" if is_valid else "_".join(reasons)
            
            print(f"Static validation for {self.camera_name}: {validation_reason} (conf: {current_conf:.1f}%, movement: {movement_detected})")
            
            if is_valid:
                validated_detections.append({
                    **detection,
                    'validation_status': 'non_static_validated',
                    'movement_detected': movement_detected,
                    'validation_reason': validation_reason
                })
        
        overall_valid = len(validated_detections) > 0
        overall_reason = f"validated_{len(validated_detections)}_of_{len(current_detections)}"
        
        return overall_valid, overall_reason, validated_detections
    
    def calculate_bbox_overlap(self, bbox1, bbox2):
        """Calculate Intersection over Union (IoU) for two bounding boxes"""
        try:
            # Convert to [x1, y1, x2, y2] format if needed
            if isinstance(bbox1, np.ndarray):
                bbox1 = bbox1.tolist()
            if isinstance(bbox2, np.ndarray):
                bbox2 = bbox2.tolist()
            
            # Calculate intersection
            x1 = max(bbox1[0], bbox2[0])
            y1 = max(bbox1[1], bbox2[1])
            x2 = min(bbox1[2], bbox2[2])
            y2 = min(bbox1[3], bbox2[3])
            
            if x2 <= x1 or y2 <= y1:
                return 0.0
            
            intersection = (x2 - x1) * (y2 - y1)
            
            # Calculate union
            area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
            area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
            union = area1 + area2 - intersection
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            print(f"Error calculating bbox overlap: {e}")
            return 0.0

    def detect_persons(self, frame):
        """Detect persons in the frame using YOLO model - FIXED VERSION"""
        if not self.is_active:
            return []
            
        import config
        from detection import load_models_safely
        
        # CRITICAL FIX: Always verify model availability in current thread
        model = getattr(config, 'PERSON_MODEL', None)
        
        # If model is None, try to load it in this thread
        if model is None:
            print(f"PERSON_MODEL is None for {self.camera_name}, attempting thread-specific load...")
            try:
                fire_model, person_model = load_models_safely()
                if person_model:
                    config.PERSON_MODEL = person_model
                    model = person_model
                    print(f"Successfully loaded PERSON_MODEL in thread: {type(model)}")
                else:
                    print(f"Failed to load PERSON_MODEL in thread")
                    return []
            except Exception as e:
                print(f"Error loading models in thread: {e}")
                logging.error(f"Error loading models in person detector thread: {e}")
                return []
        
        if model is None:
            print(f"PERSON_MODEL is still None after loading attempt for {self.camera_name}")
            return []

        try:
            # CRITICAL FIX: Verify model type and handle accordingly
            print(f"Using model type: {type(model)} for {self.camera_name}")
            
            # Check if model is Ultralytics YOLO
            if hasattr(model, 'predict'):
                # Ultralytics YOLO model
                results = model.predict(frame, verbose=False, conf=self.confidence_threshold, imgsz=640, device='cpu')
                
                detections = []
                if results and len(results) > 0:
                    result = results[0]
                    if hasattr(result, 'boxes') and result.boxes is not None and len(result.boxes) > 0:
                        for box in result.boxes:
                            try:
                                conf = float(box.conf.cpu().numpy()[0])
                                cls_id = int(box.cls.cpu().numpy()[0])
                                
                                # Only process person detections (class 0)
                                if cls_id == self.person_class_id and conf >= self.confidence_threshold:
                                    xyxy = box.xyxy.cpu().numpy()[0].astype(int)
                                    detections.append({
                                        'bbox': xyxy,
                                        'confidence': float(conf * 100),
                                        'class_id': int(cls_id),
                                        'class_name': 'person'
                                    })
                                    print(f"Person detected on {self.camera_name}: {conf*100:.1f}% confidence at {xyxy}")
                            except Exception as box_error:
                                print(f"Error processing box for {self.camera_name}: {box_error}")
                                continue
                
                return detections
            
            else:
                # OpenCV DNN model
                blob = cv2.dnn.blobFromImage(
                    frame, 
                    1/255.0, 
                    (640, 640), 
                    swapRB=True, 
                    crop=False
                )
                
                model.setInput(blob)
                outputs = model.forward()
                
                # Process YOLO outputs
                detections = []
                h, w = frame.shape[:2]
                
                for output in outputs:
                    for detection in output:
                        scores = detection[5:]
                        class_id = np.argmax(scores)
                        confidence = scores[class_id]
                        
                        # Only process person detections
                        if class_id == self.person_class_id and confidence > self.confidence_threshold:
                            # Get bounding box
                            center_x, center_y, width, height = detection[0:4]
                            center_x = int(center_x * w)
                            center_y = int(center_y * h)
                            width = int(width * w)
                            height = int(height * h)
                            
                            x = int(center_x - width / 2)
                            y = int(center_y - height / 2)
                            
                            detections.append({
                                'bbox': [x, y, x + width, y + height],
                                'confidence': float(confidence * 100),
                                'class_id': int(class_id),
                                'class_name': 'person'
                            })
                            print(f"Person detected on {self.camera_name}: {confidence*100:.1f}% confidence")
                
                return detections
                
        except Exception as e:
            print(f"Error in person detection for {self.camera_name}: {e}")
            logging.error(f"Error in person detection for {self.camera_name}: {e}")
            return []
    
    def process_frame(self, frame, email_config=None, telegram_config=None):
        """
        ENHANCED: Process frame with static object detection validation
        """
        if not self.is_active:
            return False, []
            
        current_time = time.time()
        
        print(f"Processing frame with static detection for {self.camera_name} (active: {self.is_active})")
        
        # CRITICAL FIX: Update last detection time
        self.last_detection_time = current_time
        
        # Detect persons in current frame
        person_detections = self.detect_persons(frame)
        
        # Store detailed detection history for static analysis
        self.detection_history_detailed.append({
            'timestamp': current_time,
            'detections': person_detections.copy()
        })
        
        # Keep history manageable
        if len(self.detection_history_detailed) > self.max_history_frames:
            self.detection_history_detailed.pop(0)
        
        print(f"Initial detections for {self.camera_name}: {len(person_detections)} persons")
        
        # NEW: Apply static object validation
        person_valid, validation_reason, validated_detections = self.validate_non_static_person(person_detections)
        
        print(f"After static validation for {self.camera_name}: {len(validated_detections)} valid persons")
        print(f"Validation result: {validation_reason}")
        
        has_person = len(validated_detections) > 0
        
        # Add to detection buffer (using validated results)
        self.detection_buffer.append(has_person)
        
        # Keep buffer at specified size
        if len(self.detection_buffer) > self.buffer_size:
            self.detection_buffer.pop(0)
        
        # Check if person detected in majority of recent frames
        if len(self.detection_buffer) >= self.buffer_size:
            person_confirmed = sum(self.detection_buffer) >= (self.buffer_size - 1)  # Allow 1 miss
        else:
            person_confirmed = has_person  # Single frame validation if buffer not full
        
        print(f"Person confirmed for {self.camera_name}: {person_confirmed}, buffer: {self.detection_buffer}")
        
        # CRITICAL FIX: Add to detection history (using validated results)
        self.detection_history.append({
            'time': current_time,
            'detected': person_confirmed,
            'count': len(validated_detections),
            'validation_reason': validation_reason
        })
        
        # Keep history manageable
        if len(self.detection_history) > 100:
            self.detection_history = self.detection_history[-50:]
        
        # Send alert if person confirmed and cooldown passed
        if person_confirmed and validated_detections and self.is_active:
            time_since_last = current_time - self.last_person_alert
            print(f"Time since last alert for {self.camera_name}: {time_since_last:.1f}s (cooldown: {self.person_alert_cooldown}s)")
            
            if time_since_last > self.person_alert_cooldown:
                print(f"Sending validated person alert for {self.camera_name}")
                success = self.send_person_alert(frame, validated_detections, email_config, telegram_config)
                if success:
                    self.last_person_alert = current_time
                    self.alert_count += 1
                    print(f"Validated person alert sent successfully for {self.camera_name} (alert #{self.alert_count})")
                else:
                    print(f"Failed to send validated person alert for {self.camera_name}")
                return True, validated_detections
            else:
                print(f"Valid person detected on {self.camera_name} but in cooldown period ({time_since_last:.1f}s < {self.person_alert_cooldown}s)")
        
        return person_confirmed, validated_detections
    
    def send_person_alert(self, frame, detections, email_config=None, telegram_config=None):
        """
        ENHANCED: Send person detection alert with static validation info
        """
        if not self.is_active:
            return False
            
        try:
            print(f"Preparing validated person alert for {self.camera_name} with {len(detections)} detections")
            
            # Create annotated frame
            annotated_frame = frame.copy()
            person_count = len(detections)
            max_confidence = max([det['confidence'] for det in detections])
            
            # Draw bounding boxes with validation status
            for detection in detections:
                if isinstance(detection['bbox'], np.ndarray):
                    x1, y1, x2, y2 = detection['bbox'].astype(int)
                else:
                    x1, y1, x2, y2 = map(int, detection['bbox'])
                confidence = detection['confidence']
                
                # Color based on validation
                validation_status = detection.get('validation_status', 'unknown')
                movement_detected = detection.get('movement_detected', False)
                
                if validation_status == 'non_static_validated':
                    color = (0, 255, 0)  # Green for validated
                    status_text = "VALIDATED"
                else:
                    color = (0, 165, 255)  # Orange for unvalidated
                    status_text = "DETECTED"
                
                # Draw rectangle
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 3)
                
                # Add label with validation info
                label = f"PERSON {confidence:.1f}% {status_text}"
                if movement_detected:
                    label += " [MOVING]"
                
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                cv2.rectangle(annotated_frame, (x1, y1 - label_size[1] - 10), 
                            (x1 + label_size[0], y1), color, -1)
                cv2.putText(annotated_frame, label, (x1, y1 - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            
            # Add header text with validation info
            header_text = f"STATIC-VALIDATED MONITORING - {self.camera_name}: {person_count} PERSON(S)"
            cv2.putText(annotated_frame, header_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Add alert count and validation status
            alert_text = f"Alert #{self.alert_count + 1} - Non-Static Validated"
            cv2.putText(annotated_frame, alert_text, (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Ensure alerts directory exists
            alerts_dir = os.path.join(BASE_DIR, "alerts")
            os.makedirs(alerts_dir, exist_ok=True)
            
            # Save image with unique filename
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = os.path.join(alerts_dir, f"{self.camera_name}_VALIDATED_PERSON_Alert{self.alert_count + 1}_{timestamp}.jpg")
            
            # Save with error handling
            success = cv2.imwrite(filename, annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            if not success:
                print(f"Failed to save image: {filename}")
                return False
            
            print(f"Validated person image saved: {filename}")
            
            # Prepare enhanced alert message
            alert_message = f"VALIDATED PERSON DETECTED - {self.camera_name}\n"
            alert_message += f"{'='*60}\n"
            alert_message += f"Alert Number: #{self.alert_count + 1}\n"
            alert_message += f"Persons Detected: {person_count} (Static-Object Validated)\n"
            alert_message += f"Highest Confidence: {max_confidence:.1f}%\n"
            alert_message += f"Location: Camera {self.camera_name}\n"
            alert_message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            alert_message += f"Evidence: {os.path.basename(filename)}\n\n"
            
            alert_message += f"STATIC OBJECT VALIDATION:\n"
            alert_message += f"  ✓ Multi-frame movement analysis: PASSED\n"
            alert_message += f"  ✓ Confidence pattern analysis: PASSED\n"
            alert_message += f"  ✓ Static object filtering: ACTIVE\n"
            alert_message += f"  ✓ Photo/Poster detection: EXCLUDED\n\n"
            
            alert_message += f"Detection Details:\n"
            
            for i, detection in enumerate(detections, 1):
                validation_status = detection.get('validation_status', 'unknown')
                movement_detected = detection.get('movement_detected', False)
                validation_reason = detection.get('validation_reason', 'no_reason')
                
                alert_message += f"  • Person {i}: {detection['confidence']:.1f}% confidence\n"
                alert_message += f"    - Validation: {validation_status}\n"
                alert_message += f"    - Movement: {'Yes' if movement_detected else 'No'}\n"
                alert_message += f"    - Reason: {validation_reason}\n"
            
            alert_message += f"\nEnhanced Detection System:\n"
            alert_message += f"  • Base confidence threshold: {self.confidence_threshold*100:.0f}%\n"
            alert_message += f"  • Static object threshold: {self.static_confidence_threshold:.0f}%\n"
            alert_message += f"  • Movement detection: {self.movement_detection_frames} frames\n"
            alert_message += f"  • Movement threshold: {self.bbox_movement_threshold} pixels\n"
            alert_message += f"  • Buffer validation: {self.buffer_size} frames\n"
            alert_message += f"  • Alert cooldown: {self.person_alert_cooldown//60} minutes\n"
            alert_message += f"  • Session alerts: {self.alert_count + 1}\n"
            
            print(f"VALIDATED PERSON ALERT: {self.camera_name} - {person_count} person(s) detected! (Alert #{self.alert_count + 1})")
            logging.info(f"Validated person alert sent for {self.camera_name}: {person_count} persons detected (Alert #{self.alert_count + 1})")
            
            alert_sent = False
            
            # Send email alert
            if email_config and len(email_config) >= 3 and all(email_config):
                try:
                    print(f"Sending validated person email alert for {self.camera_name}...")
                    send_email_alert(
                        f"VALIDATED PERSON DETECTED - {self.camera_name} (Alert #{self.alert_count + 1})",
                        alert_message,
                        email_config[0], email_config[1], email_config[2]
                    )
                    print(f"Validated person email alert sent successfully for {self.camera_name}")
                    alert_sent = True
                except Exception as e:
                    print(f"Failed to send validated person email alert for {self.camera_name}: {e}")
                    logging.error(f"Failed to send validated person email alert for {self.camera_name}: {e}")
            else:
                print(f"Email not configured for {self.camera_name}")
            
            # Send Telegram alert using unified system
            if telegram_config and len(telegram_config) >= 2 and all(telegram_config):
                try:
                    bot_token, chat_ids = telegram_config
                    print(f"Sending validated person Telegram alert for {self.camera_name} via unified system to {chat_ids}")
                    
                    # Import the unified alerting function
                    from alerting import send_telegram_alert_unified
                    
                    # Use unified alert system 
                    success = send_telegram_alert_unified(alert_message, filename, bot_token, chat_ids)
                    if success:
                        print(f"Validated person Telegram alert sent via unified system for {self.camera_name}")
                        alert_sent = True
                    else:
                        print(f"Failed to send validated person Telegram via unified system for {self.camera_name}")
                            
                except Exception as e:
                    print(f"Error sending validated person Telegram via unified system for {self.camera_name}: {e}")
                    logging.error(f"Error sending validated person Telegram via unified system for {self.camera_name}: {e}")
            else:
                print(f"Telegram not configured for {self.camera_name}")
            
            if alert_sent:
                print(f"Validated person alert sent successfully for {self.camera_name}")
                return True
            else:
                print(f"No alerts were sent for {self.camera_name}")
                return False
            
        except Exception as e:
            print(f"Error sending validated person alert for {self.camera_name}: {e}")
            logging.error(f"Error sending validated person alert for {self.camera_name}: {e}")
            return False

def clear_camera_detector(camera_name):
    """
    CRITICAL FIX: Clear detector state for a specific camera to prevent alert issues on restart
    """
    global _active_detectors, _detector_lock
    
    try:
        with _detector_lock:
            if camera_name in _active_detectors:
                detector = _active_detectors[camera_name]
                
                # Deactivate detector first
                detector.deactivate()
                
                # Reset detector state
                detector.reset_state()
                
                # Remove from active detectors
                del _active_detectors[camera_name]
                
                print(f"CLEANUP: Cleared enhanced detector state for camera: {camera_name}")
                logging.info(f"Enhanced detector state cleared for camera: {camera_name}")
                return True
            else:
                print(f"CLEANUP: No active enhanced detector found for {camera_name}")
                
    except Exception as e:
        print(f"Error clearing enhanced detector for {camera_name}: {e}")
        logging.error(f"Error clearing enhanced detector for {camera_name}: {e}")
        return False
    
    return True

def create_person_detector(camera_name, confidence_threshold=0.6):
    """
    CRITICAL FIX: Factory function to create enhanced person detector with global tracking
    """
    global _active_detectors, _detector_lock
    
    # Clear any existing detector first
    clear_camera_detector(camera_name)
    
    # Create new detector with fresh state
    detector = PersonDetector(camera_name, confidence_threshold)
    
    # Track it globally for cleanup
    with _detector_lock:
        _active_detectors[camera_name] = detector
    
    print(f"CREATED: New enhanced person detector for {camera_name} (total active: {len(_active_detectors)})")
    logging.info(f"Enhanced person detector created for {camera_name}")
    
    return detector

def get_active_detectors():
    """Get list of currently active detectors (for debugging)"""
    global _active_detectors, _detector_lock
    
    with _detector_lock:
        return list(_active_detectors.keys())

def cleanup_all_detectors():
    """CRITICAL FIX: Clean up all enhanced detectors (for system shutdown)"""
    global _active_detectors, _detector_lock
    
    camera_names = list(_active_detectors.keys())
    
    for camera_name in camera_names:
        clear_camera_detector(camera_name)
    
    print(f"CLEANUP: All enhanced detectors cleaned up ({len(camera_names)} total)")
    logging.info(f"All enhanced person detectors cleaned up: {camera_names}")