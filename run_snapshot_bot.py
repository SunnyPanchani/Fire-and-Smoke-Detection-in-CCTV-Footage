# run_snapshot_bot.py - Simple runner for the Telegram snapshot bot
import os
import sys
import subprocess
import time
from datetime import datetime

def install_requirements():
    """Install required packages if not present"""
    required_packages = [
        'python-telegram-bot==20.7'
     
    ]
    
    print("Checking required packages...")
    
    for package in required_packages:
        try:
            package_name = package.split('==')[0].replace('-', '_')
            if package_name == 'python_telegram_bot':
                import telegram
            elif package_name == 'opencv_python':
                import cv2
            elif package_name == 'asyncio':
                import asyncio
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"Installing {package}...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✓ {package} installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to install {package}: {e}")
                return False
    
    return True

def check_config_files():
    """Check if required config files exist"""
    required_files = [
        'config_manager.py',
        'camera_snapshot.py',
        'alerting.py',
        'config.py',
        'lan.txt'  # Camera configuration file
    ]
    
    print("Checking required files...")
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file} found")
        else:
            print(f"✗ {file} missing")
            missing_files.append(file)
    
    if missing_files:
        print(f"\nMissing files: {', '.join(missing_files)}")
        print("Please ensure all required files are in the same directory.")
        return False
    
    return True

def test_telegram_config():
    """Test if Telegram configuration is valid in the bot script"""
    try:
        print("Testing Telegram configuration in bot script...")
        
        # Read the bot script to check configuration
        if not os.path.exists('telegram_bot_snapshot.py'):
            print("✗ telegram_bot_snapshot.py not found")
            return False
        
        with open('telegram_bot_snapshot.py', 'r') as f:
            content = f.read()
        
        # Check if BOT_TOKEN is configured
        if 'BOT_TOKEN = "8274205287:AAFVYWGa7rB_3fwttHbT3M_2YnaBffZMaq0"' in content:
            print("✗ BOT_TOKEN not configured")
            print("Please edit telegram_bot_snapshot.py and set your BOT_TOKEN")
            return False
        
        # Check if CHAT_ID is configured  
        if 'CHAT_ID = "926902525"' in content:
            print("✗ CHAT_ID not configured")
            print("Please edit telegram_bot_snapshot.py and set your CHAT_ID")
            return False
        
        print("✓ Bot script appears to be configured")
        print("  (BOT_TOKEN and CHAT_ID have been updated)")
        
        return True
        
    except Exception as e:
        print(f"✗ Error checking bot configuration: {e}")
        return False

def run_bot():
    """Run the Telegram bot"""
    try:
        print(f"\n{'='*50}")
        print(f"Starting Camera Snapshot Bot")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}\n")
        
        # Import and run bot
        from telegram_bot_snapshot import main
        main()
        
    except KeyboardInterrupt:
        print("\n\nBot stopped by user (Ctrl+C)")
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure telegram_bot_snapshot.py is in the same directory")
    except Exception as e:
        print(f"Error running bot: {e}")
        return False
    
    return True

def main():
    """Main function"""
    print("Camera Snapshot Bot Runner")
    print("=" * 40)
    
    # Step 1: Install requirements
    if not install_requirements():
        print("Failed to install required packages. Exiting.")
        return
    
    print()
    
    # Step 2: Check config files
    if not check_config_files():
        print("Missing required files. Exiting.")
        return
    
    print()
    
    # Step 3: Test Telegram config
    if not test_telegram_config():
        print("Telegram configuration invalid. Exiting.")
        return
    
    print()
    
    # Step 4: Run the bot
    print("All checks passed! Starting bot...")
    time.sleep(2)
    
    run_bot()

if __name__ == "__main__":
    main()