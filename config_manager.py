# config_manager.py - Configuration file loading and management
import os
import sys
from config import BASE_DIR

# Single bot token for both camera scheduling AND alerts
# This ensures all communication goes through the same bot conversation
TELEGRAM_BOT_TOKEN = "8274205287:AAFVYWGa7rB_3fwttHbT3M_2YnaBffZMaq0"

def read_credentials():
    """Read camera credentials from data.txt"""
    try:
        with open(os.path.join(BASE_DIR, "data.txt"), "r") as f:
            lines = f.read().splitlines()
            username = lines[0].strip()
            password = lines[1].strip()
            return username, password
    except FileNotFoundError:
        print("Error: data.txt file not found!")
        print("Please create data.txt with:")
        print("   Line 1: Username")
        print("   Line 2: Password")
        sys.exit(1)
    except IndexError:
        print("Error: data.txt must contain at least 2 lines (username and password)")
        sys.exit(1)

def load_google_config(filename="google.txt"):
    """Load Google email configuration"""
    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        print(f"Google config file not found: {path}")
        return None, None, None
    
    with open(path, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    
    if len(lines) < 3:
        print(f"google.txt missing required lines (expected 3, got {len(lines)})")
        return None, None, None
    
    return lines[0], lines[1], lines[2]

def load_telegram_config(filename="tel.txt"):
    """Load Telegram configuration with multiple chat IDs using single bot token"""
    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        print(f"Telegram config file not found: {path}")
        return None, None
    
    try:
        with open(path, "r") as f:
            content = f.read().strip()
        
        if not content:
            print("tel.txt is empty")
            return None, None
        
        # Parse comma-separated chat IDs
        chat_ids_str = content.split(',')
        chat_ids = []
        
        for chat_id_str in chat_ids_str:
            chat_id_str = chat_id_str.strip()
            if chat_id_str:
                try:
                    chat_id = int(chat_id_str)
                    chat_ids.append(chat_id)
                except ValueError:
                    print(f"Invalid Chat ID in tel.txt: {chat_id_str}")
        
        if not chat_ids:
            print("No valid chat IDs found in tel.txt")
            return None, None
        
        print(f"Loaded {len(chat_ids)} Telegram chat IDs for unified bot")
        print(f"Bot Token: {TELEGRAM_BOT_TOKEN[:20]}...")
        return TELEGRAM_BOT_TOKEN, chat_ids
    
    except Exception as e:
        print(f"Error reading tel.txt: {e}")
        return None, None

def load_camera_streams(filename="lan.txt"):
    """Load camera stream configuration from lan.txt file"""
    camera_streams = {}
    filepath = os.path.join(BASE_DIR, filename)

    if not os.path.exists(filepath):
        print(f"{filename} not found! Please create it first.")
        return camera_streams

    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                print(f"Skipping malformed line {line_num}: {line}")
                continue
            key, value = line.split("=", 1)
            camera_streams[key.strip()] = value.strip()

    print(f"Loaded {len(camera_streams)} camera streams from {filename}")
    return camera_streams