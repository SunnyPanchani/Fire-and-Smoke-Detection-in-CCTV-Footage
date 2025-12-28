# detection.py - Complete Detection System with Multi-Frame Support
import cv2
import numpy as np
import statistics
import time
from collections import deque
from datetime import datetime
from ultralytics import YOLO
import os

from config import (FIRE_MODEL_PATH, PERSON_MODEL_PATH, SCREEN_DEVICE_CLASSES, 
                    ELECTRONIC_DEVICE_CLASSES, ALL_INTERFERENCE_CLASSES,
                    ALERTS_DIR, ADAPTIVE_DETECTORS, BRIGHTNESS_DETECTORS)

def load_models_safely():
    """Load both YOLO models safely"""
    try:
        if not os.path.exists(FIRE_MODEL_PATH):
            print(f"Fire detection model not found: {FIRE_MODEL_PATH}")
            return None, None

        if not os.path.exists(PERSON_MODEL_PATH):
            print(f"Person/Object detection model not found: {PERSON_MODEL_PATH}")
            return None, None
        
        print(f"Loading fire/smoke detection model: {FIRE_MODEL_PATH}")
        fire_model = YOLO(FIRE_MODEL_PATH)
        
        print(f"Loading person/object detection model: {PERSON_MODEL_PATH}")
        person_model = YOLO(PERSON_MODEL_PATH)
        
        print(f"Fire model classes: {fire_model.names}")
        print(f"Person model classes: {person_model.names}")
        
        return fire_model, person_model
    except Exception as e:
        print(f"Error loading models: {e}")
        return None, None

def detect_high_confidence_objects(person_results, confidence_threshold=55.0):
    """
    Complete object detection with multi-frame tracking support
    """
    high_confidence_objects = []
    
    if not person_results or len(person_results) == 0:
        return high_confidence_objects
    
    result = person_results[0]
    current_timestamp = time.time()
    
    if hasattr(result, 'boxes') and result.boxes is not None and len(result.boxes) > 0:
        for box in result.boxes:
            conf = float(box.conf.cpu().numpy()[0]) * 100
            cls_id = int(box.cls.cpu().numpy()[0])
            
            if conf > confidence_threshold:
                from config import PERSON_MODEL
                xyxy = box.xyxy.cpu().numpy()[0]
                high_confidence_objects.append({
                    'bbox': xyxy,
                    'confidence': conf,
                    'class_id': cls_id,
                    'class_name': PERSON_MODEL.names.get(cls_id, f"class_{cls_id}") if PERSON_MODEL else f"class_{cls_id}",
                    'timestamp': current_timestamp,
                    'frame_id': int(current_timestamp * 1000) % 10000,
                    'detection_age': 0,
                    'tracking_id': f"{cls_id}_{int(xyxy[0])}_{int(xyxy[1])}"
                })
    
    return high_confidence_objects

def calculate_iou_improved(box1, box2):
    """
    Complete IoU calculation with detailed analysis for multi-frame validation
    """
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2
    
    # Calculate intersection
    inter_x_min = max(x1_min, x2_min)
    inter_y_min = max(y1_min, y2_min)
    inter_x_max = min(x1_max, x2_max)
    inter_y_max = min(y1_max, y2_max)
    
    if inter_x_max <= inter_x_min or inter_y_max <= inter_y_min:
        return 0.0, 0.0, 0.0, {
            'intersection_area': 0, 
            'coverage_type': 'no_overlap',
            'temporal_score': 0.0,
            'interference_risk': 'none'
        }
    
    inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
    
    # Calculate areas
    box1_area = (x1_max - x1_min) * (y1_max - y1_min)
    box2_area = (x2_max - x2_min) * (y2_max - y2_min)
    union_area = box1_area + box2_area - inter_area
    
    # Calculate IoU and overlaps
    iou = inter_area / union_area if union_area > 0 else 0.0
    overlap1 = inter_area / box1_area if box1_area > 0 else 0.0
    overlap2 = inter_area / box2_area if box2_area > 0 else 0.0
    
    # Enhanced coverage analysis
    coverage_details = {
        'intersection_area': inter_area,
        'fire_coverage': overlap1,
        'object_coverage': overlap2,
        'coverage_type': 'complete' if overlap1 > 0.8 else 'partial' if overlap1 > 0.3 else 'minimal',
        'temporal_score': min(1.0, iou * 1.2),
        'interference_risk': 'high' if overlap1 > 0.6 and overlap2 > 0.6 else 'medium' if overlap1 > 0.3 else 'low'
    }
    
    return iou, overlap1, overlap2, coverage_details

def analyze_object_interference(fire_bbox, objects, detection_type="fire"):
    """
    Complete multi-frame aware object interference analysis
    """
    interference_report = {
        'has_interference': False,
        'interference_level': 'none',
        'interfering_objects': [],
        'recommended_action': 'proceed',
        'confidence_adjustment': 0,
        'details': [],
        'highest_interfering_confidence': 0,
        'temporal_interference_score': 0.0,
        'persistent_objects': [],
        'frame_consistency': 0.0
    }
    
    for obj in objects:
        iou, fire_overlap, obj_overlap, coverage_details = calculate_iou_improved(fire_bbox, obj['bbox'])
        
        if iou > 0.1 or fire_overlap > 0.3:
            obj_info = {
                'class_name': obj['class_name'],
                'class_id': obj['class_id'],
                'confidence': obj['confidence'],
                'iou': iou,
                'fire_overlap': fire_overlap,
                'object_overlap': obj_overlap,
                'coverage_details': coverage_details,
                'timestamp': obj.get('timestamp', time.time()),
                'frame_id': obj.get('frame_id', 0),
                'tracking_id': obj.get('tracking_id', 'unknown'),
                'detection_age': obj.get('detection_age', 0)
            }
            
            # Track highest interfering confidence
            interference_report['highest_interfering_confidence'] = max(
                interference_report['highest_interfering_confidence'],
                obj['confidence']
            )
            
            # Calculate temporal interference
            temporal_weight = max(0.5, 1.0 - (obj.get('detection_age', 0) * 0.1))
            interference_report['temporal_interference_score'] += (iou * obj['confidence'] / 100) * temporal_weight
            
            # Determine interference score based on object type
            interference_score = 0
            
            if obj['class_id'] in SCREEN_DEVICE_CLASSES:
                interference_score = 95 if iou > 0.4 else 80 if iou > 0.2 else 60
                obj_info['category'] = 'screen_device'
                obj_info['risk'] = 'critical'
            elif obj['class_id'] == 0:  # person
                if detection_type == "fire":
                    interference_score = 85 if iou > 0.5 else 70 if iou > 0.3 else 50
                else:
                    interference_score = 45 if iou > 0.5 else 25 if iou > 0.3 else 15
                obj_info['category'] = 'person'
                obj_info['risk'] = 'high' if detection_type == "fire" else 'medium'
            elif obj['class_id'] in ELECTRONIC_DEVICE_CLASSES:
                interference_score = 60 if iou > 0.5 else 40 if iou > 0.3 else 25
                obj_info['category'] = 'electronic'
                obj_info['risk'] = 'medium'
            elif obj['class_id'] in [46, 47, 48, 49, 50, 51, 52, 53, 54, 55]:  # food
                if detection_type == "fire":
                    interference_score = 70 if iou > 0.4 else 50 if iou > 0.2 else 30
                else:
                    interference_score = 25
                obj_info['category'] = 'food'
                obj_info['risk'] = 'medium'
            else:
                base_score = 45 if iou > 0.6 else 30 if iou > 0.4 else 15
                confidence_multiplier = 1.2 if obj['confidence'] > 90 else 1.0
                interference_score = int(base_score * confidence_multiplier)
                obj_info['category'] = 'other'
                obj_info['risk'] = 'low'
            
            obj_info['interference_score'] = interference_score
            interference_report['interfering_objects'].append(obj_info)
            
            # Update overall interference level
            if interference_score >= 80:
                interference_report['interference_level'] = 'critical'
            elif interference_score >= 60 and interference_report['interference_level'] != 'critical':
                interference_report['interference_level'] = 'high'
            elif interference_score >= 40 and interference_report['interference_level'] not in ['critical', 'high']:
                interference_report['interference_level'] = 'medium'
            elif interference_score > 0 and interference_report['interference_level'] == 'none':
                interference_report['interference_level'] = 'low'
    
    # Calculate frame consistency and recommendations
    if interference_report['interfering_objects']:
        interference_report['has_interference'] = True
        
        # Normalize temporal interference score
        max_possible_temporal_score = len(interference_report['interfering_objects'])
        if max_possible_temporal_score > 0:
            interference_report['temporal_interference_score'] = min(1.0, 
                interference_report['temporal_interference_score'] / max_possible_temporal_score)
        
        # Determine recommended action with multi-frame awareness
        max_score = max(obj['interference_score'] for obj in interference_report['interfering_objects'])
        temporal_factor = interference_report['temporal_interference_score']
        
        if interference_report['interference_level'] == 'critical':
            interference_report['recommended_action'] = 'suppress_alert'
            interference_report['confidence_adjustment'] = 45 + int(temporal_factor * 15)
            interference_report['details'].append("Critical interference - likely false positive")
        elif interference_report['interference_level'] == 'high':
            interference_report['recommended_action'] = 'require_high_confidence'
            interference_report['confidence_adjustment'] = 30 + int(temporal_factor * 10)
            interference_report['details'].append("High interference - elevated confidence required")
        elif interference_report['interference_level'] == 'medium':
            interference_report['recommended_action'] = 'apply_moderate_filter'
            interference_report['confidence_adjustment'] = 20 + int(temporal_factor * 5)
            interference_report['details'].append("Medium interference - standard filtering")
        else:
            interference_report['recommended_action'] = 'apply_light_filter'
            interference_report['confidence_adjustment'] = 10 + int(temporal_factor * 5)
            interference_report['details'].append("Low interference - minimal filtering")
    
    return interference_report

def enhanced_calculate_adaptive_threshold(detection_bbox, high_confidence_objects, base_threshold, detection_type, frame=None):
    """
    Complete multi-frame aware adaptive threshold calculation
    """
    try:
        # Get comprehensive interference analysis
        interference_report = analyze_object_interference(detection_bbox, high_confidence_objects, detection_type)
        
        adaptive_threshold = base_threshold
        adjustment_reasons = []
        
        if interference_report['has_interference']:
            highest_interfering_conf = interference_report['highest_interfering_confidence']
            temporal_interference = interference_report['temporal_interference_score']
            
            # Enhanced adjustments for fire detection
            if detection_type == "fire":
                base_confidence_adjustment = interference_report['confidence_adjustment']
                confidence_adjustment = base_confidence_adjustment * 0.7  # More lenient for fires
                temporal_adjustment = temporal_interference * 10
                
                adaptive_threshold += confidence_adjustment + temporal_adjustment
                
                # Additional adjustments for persistent high-confidence interference
                if highest_interfering_conf > 85 and temporal_interference > 0.7:
                    adaptive_threshold += 12
                    adjustment_reasons.append(f"persistent_high_conf_{highest_interfering_conf:.0f}")
                elif highest_interfering_conf > 80:
                    adaptive_threshold += 8
                    adjustment_reasons.append(f"high_conf_{highest_interfering_conf:.0f}")
                
                # Log interfering objects
                for obj in interference_report['interfering_objects'][:3]:
                    reason = f"{obj['category']}_{obj['class_name']}_{obj['confidence']:.0f}"
                    adjustment_reasons.append(reason)
                
                # Multiple persistent objects penalty
                if len(interference_report['interfering_objects']) > 2 and temporal_interference > 0.5:
                    adaptive_threshold += 8
                    adjustment_reasons.append("multiple_persistent")
                elif len(interference_report['interfering_objects']) > 1:
                    adaptive_threshold += 3
                    adjustment_reasons.append("multiple_objects")
                    
            else:  # smoke - keep strict
                adaptive_threshold += interference_report['confidence_adjustment']
                if temporal_interference > 0.6:
                    adaptive_threshold += 5
                    adjustment_reasons.append("persistent_smoke_interference")
                
                adjustment_reasons.extend([obj['category'] for obj in interference_report['interfering_objects'][:2]])
        else:
            # No interference - more sensitive
            if detection_type == "fire":
                adaptive_threshold = max(base_threshold - 10, 22.0)
            else:
                adaptive_threshold = max(base_threshold - 5, 65.0)
            adjustment_reasons.append("no_interference_enhanced")
        
        # Apply bounds with temporal considerations
        temporal_interference = interference_report.get('temporal_interference_score', 0.0)
        if detection_type == "fire":
            min_threshold = 22.0 if temporal_interference < 0.3 else 25.0
            max_threshold = 80.0 if temporal_interference > 0.8 else 75.0
            adaptive_threshold = max(min_threshold, min(max_threshold, adaptive_threshold))
        else:
            adaptive_threshold = max(65.0, min(90.0, adaptive_threshold))
        
        # Build reason string
        reason_string = "_".join(adjustment_reasons[:4]) if adjustment_reasons else "no_adjustment"
        if temporal_interference > 0.5:
            reason_string += f"_temporal_{temporal_interference:.2f}"
        
        return adaptive_threshold, reason_string, interference_report
        
    except Exception as e:
        print(f"Error in enhanced adaptive threshold calculation: {e}")
        return base_threshold, "error_fallback", {
            'has_interference': False, 
            'interference_level': 'none',
            'temporal_interference_score': 0.0
        }

def check_enhanced_interference(fire_bbox, fire_conf, objects, min_obj_confidence=70.0):
    """
    Complete enhanced interference detection for comprehensive validation
    """
    interference_details = []
    
    for obj in objects:
        obj_conf = obj.get('confidence', 0)
        obj_class = obj.get('class_name', 'unknown_object')
        
        if obj_conf >= min_obj_confidence:
            # Calculate overlap using enhanced IoU
            iou, fire_overlap, obj_overlap, coverage_details = calculate_iou_improved(fire_bbox, obj['bbox'])
            
            # Determine interference criteria
            causes_interference = False
            interference_reason = ""
            
            # High overlap with higher confidence object
            if fire_overlap > 0.4 and obj_conf > fire_conf:
                causes_interference = True
                interference_reason = f"high_overlap_{fire_overlap:.2f}_higher_conf"
            # Significant overlap with very high confidence object
            elif fire_overlap > 0.3 and obj_conf >= 85:
                causes_interference = True
                interference_reason = f"significant_overlap_{fire_overlap:.2f}_very_high_conf"
            # Complete overlap regardless of confidence
            elif fire_overlap > 0.7:
                causes_interference = True
                interference_reason = f"complete_overlap_{fire_overlap:.2f}"
            
            if causes_interference:
                interference_details.append({
                    'object_class': obj_class,
                    'object_confidence': obj_conf,
                    'fire_confidence': fire_conf,
                    'overlap_ratio': fire_overlap,
                    'interference_reason': interference_reason,
                    'iou': iou,
                    'coverage_details': coverage_details
                })
    
    if interference_details:
        # Return most significant interference
        primary_interference = max(interference_details, key=lambda x: x['overlap_ratio'])
        return True, primary_interference
    
    return False, None

def validate_detection_comprehensive(fire_bbox, fire_confidence, frame, objects, detector):
    """
    Complete comprehensive detection validation for multi-frame system
    Performs all validation checks that should be done per frame
    """
    validation_failures = []
    
    try:
        # Check 1: Enhanced object interference
        interference_detected, interference_details = check_enhanced_interference(
            fire_bbox, fire_confidence, objects, min_obj_confidence=70.0
        )
        if interference_detected:
            validation_failures.append(f"object_interference_{interference_details['object_class']}")
        
        # Check 2: Static pixel detection
        try:
            is_static, overlap_ratio, pixel_analysis = detector.is_same_pixel_detection_advanced(fire_bbox)
            if is_static and overlap_ratio > 0.90 and fire_confidence < 50:
                validation_failures.append(f"static_detection_{pixel_analysis}")
        except Exception as e:
            validation_failures.append(f"static_check_error")
        
        # Check 3: Orange clothing detection
        try:
            is_clothing, clothing_reason = detector.detect_orange_clothing_advanced(frame, fire_bbox)
            if is_clothing:
                validation_failures.append(f"orange_clothing_{clothing_reason}")
        except Exception as e:
            validation_failures.append(f"clothing_check_error")
        
        # Check 4: Fire characteristics analysis
        try:
            is_real_fire, fire_analysis = detector.analyze_real_fire_characteristics_enhanced(
                frame, fire_bbox, fire_confidence
            )
            if not is_real_fire:
                validation_failures.append(f"poor_fire_characteristics_{fire_analysis}")
        except Exception as e:
            validation_failures.append(f"fire_characteristics_error")
        
        # Check 5: Adaptive threshold validation
        try:
            adaptive_threshold, threshold_reason, interference_report = enhanced_calculate_adaptive_threshold(
                fire_bbox, objects, 35.0, "fire", frame
            )
            if fire_confidence < adaptive_threshold:
                validation_failures.append(f"threshold_fail_{fire_confidence:.1f}<{adaptive_threshold:.1f}")
        except Exception as e:
            validation_failures.append(f"threshold_check_error")
        
        # Return validation result
        if validation_failures:
            return False, "_".join(validation_failures[:2])
        else:
            return True, "all_comprehensive_checks_passed"
            
    except Exception as e:
        return False, f"validation_system_error_{str(e)}"