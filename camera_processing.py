# camera_processing.py - Fixed Fire Detection System with Enhanced Static Object Detection
import cv2
import time
import sys
import logging
import os
from datetime import datetime

import config
from config import (ADAPTIVE_DETECTORS, BRIGHTNESS_DETECTORS, ALERTS_DIR)
from detection import detect_high_confidence_objects, enhanced_calculate_adaptive_threshold
from adaptive_detection import ImprovedAdaptiveFireSmokeDetector, BrightnessAwareDetector
from alerting import check_and_send_fire_alert, log_detection_stats
from system_utils import grab_real_time_frame, check_memory_usage, monitor_internet_connection
from person_detection import create_person_detector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

def process_person_detection_only(camera_name, camera_url, email_config, telegram_config, stop_callback=None):
    """
    FIXED: Process camera feed for person detection only with stop control
    
    Parameters:
    - stop_callback: Function that returns True when this process should stop
    """
    import logging
    from system_utils import grab_real_time_frame, check_memory_usage
    import config
    
    print(f"Starting CONTROLLABLE person detection monitoring for {camera_name}")
    logging.info(f"Starting controllable person detection monitoring for {camera_name}")
    
    # CRITICAL FIX: Check and load models if needed
    print(f"DEBUG: Checking PERSON_MODEL status...")
    print(f"DEBUG: config.PERSON_MODEL = {config.PERSON_MODEL}")
    print(f"DEBUG: PERSON_MODEL is None: {config.PERSON_MODEL is None}")
    
    if config.PERSON_MODEL is None:
        print(f"PERSON_MODEL is None, attempting to load...")
        try:
            from detection import load_models_safely
            fire_model, person_model = load_models_safely()
            if person_model:
                config.PERSON_MODEL = person_model
                print(f"Successfully loaded PERSON_MODEL in thread: {type(person_model)}")
            else:
                print(f"Failed to load PERSON_MODEL in thread")
                return
        except Exception as e:
            print(f"Error loading models in person detection thread: {e}")
            return
    else:
        print(f"PERSON_MODEL already loaded: {type(config.PERSON_MODEL)}")
    
    # Create person detector
    person_detector = create_person_detector(camera_name, confidence_threshold=0.6)
    
    # Camera connection variables
    cap = None
    connection_failures = 0
    max_connection_failures = 5
    frame_count = 0
    
    try:
        # CRITICAL FIX: Loop with stop control
        while True:
            # CRITICAL FIX: Check stop signal every loop iteration
            if stop_callback and stop_callback():
                print(f"Stop signal received for {camera_name} person detection")
                logging.info(f"Stop signal received for {camera_name} person detection")
                break
            
            # Initialize camera connection
            if cap is None or not cap.isOpened():
                try:
                    print(f"Connecting to {camera_name} for person detection...")
                    cap = cv2.VideoCapture(camera_url)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  
                    cap.set(cv2.CAP_PROP_FPS, 5)  # Lower FPS for person detection
                    
                    if not cap.isOpened():
                        raise Exception("Failed to open camera stream")
                    
                    print(f"Connected to {camera_name} for person detection")
                    connection_failures = 0
                    
                except Exception as e:
                    connection_failures += 1
                    print(f"Camera connection failed for {camera_name}: {e}")
                    logging.error(f"Camera connection failed for {camera_name}: {e}")
                    
                    if connection_failures >= max_connection_failures:
                        print(f"Max connection failures reached for {camera_name}")
                        break
                    
                    # CRITICAL FIX: Check stop signal during wait
                    for i in range(10):  # 10 second wait, but check stop every second
                        if stop_callback and stop_callback():
                            print(f"Stop signal during connection retry for {camera_name}")
                            return
                        time.sleep(1)
                    continue
            
            # Capture frame
            frame = grab_real_time_frame(cap, max_flush=5)
            if frame is None:
                print(f"Failed to get frame from {camera_name}")
                cap.release()
                cap = None
                
                # CRITICAL FIX: Check stop signal during frame failure wait
                for i in range(2):  # 2 second wait, but check stop every second
                    if stop_callback and stop_callback():
                        print(f"Stop signal during frame failure for {camera_name}")
                        return
                    time.sleep(1)
                continue
            
            frame_count += 1
            
            # Process frame for person detection
            try:
                person_detected, detections = person_detector.process_frame(
                    frame, email_config, telegram_config
                )
                
                # Optional: Display detection status (reduce spam)
                if person_detected and detections:
                    print(f"Person detection active on {camera_name}: {len(detections)} person(s)")
                
            except Exception as e:
                logging.error(f"Error processing frame for {camera_name}: {e}")
                print(f"Error processing frame for {camera_name}: {e}")
            
            # Memory check
            if check_memory_usage():
                print(f"High memory usage detected during {camera_name} processing")
            
            # CRITICAL FIX: Check stop signal before sleep
            if stop_callback and stop_callback():
                print(f"Stop signal before sleep for {camera_name}")
                break
            
            # Control frame rate - slower for person detection
            time.sleep(1.0)  # 1 FPS for person detection
            
            # CRITICAL FIX: Periodic stop check (every 10 frames)
            if frame_count % 10 == 0:
                if stop_callback and stop_callback():
                    print(f"Periodic stop check triggered for {camera_name}")
                    break
    
    except KeyboardInterrupt:
        print(f"Person detection stopped for {camera_name}")
        logging.info(f"Person detection stopped for {camera_name}")
        
    except Exception as e:
        print(f"Critical error in person detection for {camera_name}: {e}")
        logging.error(f"Critical error in person detection for {camera_name}: {e}")
        
    finally:
        if cap:
            cap.release()
        print(f"Camera {camera_name} person detection monitoring ended cleanly")
        logging.info(f"Camera {camera_name} person detection monitoring ended cleanly")

def enhanced_fire_detection_with_algorithm_details(fire_results, person_results, camera_name, frame, save_annotated=True):
    """
    ENHANCED: Complete algorithm pipeline with EARLY static object detection
    
    ALGORITHM PIPELINE:
    1. Initial Confidence Check (20% minimum)
    2. EARLY Static Object Detection (NEW POSITION)
    3. Brightness Analysis
    4. Adaptive Threshold Calculation
    5. Static Detection Analysis
    6. Fire Characteristics Validation
    7. Multi-Frame Validation (Simplified: 18 frames)
    """
    fire_detected = False
    max_fire_conf = 0
    detection_details = []
    valid_fire_detections = []
    suppressed_detections = []
    algorithm_details = []
    
    try:
        base_fire_threshold = 30.0
        annotated_frame = frame.copy()
        
        # Initialize detectors
        if camera_name not in BRIGHTNESS_DETECTORS:
            BRIGHTNESS_DETECTORS[camera_name] = BrightnessAwareDetector(camera_name)
        if camera_name not in ADAPTIVE_DETECTORS:
            ADAPTIVE_DETECTORS[camera_name] = ImprovedAdaptiveFireSmokeDetector(camera_name)
        
        brightness_detector = BRIGHTNESS_DETECTORS[camera_name]
        adaptive_detector = ADAPTIVE_DETECTORS[camera_name]

        # Initialize counters if needed
        adaptive_detector.initialize_counters_if_needed()

        print(f"\n=== FRAME ANALYSIS START for {camera_name} ===")
        
        # ALGORITHM 1: High confidence object detection
        try:
            high_confidence_objects = detect_high_confidence_objects(person_results, confidence_threshold=55.0)
            if high_confidence_objects is None:
                high_confidence_objects = []
            print(f"  Found {len(high_confidence_objects)} high confidence objects")
            algorithm_details.append(f"Object Detection: {len(high_confidence_objects)} objects detected")
        except Exception as e:
            print(f"  Object detection failed: {e}")
            high_confidence_objects = []
            algorithm_details.append(f"Object Detection: FAILED - {str(e)}")

        # ALGORITHM 2: Frame data storage
        try:
            adaptive_detector.store_frame_data(frame, [], high_confidence_objects)
        except Exception as e:
            print(f"  Frame data storage failed: {e}")

        # Process fire detections
        if fire_results is not None:
            for result in fire_results:
                if not hasattr(result, 'boxes') or result.boxes is None or len(result.boxes) == 0:
                    continue

                for box in result.boxes:
                    try:
                        conf = float(box.conf.item() * 100)
                        cls_id = int(box.cls.item())
                        xyxy = box.xyxy[0].cpu().numpy().astype(int)

                        # Only process fire detections (cls_id == 0)
                        if cls_id != 0:
                            continue
                        
                        detection_type = "fire"
                        is_excluded = False
                        exclusion_reason = ""
                        frame_algorithm_details = []

                        # ALGORITHM 3: Minimum confidence check
                        if conf < 20.0:
                            is_excluded = True
                            exclusion_reason = f"below_minimum_{conf:.1f}%"
                        else:
                            print(f"  Fire {conf:.1f}% above minimum 20%")
                            frame_algorithm_details.append(f"Min Confidence Check: PASSED ({conf:.1f}% >= 20%)")

                        # ALGORITHM 4: EARLY Static Object Detection (MOVED HERE)
                        if not is_excluded:
                            print("ALGORITHM 4: Early Static Object Detection...")
                            try:
                                is_static, max_overlap, static_reason = adaptive_detector.is_same_pixel_detection_advanced(xyxy)
                                
                                print(f"DEBUG: Static detection - is_static: {is_static}, max_overlap: {max_overlap:.3f}")
                                print(f"DEBUG: Consecutive static: {adaptive_detector.consecutive_static_detections}")
                                print(f"DEBUG: Static threshold: {adaptive_detector.static_fire_threshold}")
                                
                                if is_static and adaptive_detector.consecutive_static_detections > 8:
                                    is_excluded = True
                                    exclusion_reason = f"static_object_detected_{static_reason}_consecutive_{adaptive_detector.consecutive_static_detections}"
                                    print(f"  STATIC OBJECT REJECTED: {static_reason}")
                                    print(f"  Consecutive static detections: {adaptive_detector.consecutive_static_detections}")
                                    frame_algorithm_details.append(f"Static Detection: REJECTED - {static_reason}")
                                    
                                    # Reset counter when we reject a static object
                                    adaptive_detector.reset_static_detection_counter()
                                else:
                                    print(f"  Static check: {static_reason} (consecutive: {adaptive_detector.consecutive_static_detections})")
                                    frame_algorithm_details.append(f"Static Detection: PASSED - {static_reason}")
                                    
                            except Exception as e:
                                print(f"  Static detection error: {e}")
                                frame_algorithm_details.append(f"Static Detection: ERROR - {str(e)}")

                        # ALGORITHM 5: Brightness analysis (only if not excluded)
                        brightness_threshold = base_fire_threshold
                        if not is_excluded:
                            try:
                                brightness_threshold, brightness_reasons = brightness_detector.calculate_brightness_adjusted_threshold(
                                    base_fire_threshold, frame, xyxy
                                )
                                print(f"  Brightness threshold: {brightness_threshold:.1f}%")
                                frame_algorithm_details.append(f"Brightness Analysis: threshold={brightness_threshold:.1f}%")
                            except Exception as e:
                                brightness_threshold = base_fire_threshold
                                frame_algorithm_details.append(f"Brightness Analysis: ERROR - {str(e)}")

                        # ALGORITHM 6: Adaptive threshold calculation
                        adaptive_threshold = brightness_threshold
                        if not is_excluded:
                            print("ALGORITHM 6: Adaptive threshold calculation...")
                            try:
                                adaptive_threshold, overlap_reason, interference_report = enhanced_calculate_adaptive_threshold(
                                    xyxy, high_confidence_objects, brightness_threshold, detection_type, frame
                                )
                                print(f"  Adaptive threshold: {adaptive_threshold:.1f}%")
                                print(f"  Overlap reason: {overlap_reason}")
                                print(f"  Interference: {interference_report}")
                                frame_algorithm_details.append(f"Adaptive Threshold: {adaptive_threshold:.1f}%, overlap: {overlap_reason}")
                            except Exception as e:
                                print(f"  Adaptive threshold failed: {e}")
                                adaptive_threshold = brightness_threshold
                                frame_algorithm_details.append(f"Adaptive Threshold: FAILED - {str(e)}")

                        # ALGORITHM 7: Threshold comparison
                        if not is_excluded:
                            if conf < adaptive_threshold:
                                is_excluded = True
                                exclusion_reason = f"below_adaptive_threshold_{conf:.1f}%_vs_{adaptive_threshold:.1f}%"
                            else:
                                print(f"  Fire {conf:.1f}% above adaptive threshold {adaptive_threshold:.1f}%")

                        # ALGORITHM 8: Multi-frame validation (SIMPLIFIED - no comprehensive validation inside)
                        if not is_excluded:
                            try:
                                # Initialize counter if it doesn't exist
                                if not hasattr(adaptive_detector, 'single_method_frame_counter'):
                                    adaptive_detector.single_method_frame_counter = 0
                                
                                # Simple frame counting without resetting comprehensive validations
                                adaptive_detector.single_method_frame_counter += 1
                                
                                print(f"  Multi-frame counting: {adaptive_detector.single_method_frame_counter}/18")
                                
                                if adaptive_detector.single_method_frame_counter >= 18:
                                    # VALIDATION COMPLETE
                                    adaptive_detector.single_method_frame_counter = 0  # Reset for next sequence
                                    is_excluded = False  # This is a VALID detection
                                    print(f"  MULTI-FRAME VALIDATION COMPLETE! FIRE CONFIRMED!")
                                    frame_algorithm_details.append(f"Multi-Frame: COMPLETED - 18 frames reached")
                                else:
                                    is_excluded = True  # Still counting, not ready to alert yet
                                    exclusion_reason = f"counting_frames_{adaptive_detector.single_method_frame_counter}_of_18"
                                    frame_algorithm_details.append(f"Multi-Frame: COUNTING - {adaptive_detector.single_method_frame_counter}/18")
                                    
                            except Exception as e:
                                print(f"  Multi-frame validation error: {e}")
                                is_excluded = True
                                exclusion_reason = f"multi_frame_error"
                                adaptive_detector.single_method_frame_counter = 0  # Reset on error
                                frame_algorithm_details.append(f"Multi-Frame: ERROR - {str(e)}")

                        # Add frame algorithm details to main list
                        algorithm_details.extend(frame_algorithm_details)

                        # Build detection info
                        detection_info = f"Fire: {conf:.1f}%"
                        
                        # Handle results
                        if is_excluded:
                            detection_info += f" - EXCLUDED: {exclusion_reason}"
                            detection_details.append(detection_info)
                            
                            # Draw excluded detection
                            cv2.rectangle(annotated_frame, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), (128, 128, 128), 1)
                            label = f"EXCLUDED FIRE {conf:.0f}%"
                            cv2.putText(annotated_frame, label, (xyxy[0], xyxy[1] - 5),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
                            
                            suppressed_detections.append({
                                'type': 'fire',
                                'confidence': conf,
                                'reason': exclusion_reason
                            })
                            
                            print(f"  RESULT: FIRE EXCLUDED - {exclusion_reason}")
                        else:
                            # Valid fire detection - ALERT READY
                            fire_detected = True
                            max_fire_conf = max(max_fire_conf, conf)
                            valid_fire_detections.append({
                                'bbox': xyxy,
                                'confidence': conf,
                                'threshold': adaptive_threshold,
                                'validation_status': 'MULTI_FRAME_VALIDATED'
                            })
                            
                            # Store this detection in pixel history AFTER it's validated
                            adaptive_detector.fire_pixel_history.append(xyxy)

                            detection_info += f" - VALIDATED (18 frames completed)"
                            detection_details.append(detection_info)

                            # Draw valid detection
                            color = (0, 0, 255)  # Red for fire
                            label = f"FIRE ALERT {conf:.1f}%"
                            
                            cv2.rectangle(annotated_frame, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), color, 3)
                            cv2.putText(annotated_frame, label, (xyxy[0], xyxy[1] - 5),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                            
                            print(f"  RESULT: FIRE ALERT TRIGGERED!")
                    
                    except Exception as box_error:
                        print(f"Warning: Error processing box: {box_error}")
                        algorithm_details.append(f"Box Processing: ERROR - {str(box_error)}")
                        continue

        # Draw interfering objects
        for obj in high_confidence_objects:
            x1, y1, x2, y2 = map(int, obj['bbox'])
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            label = f"{obj['class_name']} {obj['confidence']:.0f}%"
            cv2.putText(annotated_frame, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # Add system info with frame counter
        if camera_name in ADAPTIVE_DETECTORS:
            detector = ADAPTIVE_DETECTORS[camera_name]
            single_counter = getattr(detector, 'single_method_frame_counter', 0)
            static_counter = getattr(detector, 'consecutive_static_detections', 0)
            
            info_text = f"Frame Count: {single_counter}/18 | Static: {static_counter}"
            cv2.putText(annotated_frame, info_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Print algorithm summary
        print(f"\n=== ALGORITHM SUMMARY ===")
        for detail in algorithm_details:
            print(f"  {detail}")
        print(f"=== FRAME ANALYSIS END ===\n")

        # Save annotated frame
        if save_annotated and (fire_detected or suppressed_detections):
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            status = "ALERT" if fire_detected else "SUPPRESSED"
            filename = os.path.join(ALERTS_DIR, f"{camera_name}_{status}_fire_{timestamp}.jpg")
            cv2.imwrite(filename, annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

    except Exception as main_error:
        print(f"Error in detection pipeline: {main_error}")
        algorithm_details.append(f"Pipeline Error: {str(main_error)}")
        return (False, 0, ["Pipeline error"], [], frame.copy(), algorithm_details)

    return (
        fire_detected, max_fire_conf, detection_details, 
        valid_fire_detections, annotated_frame, algorithm_details
    )

def process_camera_real_time(name, url, email_config=None, telegram_config=None, person_detection_only=False, stop_callback=None):
    """
    FIXED: Real-time camera processing with controllable person detection
    
    Parameters:
    - person_detection_only: If True, only detect persons (for scheduled monitoring)
    - stop_callback: Function that returns True when this process should stop
    """

    # CRITICAL FIX: Pass stop callback to person detection
    if person_detection_only:
        print(f"Starting CONTROLLABLE person detection monitoring for {name}")
        return process_person_detection_only(name, url, email_config, telegram_config, stop_callback)
    
    # Fire detection code with enhanced static object detection:
    print(f"Starting ENHANCED fire detection with early static detection for {name}")
    
    while True:
        cap = None
        try:
            cap = cv2.VideoCapture(url)
            if not cap.isOpened():
                print(f"{name}: Cannot connect. Retrying in 15s...")
                time.sleep(15)
                continue

            # Optimize capture settings
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FPS, 10)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
            
            print(f"{name}: Connected - ENHANCED Fire detection with static object filtering active")
            consecutive_failures = 0
            last_status_time = 0
            
            while True:
                loop_start = time.time()
                
                # Memory check
                if check_memory_usage():
                    time.sleep(1)
                    continue
                
                # Get frame
                try:
                    frame = grab_real_time_frame(cap, max_flush=15)
                    if frame is None:
                        consecutive_failures += 1
                        if consecutive_failures > 3:
                            break
                        continue
                    consecutive_failures = 0
                except Exception as e:
                    print(f"Frame grab error: {e}")
                    consecutive_failures += 1
                    if consecutive_failures > 3:
                        break
                    continue
                
                try:
                    frame_resized = cv2.resize(frame, (640, 640))
                    
                    # Check models loaded
                    if config.FIRE_MODEL is None or config.PERSON_MODEL is None:
                        print(f"{name}: Models not loaded, skipping...")
                        time.sleep(1)
                        continue
                    
                    # Run models
                    fire_results = config.FIRE_MODEL.predict(
                        frame_resized, verbose=False, conf=0.15, imgsz=640, device='cpu'
                    )
                    person_results = config.PERSON_MODEL.predict(
                        frame_resized, verbose=False, conf=0.15, imgsz=640, device='cpu'  
                    )
                    
                    # Enhanced fire detection with early static detection
                    try:
                        detection_result = enhanced_fire_detection_with_algorithm_details(
                            fire_results, person_results, name, frame_resized, save_annotated=True
                        )
                        
                        if detection_result is None or len(detection_result) != 6:
                            print(f"Detection function returned invalid data")
                            continue
                            
                        (fire_detected, max_fire_conf, detection_details, 
                         valid_fire_detections, annotated_frame, algorithm_details) = detection_result
                         
                    except Exception as e:
                        print(f"Detection error: {e}")
                        fire_detected = False
                        max_fire_conf = 0
                        detection_details = [f"Detection error: {e}"]
                        valid_fire_detections = []
                        annotated_frame = frame_resized.copy()
                        algorithm_details = [f"Detection Error: {str(e)}"]
                    
                    # Get detector
                    if name in ADAPTIVE_DETECTORS:
                        detector = ADAPTIVE_DETECTORS[name]
                    else:
                        ADAPTIVE_DETECTORS[name] = ImprovedAdaptiveFireSmokeDetector(name)
                        detector = ADAPTIVE_DETECTORS[name]
                    
                    # Initialize counters if needed
                    detector.initialize_counters_if_needed()
                    
                    # Validate results
                    fire_is_valid = fire_detected  # Already validated in pipeline
                    fire_validation_reason = "enhanced_static_pipeline_validated" if fire_detected else "no_fire"
                    
                    # Update history (fire only)
                    detector.update_detection_history(
                        max_fire_conf if fire_detected else 0,
                        0,  # No smoke detection
                        fire_is_valid, 
                        False  # No smoke validation
                    )
                    
                    # Log stats
                    objects_excluded = len([d for d in detection_details if "EXCLUDED" in d])
                    log_detection_stats(fire_detected, False, fire_is_valid, False, objects_excluded)

                    # Status logging with algorithm details
                    current_time = time.time()
                    if current_time - last_status_time > 30:
                        detector_info = detector.get_status_info()
                        
                        # Get debug static information
                        debug_static_info = detector.get_debug_static_info()
                        
                        single_counter = getattr(detector, 'single_method_frame_counter', 0)
                        static_counter = getattr(detector, 'consecutive_static_detections', 0)
                        
                        status = f"[{name}] Fire: {max_fire_conf:.1f}% | "
                        status += f"Frame Count: {single_counter}/18 | "
                        status += f"Static Count: {static_counter} | "
                        status += f"Env: {detector_info['environment']} | Excluded: {objects_excluded}"
                        
                        if fire_detected:
                            status += " FIRE ALERT TRIGGERED!" if fire_is_valid else f" Fire Invalid: {fire_validation_reason[:20]}"
                        
                        print(status)
                        
                        # Print debug static information
                        print(f"[{name}] Debug Static Info: {debug_static_info}")
                        
                        # Print recent algorithm details
                        if algorithm_details:
                            print(f"[{name}] Recent Algorithm Checks:")
                            for detail in algorithm_details[-5:]:  # Show last 5 checks
                                print(f"  {detail}")
                        
                        last_status_time = current_time

                    # Check internet
                    internet_connected = monitor_internet_connection()
                    
                    # Send fire alerts only
                    check_and_send_fire_alert(
                        name, fire_detected, max_fire_conf, frame_resized, detection_details,
                        fire_is_valid, fire_validation_reason, valid_fire_detections, annotated_frame,
                        internet_connected=internet_connected, email_config=email_config, telegram_config=telegram_config
                    )
                    
                    # Cleanup
                    del fire_results, person_results, frame_resized
                    
                except Exception as e:
                    print(f"{name}: Processing error: {e}")
                    logging.error(f"{name}: Processing error: {e}")
                
                # Dynamic sleep
                processing_time = time.time() - loop_start
                sleep_time = max(0, 0.5 - processing_time)  # Target 2 FPS
                time.sleep(sleep_time)

        except Exception as outer_error:
            print(f"{name}: Outer error: {outer_error}")
            logging.error(f"{name}: Outer error: {outer_error}")
            
        finally:
            if cap:
                cap.release()
            cv2.destroyAllWindows()
            time.sleep(1)