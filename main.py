#!/usr/bin/env python3
"""
Main Runner Script
Executes la-detect.py first, then check.py after 10 seconds
"""

import subprocess
import time
import sys
import os
from datetime import datetime

def print_header():
    """Print script header"""
    print("=" * 60)
    print("🚀 FIRE DETECTION SYSTEM LAUNCHER")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📋 Execution sequence:")
    print("   1. Run la-detect.py (RTSP scanner)")
    print("   2. Wait 10 seconds")
    print("   3. Run every.py (Pi optimization)")
    print("=" * 60)

def run_script(script_name, description):
    """
    Run a Python script and handle errors
    
    Args:
        script_name (str): Name of the script file
        description (str): Description for logging
    
    Returns:
        bool: True if successful, False if failed
    """
    print(f"\n🔄 {description}")
    print(f"📄 Executing: {script_name}")
    print("-" * 40)
    
    # Check if script exists
    if not os.path.exists(script_name):
        print(f"❌ ERROR: {script_name} not found!")
        return False
    
    try:
        # Run the script
        result = subprocess.run(
            [sys.executable, script_name], 
            capture_output=False,  # Show output in real-time
            text=True,
            check=True
        )
        
        print(f"✅ {script_name} completed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: {script_name} failed with exit code {e.returncode}")
        return False
        
    except FileNotFoundError:
        print(f"❌ ERROR: Python interpreter not found")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: Unexpected error running {script_name}: {e}")
        return False

def main():
    """Main execution function"""
    print_header()
    
    # Step 1: Run la-detect.py
    success1 = run_script("la-detect.py", "STEP 1: Running RTSP Scanner")
    
    if not success1:
        print(f"\n⚠️  WARNING: la-detect.py failed, but continuing...")
    
    # Step 2: Wait 10 seconds
    print(f"\n⏳ STEP 2: Waiting 10 seconds...")
    for i in range(10, 0, -1):
        print(f"   ⏱️  {i} seconds remaining...", end='\r')
        time.sleep(1)
    print("   ✅ Wait complete!             ")
    
    # Step 3: Run every.py
    success2 = run_script("every.py", "STEP 3: Running Raspberry Pi Optimization")
    
    # Final status
    print("\n" + "=" * 60)
    print("🏁 EXECUTION SUMMARY")
    print("=" * 60)
    print(f"📄 la-detect.py: {'✅ SUCCESS' if success1 else '❌ FAILED'}")
    print(f"📄 every.py:    {'✅ SUCCESS' if success2 else '❌ FAILED'}")
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success1 and success2:
        print("🎉 All scripts executed successfully!")
        print("🔥 Ready to run your fire detection system!")
    else:
        print("⚠️  Some scripts failed. Check the errors above.")
    
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Execution interrupted by user")
        print("👋 Goodbye!")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        sys.exit(1)