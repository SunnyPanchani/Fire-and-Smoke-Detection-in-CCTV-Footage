# file_utils.py - File management, cleanup, and logging utilities
import os
import time
import logging
from datetime import datetime
from config import BASE_DIR, ALERTS_DIR, ALERTS_FOLDER_MAX_SIZE, LOG_FILE_MAX_SIZE

def get_folder_size(folder_path):
    """Calculate total size of all files in folder"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        print(f"❌ Error calculating folder size: {e}")
    return total_size

def cleanup_alerts_folder():
    """Clean up alerts folder if it exceeds size limit"""
    try:
        current_size = get_folder_size(ALERTS_DIR)
        
        if current_size <= ALERTS_FOLDER_MAX_SIZE:
            return False
        
        print(f"🧹 Alerts folder cleanup needed: {current_size/1024/1024:.2f}MB > {ALERTS_FOLDER_MAX_SIZE/1024/1024:.2f}MB")
        
        # Get all files with their modification times
        files_info = []
        for filename in os.listdir(ALERTS_DIR):
            filepath = os.path.join(ALERTS_DIR, filename)
            if os.path.isfile(filepath):
                try:
                    mtime = os.path.getmtime(filepath)
                    size = os.path.getsize(filepath)
                    files_info.append((filepath, mtime, size))
                except Exception as e:
                    print(f"❌ Error getting file info for {filename}: {e}")
        
        # Sort by modification time (oldest first)
        files_info.sort(key=lambda x: x[1])
        
        # Delete oldest files until we're under the limit
        deleted_count = 0
        deleted_size = 0
        
        for filepath, mtime, size in files_info:
            if current_size - deleted_size <= ALERTS_FOLDER_MAX_SIZE * 0.8:  # Keep 20% buffer
                break
            
            try:
                os.remove(filepath)
                deleted_count += 1
                deleted_size += size
                current_size -= size
                print(f"🗑️ Deleted old alert: {os.path.basename(filepath)} ({size/1024:.1f}KB)")
            except Exception as e:
                print(f"❌ Error deleting {filepath}: {e}")
        
        if deleted_count > 0:
            print(f"✅ Cleanup completed: {deleted_count} files deleted, {deleted_size/1024/1024:.2f}MB freed")
            print(f"📁 Alerts folder size now: {current_size/1024/1024:.2f}MB")
            return True
        
    except Exception as e:
        print(f"❌ Error during alerts folder cleanup: {e}")
    
    return False

def rotate_log_file():
    """Rotate log file if it exceeds size limit"""
    log_file_path = os.path.join(BASE_DIR, "fire_smoke_detection_log.txt")
    
    try:
        if not os.path.exists(log_file_path):
            return False
        
        current_size = os.path.getsize(log_file_path)
        
        if current_size <= LOG_FILE_MAX_SIZE:
            return False
        
        print(f"🧹 Log file rotation needed: {current_size/1024/1024:.2f}MB > {LOG_FILE_MAX_SIZE/1024/1024:.2f}MB")
        
        # Create backup of current log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BASE_DIR, f"fire_smoke_detection_log_backup_{timestamp}.txt")
        
        # Read last 50% of the file to keep recent logs
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Keep last 50% of lines
        keep_lines = lines[len(lines)//2:]
        
        # Create backup with older logs
        with open(backup_path, 'w', encoding='utf-8') as backup_f:
            backup_f.writelines(lines[:len(lines)//2])
        
        # Rewrite main log with recent logs
        with open(log_file_path, 'w', encoding='utf-8') as f:
            f.writelines(keep_lines)
            f.write(f"\n--- Log rotated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        
        new_size = os.path.getsize(log_file_path)
        backup_size = os.path.getsize(backup_path)
        
        print(f"✅ Log rotation completed:")
        print(f"   • Main log: {new_size/1024/1024:.2f}MB")
        print(f"   • Backup created: {os.path.basename(backup_path)} ({backup_size/1024/1024:.2f}MB)")
        
        # Clean up old backup files (keep only last 3)
        cleanup_old_log_backups()
        
        return True
        
    except Exception as e:
        print(f"❌ Error during log rotation: {e}")
        return False

def cleanup_old_log_backups():
    """Keep only the 3 most recent log backup files"""
    try:
        backup_files = []
        for filename in os.listdir(BASE_DIR):
            if filename.startswith("fire_smoke_detection_log_backup_") and filename.endswith(".txt"):
                filepath = os.path.join(BASE_DIR, filename)
                if os.path.isfile(filepath):
                    mtime = os.path.getmtime(filepath)
                    backup_files.append((filepath, mtime))
        
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda x: x[1], reverse=True)
        
        # Delete all but the 3 most recent
        for filepath, mtime in backup_files[3:]:
            try:
                os.remove(filepath)
                print(f"🗑️ Deleted old log backup: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"❌ Error deleting old backup {filepath}: {e}")
                
    except Exception as e:
        print(f"❌ Error during log backup cleanup: {e}")

def periodic_cleanup():
    """Perform periodic cleanup of files"""
    while True:
        try:
            # Cleanup every 10 minutes
            time.sleep(300)
            
            # Check and cleanup alerts folder
            cleanup_alerts_folder()
            
            # Check and rotate log file
            rotate_log_file()
            
        except Exception as e:
            print(f"❌ Error in periodic cleanup: {e}")
            time.sleep(60)  # Wait a minute before retrying

def setup_logging():
    """Setup logging with automatic rotation"""
    log_file_path = os.path.join(BASE_DIR, "fire_smoke_detection_log.txt")
    
    # Check if log rotation is needed before setting up logging
    rotate_log_file()
    
    # Setup logging
    logging.basicConfig(
        filename=log_file_path,
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        filemode='a'  # Append mode
    )
    
    # Log startup message
    logging.info("=" * 50)
    logging.info("Fire & Smoke Detection System Started")
    logging.info("=" * 50)