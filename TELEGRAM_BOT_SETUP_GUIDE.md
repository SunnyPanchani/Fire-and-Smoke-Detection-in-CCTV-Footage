# Telegram Bot Setup Guide for Enhanced Fire Detection System

## Overview
This guide will help you set up the enhanced fire detection system with Telegram bot integration for scheduled camera monitoring and person detection alerts.

## 📋 Prerequisites

### 1. Python Environment
- Python 3.8 or higher
- pip (Python package manager)

### 2. Existing Files (Keep your current files)
- `lan.txt` - Camera configuration
- `data.txt` - Camera credentials  
- `google.txt` - Email configuration
- `tel.txt` - Telegram chat IDs
- `lumi.onnx` - Fire/Smoke detection model
- `person.onnx` - Person detection model
- All other existing Python files

## 🚀 Step-by-Step Setup

### Step 1: Install Required Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install python-telegram-bot==20.7
pip install opencv-python==4.8.1.78
pip install numpy==1.24.3
pip install psutil==5.9.5
pip install requests==2.31.0
pip install pillow==10.0.1
pip install schedule==1.2.0
```

### Step 2: Update Your Configuration Files

#### A. Update `tel.txt` (Telegram Configuration)
Your current `tel.txt` should contain:
```
926902525
```

For multiple users, you can add comma-separated chat IDs:
```
926902525,123456789,987654321
```

#### B. Verify `lan.txt` (Camera Configuration)
Your current `lan.txt` should look like:
```
Cam1=rtsp://admin:admin456@192.168.1.150:554/cam/realmonitor?channel=1&subtype=1
Cam2=rtsp://admin:admin456@192.168.1.150:554/cam/realmonitor?channel=2&subtype=1
Cam3=rtsp://admin:admin456@192.168.1.150:554/cam/realmonitor?channel=3&subtype=1
Cam4=rtsp://admin:admin456@192.168.1.150:554/cam/realmonitor?channel=4&subtype=1
Cam5=rtsp://admin:admin456@192.168.1.150:554/cam/realmonitor?channel=5&subtype=1
```

### Step 3: Bot Token Configuration

The bot token is already configured in the code:
- **Bot Token**: `   `
- **Authorized User ID**: ` ` (your Telegram ID)

### Step 4: File Organization

Place all new files in your project directory alongside existing files:

```
your_project_folder/
├── existing files:
│   ├── every.py (original)
│   ├── security.py
│   ├── config.py
│   ├── config_manager.py
│   ├── system_utils.py
│   ├── alerting.py
│   ├── file_utils.py
│   ├── lan.txt
│   ├── data.txt
│   ├── google.txt
│   ├── tel.txt
│   ├── lumi.onnx
│   └── person.onnx
├── new files:
│   ├── enhanced_every.py (NEW MAIN FILE)
│   ├── telegram_bot_handler.py
│   ├── scheduled_camera_processor.py
│   ├── person_detection.py
│   └── requirements.txt
└── created automatically:
    ├── logs/ (directory)
    ├── camera_schedule.json
    └── active_schedules.json
```

### Step 5: Start the Enhanced System

Run the new enhanced version:
```bash
python enhanced_every.py
```

## 🤖 Bot Commands and Usage

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Welcome message and help | `/start` |
| `/help` | Detailed help information | `/help` |
| `/schedule` | Interactive camera scheduling | `/schedule` |
| `/list` | List all scheduled cameras | `/list` |
| `/status` | Current active cameras | `/status` |
| `/cameras` | Available cameras | `/cameras` |
| `/stop CamName` | Stop specific camera | `/stop Cam1` |

### Quick Scheduling Format

Send these messages directly to the bot:

#### Time-Based Scheduling
```
Cam1 00:00-06:00    # Midnight to 6 AM
Cam2 18:00-23:00    # 6 PM to 11 PM  
Cam3 22:00-06:00    # 10 PM to 6 AM (overnight)
```

#### 24/7 Monitoring
```
Cam1 all            # Continuous monitoring
```

#### Stop Monitoring
```
Cam1 off            # Stop scheduled monitoring
```

### Interactive Scheduling
1. Send `/schedule`
2. Click on camera button
3. Follow the prompted format

## 📱 Bot Setup in Telegram

### 1. Find Your Bot
- Search for your bot name: `camsnapshot` (or the name you gave it)
- Start a conversation with `/start`

### 2. Verify Authorization
- Only user ID `926902525` can control the bot
- Other users will receive "Unauthorized access denied"

### 3. Test Basic Commands
```
/start              # Should show welcome message
/cameras            # Should list Cam1-Cam5
Cam1 all            # Should schedule Cam1 for 24/7
/status             # Should show Cam1 as active
/stop Cam1          # Should stop Cam1
```

## 🔧 System Features

### Person Detection Alerts
- Activated when cameras are scheduled
- Multi-frame validation (3 consecutive frames)
- 5-minute cooldown between alerts
- Confidence threshold: 60%
- Sends image with bounding boxes

### Schedule Management
- Daily recurring schedules
- Automatic start/stop based on time
- Overnight time ranges supported (e.g., 22:00-06:00)
- JSON-based schedule storage

### Error Recovery
- Auto-restart on camera failures
- Schedule persistence across restarts
- Comprehensive logging
- Internet connectivity monitoring

## 📁 Generated Files

The system automatically creates:

### `camera_schedule.json`
```json
{
  "Cam1": {
    "camera": "Cam1",
    "time_range": "custom",
    "start_time": "00:00",
    "end_time": "06:00",
    "enabled": true,
    "created": "2025-01-12 10:30:00"
  }
}
```

### `active_schedules.json`
```json
{
  "Cam1": {
    "schedule": {...},
    "started_at": "2025-01-12T00:00:00",
    "status": "active"
  }
}
```

## 🚨 Alert Examples

### Person Detection Alert
```
PERSON DETECTED - Cam1
==================================================
👤 Persons Detected: 2  
📊 Highest Confidence: 87.3%
📍 Location: Camera Cam1
🕒 Time: 2025-01-12 02:15:30
📸 Evidence: Cam1_PERSON_2025-01-12_02-15-30.jpg

🎯 Detection Details:
  • Person 1: 87.3% confidence
  • Person 2: 72.1% confidence

🤖 Scheduled Monitoring System:
  • Multi-frame validation: PASSED ✅
  • Detection threshold: 60%
  • Buffer validation: 3 frames
  • Alert cooldown: 5 minutes
```

## 🔍 Troubleshooting

### Bot Not Responding
1. Check internet connection
2. Verify bot token in code
3. Ensure user ID matches ` `
4. Restart the system

### Cameras Not Starting
1. Check `lan.txt` format
2. Verify camera URLs are accessible
3. Check logs in `logs/` directory
4. Ensure AI models (`lumi.onnx`, `person.onnx`) are present

### Schedule Not Working
1. Use correct format: `Cam1 00:00-06:00`
2. Check available cameras with `/cameras`
3. View logs for errors
4. Verify time format (24-hour, HH:MM)

### Person Detection Issues
1. Check `person.onnx` model file
2. Verify camera feed quality
3. Adjust confidence threshold if needed
4. Check detection logs

## 📊 Monitoring and Logs

### Log Files (created in `logs/` directory)
- `enhanced_fire_detection.log` - Main system log
- `telegram_bot.log` - Bot-specific events

### System Status
- Monitor via `/status` command
- Check console output
- Review log files for errors

## 🔐 Security Notes

- Bot only responds to authorized user ID (926902525)
- All camera URLs and credentials stored locally
- No data sent to external servers except Telegram
- Local file storage for schedules

## 💡 Usage Tips

1. **Test with short schedules first**: Try `Cam1 now+5min` format for testing
2. **Use overnight schedules**: Perfect for `22:00-06:00` home security
3. **Monitor multiple cameras**: Each can have different schedules
4. **Check status regularly**: Use `/status` to verify active cameras
5. **Stop when needed**: Use `/stop CamName` to immediately stop monitoring

## 📞 Support

If you encounter issues:
1. Check the console output for error messages
2. Review log files in the `logs/` directory
3. Ensure all dependencies are installed
4. Verify configuration files are properly formatted
5. Test with a single camera first before scheduling multiple cameras

---

**System Ready!** Your enhanced fire detection system with Telegram bot is now configured for both fire detection and scheduled person monitoring.