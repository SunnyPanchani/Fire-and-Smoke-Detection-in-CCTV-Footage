



# adaptive_detection.py - Complete Comprehensive Multi-Frame Validation System
import cv2
import numpy as np
import statistics
import time
from collections import deque
from datetime import datetime
from detection import validate_detection_comprehensive
import uuid
import subprocess
import platform

def get_mac_address():
    """Get the primary MAC address of the system"""
    try:
        # Get MAC using uuid method
        mac = uuid.getnode()
        mac_address = ':'.join(['{:02x}'.format((mac >> elements) & 0xff) 
                               for elements in range(0,2*6,2)][::-1])
        return mac_address
    except Exception as e:
        print(f"❌ Error getting MAC address: {e}")
        return None

def get_active_mac_windows():
    """Get the active network adapter MAC address on Windows"""
    try:
        result = subprocess.run([
            'wmic', 'path', 'Win32_NetworkAdapter', 
            'where', 'NetConnectionStatus=2', 
            'get', 'MACAddress', '/format:csv'
        ], capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        for line in lines:
            if line.strip():
                parts = line.split(',')
                if len(parts) >= 2 and parts[1]:
                    return parts[1].replace('-', ':').lower()
    except:
        pass
    return None

def validate_mac_address():
    """Validate MAC address against expected values"""
    print("🔒 MAC Address Validation")
    print("=" * 30)
    
    # Expected MAC addresses (add your valid MACs here)
    valid_macs = [
        "75:d4:51:44:12:48",
        "28:f1:0e:1c:3f:86"  # Alternative MAC
    ]

    current_mac = get_mac_address()
    active_mac = get_active_mac_windows() if platform.system() == "Windows" else None
    
    print(f"Current MAC (UUID): {current_mac}")
    if active_mac:
        print(f"Active MAC (System): {active_mac}")
    
    # Check if any MAC matches
    macs_to_check = [mac for mac in [current_mac, active_mac] if mac is not None]
    
    for mac in macs_to_check:
        if mac.lower() in [valid.lower() for valid in valid_macs]:
            print(f"✅ MAC Address validated: {mac}")
            print("🚀 Starting Fire & Smoke Detection System...\n")
            return True
    
    print("❌ MAC Address validation failed!")
    print("🔒 This system is not authorized to run this application.")
    print(f"📋 Valid MAC addresses:")
    for valid_mac in valid_macs:
        print(f"   • {valid_mac}")
    print(f"📋 Found MAC addresses:")
    for mac in macs_to_check:
        print(f"   • {mac}")
    
    return False

def check_enhanced_interference(fire_bbox, fire_conf, objects, min_obj_confidence=55.0):
    """Enhanced interference detection for multi-frame validation"""
    for obj in objects:
        obj_conf = obj.get('confidence', 0)
        obj_class = obj.get('class_name', 'unknown_object')
        
        if obj_conf >= min_obj_confidence:
            # Simple overlap calculation
            fire_x1, fire_y1, fire_x2, fire_y2 = fire_bbox
            obj_x1, obj_y1, obj_x2, obj_y2 = obj['bbox']
            
            inter_x1 = max(fire_x1, obj_x1)
            inter_y1 = max(fire_y1, obj_y1)
            inter_x2 = min(fire_x2, obj_x2)
            inter_y2 = min(fire_y2, obj_y2)
            
            if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                fire_area = (fire_x2 - fire_x1) * (fire_y2 - fire_y1)
                overlap = inter_area / fire_area if fire_area > 0 else 0
                
                if (overlap > 0.3 and obj_conf > fire_conf) or (overlap > 0.5 and obj_conf >= min_obj_confidence):
                    return True, {
                        'type': obj_class,
                        'confidence': obj_conf,
                        'overlap': overlap,
                        'reason': f"Object {obj_class} ({obj_conf:.1f}%) overlaps fire ({fire_conf:.1f}%) by {overlap:.2f}"
                    }
    return False, None

class BrightnessAwareDetector:
    def __init__(self, camera_name):
        self.camera_name = camera_name
        
        # Brightness monitoring
        self.brightness_history = deque(maxlen=300)
        self.brightness_baseline = deque(maxlen=100)
        self.brightness_variance_history = deque(maxlen=50)
        self.last_brightness_analysis = 0
        
        # Light change detection
        self.sudden_light_changes = deque(maxlen=20)
        self.natural_light_periods = deque(maxlen=30)
        
        # Fire-specific brightness analysis
        self.fire_region_brightness_history = deque(maxlen=20)
        self.ambient_brightness_history = deque(maxlen=50)
        
        # Environmental classification
        self.environment_type = "unknown"
        self.lighting_pattern = "unknown"
        self.is_outdoor_camera = False
        self.natural_light_score = 0.0
        
        # Multi-frame brightness validation
        self.frame_brightness_history = deque(maxlen=15)
        self.lighting_change_frames = deque(maxlen=15)
        
        self.frames_processed = 0
        self.initialization_complete = False

    def analyze_brightness_distribution(self, frame):
        """Analyze brightness distribution for multi-frame validation"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        mean_brightness = np.mean(gray)
        brightness_std = np.std(gray)
        
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist_normalized = hist.flatten() / hist.sum()
        
        bright_threshold = 200
        very_bright_pixels = np.sum(gray > bright_threshold)
        bright_pixel_ratio = very_bright_pixels / (gray.shape[0] * gray.shape[1])
        
        overexposed_pixels = np.sum(gray > 245)
        overexposed_ratio = overexposed_pixels / (gray.shape[0] * gray.shape[1])
        
        brightness_data = {
            'mean_brightness': mean_brightness,
            'brightness_std': brightness_std,
            'bright_pixel_ratio': bright_pixel_ratio,
            'overexposed_ratio': overexposed_ratio,
            'hist_peak': np.argmax(hist_normalized),
            'hist_variance': np.var(hist_normalized),
            'timestamp': time.time(),
            'frame_id': len(self.frame_brightness_history)
        }
        
        self.frame_brightness_history.append(brightness_data)
        return brightness_data
    
    def validate_brightness_consistency_across_frames(self, current_fire_bbox):
        """Multi-frame brightness consistency validation"""
        if len(self.frame_brightness_history) < 5:
            return True, "insufficient_brightness_history"
        
        try:
            recent_frames = list(self.frame_brightness_history)[-8:]
            brightness_values = [frame['mean_brightness'] for frame in recent_frames]
            brightness_changes = []
            
            for i in range(1, len(brightness_values)):
                change = abs(brightness_values[i] - brightness_values[i-1])
                brightness_changes.append(change)
            
            max_change = max(brightness_changes) if brightness_changes else 0
            avg_change = np.mean(brightness_changes) if brightness_changes else 0
            
            # Detect sudden lighting changes
            if max_change > 35 or avg_change > 18:
                return False, f"unstable_lighting_max_{max_change:.1f}_avg_{avg_change:.1f}"
            
            # Check persistent overexposure
            overexposed_frames = sum(1 for frame in recent_frames if frame['overexposed_ratio'] > 0.12)
            if overexposed_frames >= 4:
                return False, f"persistent_overexposure_{overexposed_frames}/8_frames"
            
            # Check brightness trend
            brightness_trend = np.polyfit(range(len(brightness_values)), brightness_values, 1)[0]
            if abs(brightness_trend) > 3:
                return False, f"rapid_brightness_trend_{brightness_trend:.1f}"
            
            return True, "brightness_stable_across_frames"
            
        except Exception as e:
            print(f"Error in brightness consistency validation: {e}")
            return True, "brightness_validation_error_default_pass"

    def detect_natural_light_conditions(self, frame):
        """Enhanced natural light detection"""
        brightness_analysis = self.analyze_brightness_distribution(frame)
        
        self.brightness_history.append(brightness_analysis['mean_brightness'])
        self.brightness_variance_history.append(brightness_analysis['brightness_std'])
        
        if len(self.brightness_history) < 10:
            return False, 0.0, "insufficient_data"
        
        recent_brightness = list(self.brightness_history)[-10:]
        brightness_trend = self.calculate_brightness_trend(recent_brightness)
        
        natural_light_score = 0.0
        reasons = []
        
        if brightness_analysis['mean_brightness'] > 120:
            natural_light_score += 0.3
            reasons.append("high_ambient_brightness")
        
        if brightness_analysis['bright_pixel_ratio'] > 0.15:
            natural_light_score += 0.4
            reasons.append("bright_pixel_patches")
        
        if brightness_analysis['overexposed_ratio'] > 0.05:
            natural_light_score += 0.5
            reasons.append("overexposed_regions")
        
        if abs(brightness_trend) > 2 and len(self.brightness_history) > 30:
            trend_consistency = self.check_brightness_trend_consistency()
            if trend_consistency > 0.7:
                natural_light_score += 0.3
                reasons.append("gradual_brightness_change")
        
        current_hour = datetime.now().hour
        if 6 <= current_hour <= 18:
            natural_light_score += 0.2
            reasons.append("daytime_period")
        
        self.natural_light_score = natural_light_score
        is_natural_light = natural_light_score > 0.6
        
        return is_natural_light, natural_light_score, "_".join(reasons)
    
    def calculate_brightness_trend(self, brightness_values):
        """Calculate brightness trend"""
        if len(brightness_values) < 5:
            return 0
        
        x = list(range(len(brightness_values)))
        y = brightness_values
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        return slope
    
    def check_brightness_trend_consistency(self):
        """Check brightness trend consistency"""
        if len(self.brightness_history) < 20:
            return 0
        
        recent_values = list(self.brightness_history)[-20:]
        
        smooth_changes = 0
        total_changes = 0
        
        for i in range(1, len(recent_values)):
            change = abs(recent_values[i] - recent_values[i-1])
            total_changes += 1
            
            if change < 5:
                smooth_changes += 1
        
        return smooth_changes / total_changes if total_changes > 0 else 0
    
    def analyze_fire_region_brightness(self, frame, fire_bbox):
        """Analyze fire region brightness"""
        x1, y1, x2, y2 = map(int, fire_bbox)
        
        fire_region = frame[y1:y2, x1:x2]
        if fire_region.size == 0:
            return None
        
        gray_region = cv2.cvtColor(fire_region, cv2.COLOR_BGR2GRAY)
        hsv_region = cv2.cvtColor(fire_region, cv2.COLOR_BGR2HSV)
        
        region_brightness = np.mean(gray_region)
        region_max_brightness = np.max(gray_region)
        
        hue_values = hsv_region[:, :, 0]
        saturation_values = hsv_region[:, :, 1]
        value_values = hsv_region[:, :, 2]
        
        fire_hue_mask = ((hue_values >= 0) & (hue_values <= 30)) | ((hue_values >= 150) & (hue_values <= 180))
        fire_hue_ratio = np.sum(fire_hue_mask) / fire_hue_mask.size
        
        high_saturation_mask = saturation_values > 100
        saturation_ratio = np.sum(high_saturation_mask) / high_saturation_mask.size
        
        return {
            'region_brightness': region_brightness,
            'region_max_brightness': region_max_brightness,
            'fire_hue_ratio': fire_hue_ratio,
            'saturation_ratio': saturation_ratio,
            'brightness_uniformity': np.std(gray_region)
        }
    
    def calculate_brightness_adjusted_threshold(self, base_threshold, frame, fire_bbox=None):
        """Enhanced brightness-adjusted threshold calculation"""
        is_natural_light, light_score, light_reason = self.detect_natural_light_conditions(frame)
        
        brightness_analysis = self.analyze_brightness_distribution(frame)
        current_brightness = brightness_analysis['mean_brightness']
        
        # Multi-frame brightness consistency check
        brightness_consistent = True
        consistency_reason = "no_fire_bbox"
        
        if fire_bbox is not None:
            brightness_consistent, consistency_reason = self.validate_brightness_consistency_across_frames(fire_bbox)
        
        adjusted_threshold = base_threshold
        adjustment_reasons = []
        
        # Reject if brightness inconsistent
        if not brightness_consistent:
            adjusted_threshold += 35
            adjustment_reasons.append(f"brightness_inconsistent_{consistency_reason}")
        
        # Natural light adjustments
        if is_natural_light:
            if light_score > 0.8:
                adjusted_threshold += 40
                adjustment_reasons.append(f"strong_natural_light_{light_score:.1f}")
            elif light_score > 0.6:
                adjusted_threshold += 30
                adjustment_reasons.append(f"natural_light_{light_score:.1f}")
        
        # Brightness-based adjustments
        if current_brightness > 150:
            adjusted_threshold += 25
            adjustment_reasons.append(f"very_bright_{current_brightness:.0f}")
        elif current_brightness > 120:
            adjusted_threshold += 18
            adjustment_reasons.append(f"bright_{current_brightness:.0f}")
        elif current_brightness < 60:
            adjusted_threshold -= 12
            adjustment_reasons.append(f"dark_{current_brightness:.0f}")
        
        # Overexposed region penalty
        if brightness_analysis['overexposed_ratio'] > 0.1:
            adjusted_threshold += 35
            adjustment_reasons.append(f"overexposed_{brightness_analysis['overexposed_ratio']:.2f}")
        
        # Fire region analysis
        if fire_bbox is not None:
            region_analysis = self.analyze_fire_region_brightness(frame, fire_bbox)
            if region_analysis:
                if region_analysis['region_brightness'] > 200:
                    adjusted_threshold += 30
                    adjustment_reasons.append("bright_fire_region")
                
                if region_analysis['saturation_ratio'] < 0.3:
                    adjusted_threshold += 25
                    adjustment_reasons.append("low_saturation")
                
                if region_analysis['fire_hue_ratio'] < 0.2:
                    adjusted_threshold += 20
                    adjustment_reasons.append("poor_fire_colors")
        
        # Apply limits
        max_threshold = 98
        min_threshold = 40
        adjusted_threshold = max(min_threshold, min(max_threshold, adjusted_threshold))
        
        self.frames_processed += 1
        
        return adjusted_threshold, adjustment_reasons


class ImprovedAdaptiveFireSmokeDetector:
    def __init__(self, camera_name):
        self.camera_name = camera_name
        self.baseline_brightness = deque(maxlen=50)
        self.brightness_history = deque(maxlen=200)
        self.fire_detection_history = deque(maxlen=20)
        self.smoke_detection_history = deque(maxlen=20)
        self.environment_type = "unknown"
        
        # Optimized fire thresholds
        self.adaptive_fire_threshold = 30.0
        self.min_fire_threshold = 22.0
        self.max_fire_threshold = 78.0
        
        # Strict smoke thresholds
        self.adaptive_smoke_threshold = 96.0
        self.min_smoke_threshold = 93.0
        self.max_smoke_threshold = 99.0
        
        self.false_positive_count = 0
        self.confirmed_fire_count = 0
        self.confirmed_smoke_count = 0
        self.initialization_frames = 100
        self.frames_processed = 0
        self.last_major_brightness_change = 0
        
        # Enhanced stability buffers
        self.fire_stability_buffer = deque(maxlen=8)
        self.smoke_stability_buffer = deque(maxlen=25)
        
        self.fog_detection_buffer = deque(maxlen=30)
        self.fire_valid_state = False
        self.smoke_valid_state = False
        
        # Enhanced fire detection tracking
        self.consecutive_fire_detections = 0
        self.last_fire_confidence = 0
        self.fire_trend_increasing = False
        
        # Enhanced pixel tracking
        self.fire_pixel_history = deque(maxlen=15)
        self.static_fire_threshold = 0.65
        self.fire_shape_variance_history = deque(maxlen=20)
        self.consecutive_static_detections = 0
        self.max_static_detections = 8
        
        # Frame dimensions
        self.frame_width = 640
        self.frame_height = 640
        self.total_pixels = self.frame_width * self.frame_height
        
        # Orange clothing detection
        self.orange_clothing_pixel_history = deque(maxlen=10)
        self.clothing_detection_threshold = 0.75
        
        # CORE: Multi-frame validation system
        self.frame_buffer = deque(maxlen=50)
        self.object_history = deque(maxlen=50)
        self.validation_lookback = 15
        


    def store_frame_data(self, frame, fire_detections=None, objects=None):
        """Store frame data for multi-frame validation"""
        frame_data = {
            'timestamp': time.time(),
            'frame_id': len(self.frame_buffer),
            'fire_detections': fire_detections or [],
            'objects': objects or [],
            'brightness': np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)) if frame is not None else 0,
            'object_count': len(objects or []),
            'high_conf_object_count': len([obj for obj in (objects or []) if obj.get('confidence', 0) > 80])
        }
        
        self.frame_buffer.append(frame_data)
        self.object_history.append(objects or [])
    
    def get_frame_history(self, lookback_frames=10):
        """Get frame history for validation"""
        if len(self.frame_buffer) < lookback_frames:
            return list(self.frame_buffer)
        return list(self.frame_buffer)[-lookback_frames:]


    def validate_fire_over_multiple_frames_single(self, frame, current_bbox, high_conf_objects, fire_confidence, lookback=None):
        """
        SIMPLIFIED: Single method multi-frame validation
        - Below 20%: Reject immediately
        - Above 25%: Validate over 10 frames
        - Any invalid frame: Restart counter
        """
        try:
            # Step 1: Minimum confidence check
            if fire_confidence < 20.0:
                print(f"SINGLE METHOD: Fire {fire_confidence:.1f}% < 20% minimum - REJECTED")
                self.reset_single_counter()
                return False, f"below_minimum_{fire_confidence:.1f}%"
            
            # Step 2: Must be above 25% to proceed
            if fire_confidence < 25.0:
                print(f"SINGLE METHOD: Fire {fire_confidence:.1f}% < 25% threshold - REJECTED")
                self.reset_single_counter()
                return False, f"below_threshold_{fire_confidence:.1f}%"
            
            # Store frame data
            self.store_frame_data(frame, [{'bbox': current_bbox, 'confidence': fire_confidence}], high_conf_objects)
            
            # Step 3: Comprehensive validation for this frame
            def perform_comprehensive_validation(fire_bbox, fire_conf, frame, objects):
                try:
                    from detection import validate_detection_comprehensive
                    is_valid, validation_reason = validate_detection_comprehensive(
                        fire_bbox, fire_conf, frame, objects, self
                    )
                    return is_valid, validation_reason
                except Exception as e:
                    print(f"Comprehensive validation error: {e}")
                    return False, f"validation_error_{str(e)}"
            
            frame_valid, failure_reason = perform_comprehensive_validation(
                current_bbox, fire_confidence, frame, high_conf_objects
            )
            
            if not frame_valid:
                self.reset_single_counter()
                print(f"COMPREHENSIVE VALIDATION FAILED: {failure_reason}")
                print(f"SINGLE COUNTER RESET - Restarting validation process")
                return False, f"comprehensive_validation_failed_{failure_reason}"
            
            # Step 4: Single method frame counting
            self.single_method_frame_counter += 1
            self.single_method_target_frames = 18  # Fixed 14 frames
            
            print(f"SINGLE METHOD FRAME {self.single_method_frame_counter}/{self.single_method_target_frames} (Fire: {fire_confidence:.1f}%)")
            
            if self.single_method_frame_counter >= self.single_method_target_frames:
                # VALIDATION COMPLETE - TRIGGER ALERT
                self.reset_single_counter()
                print(f"🔥 SINGLE METHOD VALIDATION COMPLETE! FIRE ALERT TRIGGERED!")
                return True, f"single_method_validated_{self.single_method_target_frames}_frames_FIRE_CONFIRMED"
            else:
                return False, f"single_method_counting_{self.single_method_frame_counter}_of_{self.single_method_target_frames}"
                    
        except Exception as e:
            print(f"Error in single method multi-frame validation: {e}")
            self.reset_single_counter()
            return False, f"single_method_validation_error_reject_{str(e)}"

    def reset_single_counter(self):
        """Reset single method counter"""
        self.single_method_frame_counter = 0
        print("SINGLE METHOD COUNTER RESET TO 0")





    def calculate_brightness(self, frame):
        """Calculate average brightness"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        self.brightness_history.append(brightness)
        return brightness
    
    def update_detection_history(self, fire_conf, smoke_conf, fire_valid, smoke_valid):
        """Update detection history"""
        current_time = time.time()
        
        if fire_conf > 0:
            self.fire_detection_history.append({
                'confidence': fire_conf,
                'valid': fire_valid,
                'timestamp': current_time
            })
        
        if smoke_conf > 0:
            self.smoke_detection_history.append({
                'confidence': smoke_conf,
                'valid': smoke_valid,
                'timestamp': current_time
            })
        
        if fire_valid:
            self.confirmed_fire_count += 1
        elif fire_conf > 0 and not fire_valid:
            self.false_positive_count += 1
            
        if smoke_valid:
            self.confirmed_smoke_count += 1
        elif smoke_conf > 0 and not smoke_valid:
            self.false_positive_count += 1
    
    def analyze_environment(self, frame):
        """Analyze environment type"""
        if len(self.brightness_history) < 10:
            return "initializing"
        
        current_brightness = self.calculate_brightness(frame)
        recent_brightness = list(self.brightness_history)[-10:]
        brightness_std = statistics.stdev(recent_brightness) if len(recent_brightness) > 1 else 0
        
        if self.detect_fog_conditions(frame):
            self.environment_type = "foggy"
        elif current_brightness > 150 and brightness_std < 20:
            self.environment_type = "bright_outdoor"
        elif current_brightness < 80 and brightness_std < 15:
            self.environment_type = "dark_indoor"
        elif brightness_std > 25:
            self.environment_type = "variable_lighting"
        else:
            self.environment_type = "stable_indoor"
        
        return self.environment_type
    
    def detect_fog_conditions(self, frame):
        """Detect foggy conditions"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        
        contrast = np.std(gray)
        brightness = np.mean(gray)
        
        is_low_contrast = contrast < 30
        is_low_edge_density = edge_density < 0.05
        is_uniform_brightness = 80 < brightness < 180
        
        fog_score = sum([is_low_contrast, is_low_edge_density, is_uniform_brightness])
        is_foggy = fog_score >= 2
        
        self.fog_detection_buffer.append(is_foggy)
        
        if len(self.fog_detection_buffer) >= 5:
            recent_fog_detections = list(self.fog_detection_buffer)[-5:]
            return sum(recent_fog_detections) >= 3
        
        return False
    
    def is_in_lighting_change_period(self):
        """Check if in lighting change period"""
        current_time = time.time()
        return current_time - self.last_major_brightness_change < 30
    
    def detect_sudden_lighting_change(self, current_brightness):
        """Detect sudden lighting changes"""
        if len(self.brightness_history) < 5:
            return False
        
        recent_brightness = list(self.brightness_history)[-5:]
        avg_recent = statistics.mean(recent_brightness)
        
        brightness_change = abs(current_brightness - avg_recent)
        
        if brightness_change > 50:
            self.last_major_brightness_change = time.time()
            return True
        
        return False
    
    def get_status_info(self):
        """Get detector status info"""
        avg_brightness = statistics.mean(self.brightness_history) if self.brightness_history else 0
        
        return {
            'environment': self.environment_type,
            'adaptive_fire_threshold': self.adaptive_fire_threshold,
            'adaptive_smoke_threshold': self.adaptive_smoke_threshold,
            'confirmed_fires': self.confirmed_fire_count,
            'confirmed_smokes': self.confirmed_smoke_count,
            'false_positives': self.false_positive_count,
            'frames_processed': self.frames_processed,
            'avg_brightness': avg_brightness,
            'fire_valid_state': self.fire_valid_state,
            'smoke_valid_state': self.smoke_valid_state,

        }

    def calculate_adaptive_thresholds(self, environment_type, fire_confidence_values, smoke_confidence_values):
        """Calculate adaptive thresholds"""
        fire_base_threshold = {
            "foggy": 37.0,
            "bright_outdoor": 40.0,
            "dark_indoor": 30.0,
            "variable_lighting": 37.0,
            "stable_indoor": 33.0,
            "initializing": 33.0
        }.get(environment_type, 33.0)

        smoke_base_threshold = {
            "foggy": 85.0,
            "bright_outdoor": 78.0,
            "dark_indoor": 80.0,
            "variable_lighting": 82.0,
            "stable_indoor": 75.0,
            "initializing": 78.0
        }.get(environment_type, 78.0)

        if self.false_positive_count > 20:
            fire_base_threshold += 5
            smoke_base_threshold += 8
        elif self.confirmed_fire_count > 0:
            fire_base_threshold -= 5

        self.adaptive_fire_threshold = max(self.min_fire_threshold,
                                        min(self.max_fire_threshold, fire_base_threshold))
        self.adaptive_smoke_threshold = max(self.min_smoke_threshold,
                                        min(self.max_smoke_threshold, smoke_base_threshold))
        
        return self.adaptive_fire_threshold, self.adaptive_smoke_threshold

    def calculate_bbox_center_and_area(self, bbox):
        """Calculate bbox center and area"""
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        area = (x2 - x1) * (y2 - y1)
        return (center_x, center_y), area
    
    def create_bbox_mask(self, bbox, frame_shape=(640, 640)):
        """Create binary mask for bbox"""
        mask = np.zeros(frame_shape, dtype=np.uint8)
        x1, y1, x2, y2 = map(int, bbox)
        
        x1 = max(0, min(x1, frame_shape[1]))
        y1 = max(0, min(y1, frame_shape[0]))
        x2 = max(0, min(x2, frame_shape[1]))
        y2 = max(0, min(y2, frame_shape[0]))
        
        mask[y1:y2, x1:x2] = 1
        return mask
    
    def calculate_pixel_overlap_fast(self, bbox1, bbox2):
        """Fast pixel overlap calculation"""
        try:
            x1_1, y1_1, x2_1, y2_1 = bbox1
            x1_2, y1_2, x2_2, y2_2 = bbox2
            
            x1_inter = max(x1_1, x1_2)
            y1_inter = max(y1_1, y1_2)
            x2_inter = min(x2_1, x2_2)
            y2_inter = min(y2_1, y2_2)
            
            if x1_inter >= x2_inter or y1_inter >= y2_inter:
                return 0.0
                
            intersection_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
            bbox1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
            bbox2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
            union_area = bbox1_area + bbox2_area - intersection_area
            
            if union_area <= 0:
                return 0.0
                
            overlap_ratio = intersection_area / union_area
            return min(overlap_ratio, 1.0)
            
        except Exception as e:
            print(f"Error calculating overlap: {e}")
            return 0.0
    
    def analyze_fire_shape_variance(self, current_bbox):
        """Analyze fire shape variance"""
        if len(self.fire_pixel_history) < 3:
            return 0.5, "insufficient_history"
        
        centers = []
        areas = []
        aspect_ratios = []
        
        for bbox in self.fire_pixel_history:
            center, area = self.calculate_bbox_center_and_area(bbox)
            centers.append(center)
            areas.append(area)
            
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            aspect_ratio = width / max(height, 1)
            aspect_ratios.append(aspect_ratio)
        
        current_center, current_area = self.calculate_bbox_center_and_area(current_bbox)
        centers.append(current_center)
        areas.append(current_area)
        
        width = current_bbox[2] - current_bbox[0]
        height = current_bbox[3] - current_bbox[1]
        current_aspect_ratio = width / max(height, 1)
        aspect_ratios.append(current_aspect_ratio)
        
        center_x_variance = np.var([c[0] for c in centers])
        center_y_variance = np.var([c[1] for c in centers])
        area_variance = np.var(areas) / max(np.mean(areas), 1)
        aspect_ratio_variance = np.var(aspect_ratios)
        
        movement_score = (center_x_variance + center_y_variance) / 1000
        shape_change_score = area_variance + aspect_ratio_variance
        
        total_variance_score = movement_score + shape_change_score
        self.fire_shape_variance_history.append(total_variance_score)
        
        is_dynamic = total_variance_score > 0.3
        
        reason = f"var_{total_variance_score:.3f}_move_{movement_score:.3f}_shape_{shape_change_score:.3f}"
        
        return total_variance_score, reason
    
    def analyze_geometric_shape_irregularity(self, detection_bbox, frame):
        """Analyze geometric shape irregularity"""
        try:
            x1, y1, x2, y2 = map(int, detection_bbox)
            fire_region = frame[y1:y2, x1:x2]
            
            if fire_region.size == 0:
                return 0.0, "empty_region"
            
            gray_region = cv2.cvtColor(fire_region, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray_region, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if len(contours) == 0:
                return 0.5, "no_contours"
            
            main_contour = max(contours, key=cv2.contourArea)
            
            if len(main_contour) < 10:
                return 0.5, "insufficient_contour_points"
            
            hull = cv2.convexHull(main_contour)
            contour_area = cv2.contourArea(main_contour)
            hull_area = cv2.contourArea(hull)
            
            convexity_ratio = contour_area / hull_area if hull_area > 0 else 0
            
            perimeter = cv2.arcLength(main_contour, True)
            perimeter_area_ratio = (perimeter * perimeter) / (4 * np.pi * contour_area) if contour_area > 0 else 0
            
            epsilon = 0.02 * cv2.arcLength(main_contour, True)
            approx = cv2.approxPolyDP(main_contour, epsilon, True)
            approximation_ratio = len(approx) / len(main_contour)
            
            irregularity_factors = {
                'convexity': max(0, (0.8 - convexity_ratio) / 0.5),
                'perimeter_complexity': min(1.0, (perimeter_area_ratio - 1.27) / 3.0),
                'approximation_complexity': min(1.0, approximation_ratio * 5)
            }
            
            weights = {
                'convexity': 0.4,
                'perimeter_complexity': 0.4,
                'approximation_complexity': 0.2
            }
            
            total_irregularity_score = sum(
                irregularity_factors[factor] * weights[factor]
                for factor in irregularity_factors
            )
            
            analysis_details = f"irreg_{total_irregularity_score:.3f}_convex_{convexity_ratio:.3f}"
            
            return total_irregularity_score, analysis_details
            
        except Exception as e:
            print(f"Error in geometric analysis: {e}")
            return 0.5, f"analysis_error"
    
    def detect_regular_geometric_patterns(self, detection_bbox, frame):
        """Detect regular geometric patterns"""
        try:
            x1, y1, x2, y2 = map(int, detection_bbox)
            fire_region = frame[y1:y2, x1:x2]
            
            if fire_region.size == 0:
                return False, 0.0, "empty_region"
            
            gray_region = cv2.cvtColor(fire_region, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray_region, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if len(contours) == 0:
                return False, 0.0, "no_contours"
            
            main_contour = max(contours, key=cv2.contourArea)
            
            # Rectangle detection
            rect = cv2.minAreaRect(main_contour)
            box = cv2.boxPoints(rect)
            box = np.array(box, dtype=np.int32)
            
            rect_area = cv2.contourArea(box)
            contour_area = cv2.contourArea(main_contour)
            rect_match_ratio = contour_area / rect_area if rect_area > 0 else 0
            
            is_rectangular = rect_match_ratio > 0.85
            
            # Circle detection
            (center, radius) = cv2.minEnclosingCircle(main_contour)
            circle_area = np.pi * radius * radius
            circle_match_ratio = contour_area / circle_area if circle_area > 0 else 0
            
            is_circular = 0.75 < circle_match_ratio < 0.95
            
            regular_shape_detected = is_rectangular or is_circular
            regularity_score = max(rect_match_ratio, circle_match_ratio)
            
            reason = f"rect_{rect_match_ratio:.2f}_circle_{circle_match_ratio:.2f}"
            
            return regular_shape_detected, regularity_score, reason
            
        except Exception as e:
            print(f"Error in pattern detection: {e}")
            return False, 0.0, "detection_error"

    def analyze_real_fire_characteristics_enhanced(self, frame, detection_bbox, confidence):
        """Analyze real fire characteristics"""
        try:
            x1, y1, x2, y2 = map(int, detection_bbox)
            fire_region = frame[y1:y2, x1:x2]
            
            if fire_region.size == 0:
                return False, "empty_region"
            
            irregularity_score, shape_analysis = self.analyze_geometric_shape_irregularity(detection_bbox, frame)
            regular_shape_detected, regularity_score, regular_pattern = self.detect_regular_geometric_patterns(detection_bbox, frame)
            
            # Color analysis
            hsv_region = cv2.cvtColor(fire_region, cv2.COLOR_BGR2HSV)
            
            fire_ranges = [
                (np.array([0, 120, 120]), np.array([20, 255, 255])),
                (np.array([20, 100, 100]), np.array([35, 255, 255])),
                (np.array([160, 120, 120]), np.array([180, 255, 255]))
            ]
            
            total_fire_pixels = 0
            for lower, upper in fire_ranges:
                mask = cv2.inRange(hsv_region, lower, upper)
                total_fire_pixels += cv2.countNonZero(mask)
            
            total_pixels = fire_region.shape[0] * fire_region.shape[1]
            fire_color_ratio = total_fire_pixels / total_pixels
            
            # Balanced decision logic
            if regular_shape_detected and regularity_score > 0.9 and fire_color_ratio < 0.1:
                return False, f"very_regular_no_colors_{regular_pattern}"
            elif fire_color_ratio > 0.08:
                return True, f"fire_colors_{fire_color_ratio:.2f}"
            elif confidence > 55:
                return True, f"confidence_override_{confidence:.1f}"
            else:
                return True, "default_accept_balanced"
                
        except Exception as e:
            return True, f"analysis_error_accept"

    def get_pixel_tracking_stats(self):
        """Get pixel tracking statistics"""
        return {
            'fire_pixel_history_length': len(self.fire_pixel_history),
            'consecutive_static_detections': self.consecutive_static_detections,
            'fire_shape_variance_avg': np.mean(list(self.fire_shape_variance_history)) if self.fire_shape_variance_history else 0,
            'orange_clothing_detections': len([h for h in self.orange_clothing_pixel_history if h.get('is_clothing', False)]),
            'static_fire_threshold': self.static_fire_threshold
        }

    def detect_orange_clothing_advanced(self, frame, detection_bbox):
        """Advanced orange clothing detection"""
        try:
            x1, y1, x2, y2 = map(int, detection_bbox)
            
            detection_region = frame[y1:y2, x1:x2]
            if detection_region.size == 0:
                return False, "empty_region"
            
            hsv_region = cv2.cvtColor(detection_region, cv2.COLOR_BGR2HSV)
            
            orange_clothing_ranges = [
                (np.array([10, 100, 100]), np.array([25, 255, 255])),
                (np.array([5, 80, 120]), np.array([30, 255, 255]))
            ]
            
            total_orange_pixels = 0
            for lower, upper in orange_clothing_ranges:
                mask = cv2.inRange(hsv_region, lower, upper)
                total_orange_pixels += cv2.countNonZero(mask)
            
            total_pixels = detection_region.shape[0] * detection_region.shape[1]
            orange_ratio = total_orange_pixels / total_pixels
            
            gray_region = cv2.cvtColor(detection_region, cv2.COLOR_BGR2GRAY)
            
            texture_variance = np.std(gray_region)
            edges = cv2.Canny(gray_region, 50, 150)
            edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
            
            high_orange_content = orange_ratio > 0.4
            uniform_texture = texture_variance < 35
            low_edge_density = edge_density < 0.15
            
            height, width = detection_region.shape[:2]
            aspect_ratio = width / max(height, 1)
            regular_shape = 0.5 < aspect_ratio < 2.0
            
            clothing_score = sum([high_orange_content, uniform_texture, low_edge_density, regular_shape])
            is_clothing = clothing_score >= 3
            
            reason = f"orange_{orange_ratio:.2f}_texture_{texture_variance:.1f}"
            
            self.orange_clothing_pixel_history.append({
                'bbox': detection_bbox,
                'orange_ratio': orange_ratio,
                'is_clothing': is_clothing,
                'score': clothing_score
            })
            
            return is_clothing, reason
            
        except Exception as e:
            print(f"Error in clothing detection: {e}")
            return False, "detection_error"
        
    def reset_static_detection_counter(self):
        """Reset static detection counter when detection changes significantly"""
        print(f"DEBUG: Resetting static detection counter from {self.consecutive_static_detections} to 0")
        self.consecutive_static_detections = 0
        print("Static detection counter reset - new detection pattern detected")

    def is_same_pixel_detection_advanced(self, current_bbox):
        """Advanced same-pixel detection with enhanced debug output"""
        print(f"DEBUG: Static detection - History length: {len(self.fire_pixel_history)}")
        print(f"DEBUG: Static detection - Current bbox: {current_bbox}")
        print(f"DEBUG: Static fire threshold: {self.static_fire_threshold}")
        
        if len(self.fire_pixel_history) == 0:
            print("DEBUG: No history for static detection")
            return False, 0.0, "no_history"
        
        max_overlap = 0.0
        overlaps_with_recent = []
        
        recent_history = list(self.fire_pixel_history)[-6:]
        print(f"DEBUG: Checking against {len(recent_history)} recent detections")
        
        for i, prev_bbox in enumerate(recent_history):
            overlap = self.calculate_pixel_overlap_fast(current_bbox, prev_bbox)
            max_overlap = max(max_overlap, overlap)
            overlaps_with_recent.append(overlap)
            print(f"DEBUG: Overlap with detection {i}: {overlap:.3f}")
        
        avg_recent_overlap = np.mean(overlaps_with_recent) if overlaps_with_recent else 0.0
        variance_score, variance_reason = self.analyze_fire_shape_variance(current_bbox)
        
        print(f"DEBUG: Max overlap: {max_overlap:.3f}")
        print(f"DEBUG: Avg recent overlap: {avg_recent_overlap:.3f}")
        print(f"DEBUG: Variance score: {variance_score:.3f}")
        print(f"DEBUG: Variance reason: {variance_reason}")
        
        is_static_by_overlap = max_overlap > self.static_fire_threshold
        is_static_by_variance = variance_score < 0.2
        is_static_by_avg_overlap = avg_recent_overlap > 0.70
        
        print(f"DEBUG: Static by overlap: {is_static_by_overlap} (max_overlap {max_overlap:.3f} > {self.static_fire_threshold})")
        print(f"DEBUG: Static by variance: {is_static_by_variance} (variance {variance_score:.3f} < 0.2)")
        print(f"DEBUG: Static by avg overlap: {is_static_by_avg_overlap} (avg {avg_recent_overlap:.3f} > 0.70)")
        
        is_static = (is_static_by_overlap and is_static_by_variance) or is_static_by_avg_overlap
        
        analysis_reason = f"max_overlap_{max_overlap:.3f}_avg_{avg_recent_overlap:.3f}_{variance_reason}"
        
        if is_static:
            self.consecutive_static_detections += 1
            print(f"DEBUG: STATIC DETECTED! Consecutive count now: {self.consecutive_static_detections}")
        else:
            print(f"DEBUG: NOT STATIC - Resetting consecutive count from {self.consecutive_static_detections} to 0")
            self.consecutive_static_detections = 0
        
        print(f"DEBUG: Final static result - is_static: {is_static}, max_overlap: {max_overlap:.3f}")
        print(f"DEBUG: Analysis reason: {analysis_reason}")
        
        return is_static, max_overlap, analysis_reason

    def initialize_counters_if_needed(self):
        """Initialize counters if they don't exist"""
        if not hasattr(self, 'single_method_frame_counter'):
            self.single_method_frame_counter = 0
            print("DEBUG: Initialized single_method_frame_counter to 0")
        
        if not hasattr(self, 'consecutive_static_detections'):
            self.consecutive_static_detections = 0
            print("DEBUG: Initialized consecutive_static_detections to 0")
        
        if not hasattr(self, 'static_fire_threshold'):
            self.static_fire_threshold = 0.65
            print(f"DEBUG: Initialized static_fire_threshold to {self.static_fire_threshold}")

    def get_debug_static_info(self):
        """Get debug information about static detection state"""
        return {
            'fire_pixel_history_length': len(self.fire_pixel_history),
            'consecutive_static_detections': getattr(self, 'consecutive_static_detections', 0),
            'static_fire_threshold': getattr(self, 'static_fire_threshold', 0.65),
            'single_method_frame_counter': getattr(self, 'single_method_frame_counter', 0),
            'fire_shape_variance_history_length': len(self.fire_shape_variance_history) if hasattr(self, 'fire_shape_variance_history') else 0
        }

    def is_smoke_detection_valid(self, confidence, frame, detection_bbox=None):
        """Smoke detection validation"""
        try:
            # Basic confidence check
            if confidence < 35.0:
                return False, f"below_minimum_{confidence:.1f}%"
            
            # Environment-based adaptive threshold
            environment = self.analyze_environment(frame)
            adaptive_threshold = self.calculate_adaptive_thresholds(environment, [], [confidence])[1]
            
            if confidence < adaptive_threshold:
                return False, f"below_adaptive_threshold_{confidence:.1f}%<{adaptive_threshold:.1f}%"
            
            return True, f"smoke_validated_{confidence:.1f}%"
            
        except Exception as e:
            return False, f"validation_error_{str(e)}"



