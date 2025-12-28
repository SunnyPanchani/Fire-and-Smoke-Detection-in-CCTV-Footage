Guide# 🔥 Person Detection System - Complete User Guide

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Why We Use Gmail API & Telegram Bot](#why-we-use-gmail-api--telegram-bot)
3. [Gmail Setup](#gmail-setup)
4. [Telegram Bot Setup](#telegram-bot-setup)
5. [Raspberry Pi Installation](#raspberry-pi-installation)
6. [Bot Commands & Usage](#bot-commands--usage)
7. [Alert Sound Configuration](#alert-sound-configuration)
8. [System Messages & Logs](#system-messages--logs)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 System Overview

This advanced Person detection system uses AI-powered cameras to detect person movement. It sends instant alerts through both Gmail and Telegram with images and detailed information.

**Key Features:**
- Real time Person detection with scheduling
- Multiple camera support (up to 5 cameras)
- Instant alerts with images
- 24/7 monitoring capability
- Easy remote control via Telegram bot

---

## 🔐 Why We Use Gmail API & Telegram Bot

**Privacy & Security First!**
- ✅ **Your data stays with YOU** - We don't store any personal information
- ✅ **Free of cost** - Gmail API and Telegram Bot are completely free
- ✅ **No monthly subscriptions** - One-time setup, lifetime usage
- ✅ **Full control** - You own your API keys and bot tokens
- ✅ **No mobile app needed** - Works through your existing Gmail and Telegram

This approach ensures maximum privacy while keeping costs at zero!

---

## 📧 Gmail Setup

### Step 1: Create Gmail App Password

**Important:** You'll need TWO Gmail accounts:
1. **Sender Gmail** - Your main account (sends alerts)
2. **Receiver Gmail** - Create a NEW account only for receiving alerts

#### For Sender Gmail:
1. Go to your Gmail account settings
2. Enable **2-Step Verification** first:
   - Go to https://myaccount.google.com/security
   - Click "2-Step Verification" → Turn ON
3. Generate App Password:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" → Generate
   - **Copy the 16-character password** (example: `qadgetfaqwsgtrsw`)

#### For Receiver Gmail:
1. **Create a NEW Gmail account** specifically for alerts
   - Example: `personalerts2024@gmail.com`
   - This keeps your main inbox clean and organized

### Step 2: Configure google.txt File

Create a file named `google.txt` with this format:
```
yourmain@gmail.com
qadgetfaqwsgtrsw
personalerts2024@gmail.com
```

**Line 1:** Your main Gmail address  
**Line 2:** The 16-character app password from Step 1  
**Line 3:** Your NEW receiver Gmail address  

### Step 3: Gmail Sound Alert Setup (Optional)

Make Gmail play a loud siren ONLY for alerts:

#### On Desktop Gmail:
1. Open Gmail → ⚙️ **Settings** → **Filters and Blocked Addresses**
2. Click **Create a new filter**
3. In "From" field, enter your sender email
4. Or in "Subject" field, enter:  `PERSON DETECTED`
5. Click **Create filter**
6. Check **Apply the label** → Create new label: `🔔 Person Alerts`
7. Click **Create filter**

#### On Gmail Mobile App:
1. Open Gmail app → **Settings** → **[Your Account]** → **Manage Labels**
2. Find **🔔 Person Alerts** label → Enable **Sync messages**
3. Turn ON **Label notifications**
4. Set **custom sound** → Choose a loud siren sound
5. In main Gmail Settings → **Notifications** → Select **"High Priority only"**

✅ **Result:** Only Person alert emails will make sound, normal emails stay silent!

---

## 🤖 Telegram Bot Setup

### Step 1: Create Your Bot

1. **Scan this QR code** or search `@BotFather` in Telegram:



![alt text](BotFather_qr-1.png)

2. **Click Start** button in BotFather chat
3. Send command: `/newbot`
4. **Choose bot name:** `Person Alert System` (or any name you like)
5. **Choose username:** Must end with 'bot' and be unique
6. Bot Create Video https://youtu.be/_w4VcagV8EA?si=Jz6h91E5kxOdqbaj

**⚠️ Important Username Tips:**
- ❌ Don't use: `alertbot`, `personbot`, `securitybot` (too common)
- ✅ Good examples:
  - `myhome_23785_person_alert_bot`
  - `villa23_security_bot`
  - `yourname_person_watch_bot`

6. **Copy your bot token** (example: `0000000000:ABCPD2DQGQsakqYDQbKaqlchaXIqTdsvIda`)

### Step 2: Get Your Chat ID

1. **Scan this QR code** or search `@userinfobot` in Telegram:

![alt text](userinfobot_start_qr-1.png)

2. You will get user info in this format

- Id: 123456789 (This is your chat id)

- First: Hello

- Last: World

- Lang: en




Create a file named `tel.txt` with this format:
```
For single user
0000000000:ABCPD2DQGQsakqYDQbKaqlchaXIqTdsvIda
123456789

For multiple users
0000000000:ABCPD2DQGQsakqYDQbKaqlchaXIqTdsvIda
123456789,000000002,000000003
```

**Line 1:** Your bot token  
**Line 2:** Chat IDs (comma-separated for multiple users)  

### Step 4: Start Your Bot

1. Go to your bot chat
2. Send `/start` or click **Start** button
3. You should receive a welcome message with system status
4. Without Send `/start` or click **Start** button Bot will not activate
5. For other user who want to recive aler message need to search your bot in telegram
5. Same method for other chat id user to click **Start** button to your bot

---

## 🔔 Alert Sound Configuration

### For Telegram Bot

#### 1️⃣ Pin Bot to Home Screen
1. Open chat with your **Person Alert Bot**
2. Tap **bot name** → **Add to Home Screen**
3. Quick access shortcut created!

#### 2️⃣ Set Custom Alert Sound
1. Open bot chat → Tap **bot name**
2. Tap **Notifications** → Turn ON
3. Tap **Sound** → Choose **Custom**
4. **Download loud siren sound:** https://drive.google.com/file/d/1lYLeYuFjIg5ZBLxnD287GNkQeU9axs7H/view?usp=sharing
5. Set this as your bot's notification sound

#### 3️⃣ Mute Other Chats (Recommended)
1. Telegram → **Settings** → **Notifications and Sounds**
2. Turn OFF notifications for:
   - **Private Chats**
   - **Groups**
   - **Channels**
3. Keep your **Person Alert Bot** notifications ON

✅ **Result:** Only Person alerts make sound, everything else stays silent!

---

## 🖥️ Raspberry Pi Installation

### Hardware Requirements
- **Raspberry Pi 4** (4GB RAM recommended)
- **32GB+ MicroSD Card**
- **USB Cameras** (up to 5 supported)
- **Stable Internet Connection**

### Software Installation

1. **Download Raspberry Pi OS**
   - Use Raspberry Pi Imager
   - Choose "Raspberry Pi OS (64-bit)"

2. **Enable SSH & Camera**
   ```bash
   sudo raspi-config
   # Enable SSH, Camera, and expand filesystem
   ```

3. **Install System Dependencies**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install python3-pip python3-opencv -y
   pip3 install opencv-python numpy telegram-bot-api
   ```

4. **Copy System Files**
   - Place your program files in: `/home/pi/person_detection/`
   - Copy `google.txt` and `tel.txt` to same folder

5. **Set Auto-Start on Boot**
   ```bash
   sudo nano /etc/systemd/system/person-detection.service
   ```
   
   Add this content:
   ```
   [Unit]
   Description=Person Detection System
   After=network.target
   
   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/person_detection
   ExecStart=/usr/bin/python3 /home/pi/person_detection/main.py
   Restart=always
   RestartSec=5
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   Enable the service:
   ```bash
   sudo systemctl enable person-detection.service
   sudo systemctl start person-detection.service
   ```

### System Files Created Automatically
- `detection_log.txt` - Detection events log
- `enhanced_detection.log` - Detailed system log
- `active_schedules.json` - Current camera schedules
- `camera_schedule.json` - Camera configuration

---

## 🎮 Bot Commands & Usage

### Basic Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Welcome message & system status | `/start` |
| `/help` | Show all available commands | `/help` |
| `/status` | View currently active cameras | `/status` |
| `/list` | Show all camera schedules | `/list` |
| `/cameras` | List all available cameras | `/cameras` |
| `/test` | Test bot connection | `/test` |

### Camera Scheduling

#### Simple Scheduling
```
Cam1 09:00-17:00          → Schedule 9 AM to 5 PM
Cam2 all                  → 24/7 monitoring
Cam3 off                  → Stop monitoring
```

#### Multiple Time Periods
```
Cam3 17:45-17:50 and 00:30-5:30 and 12:30-15:45
```
**Response:** `Cam3 scheduled for 17:45-17:50 and 00:30-5:30 and 12:30-15:45 person detection monitoring!`

#### Advanced Commands
```
/schedule                 → Interactive scheduling menu
/stop Cam1               → Stop specific camera
hello                    → Quick help (casual greeting)
```

### Sample Bot Responses

#### Scheduling Status (`/list`)
```
Current Camera Schedules

Cam3   Status: Active   11:06 - 11:10   Created: 2025-09-13T11:05
Cam2   Status: Active   10:25 - 10:28   Created: 2025-09-13T10:24  
Cam1   Status: Active   15:33 - 15:49   Created: 2025-09-14T15:34
Cam4   Status: Active   24/7 Monitoring Created: 2025-09-14T16:44

Total: 4 scheduled cameras
Use /status to see which cameras are currently active.
```

#### Current Status (`/status`)
```
👤 PERSON DETECTION: Currently Active Cameras

Cam1: ✅ Active (15:33-15:49)
Cam4: ✅ Active (24/7 Monitoring)

Cam2: 💤 Scheduled (10:25-10:28) - Waiting
Cam3: 💤 Scheduled (11:06-11:10) - Waiting
Cam5: ⚪ Not Scheduled

System Status: ✅ All Systems Operational
```

---

## 📱 System Messages & Logs

### Telegram Startup Message
```
🚨 ALERT - SYSTEM NOTIFICATION
==================================================
Title: ENHANCED SYSTEM READY - AUTO-WELCOME BOT ACTIVE
Time: 2025-09-18 16:22:49
Platform: Raspberry Pi 4
Status: SUCCESS
==================================================

🔥 ENHANCED DETECTION SYSTEM READY!

SYSTEM STATUS: OPERATIONAL
Time: 2025-09-18 16:22:49

Person DETECTION: ✅
• AI Models:  Person (person.onnx)
• Real-time monitoring with pixel-level tracking
• Adaptive brightness thresholds
• Object interference filtering
• Active on ALL 5 cameras

TELEGRAM BOT: ✅ READY WITH AUTO-WELCOME
• Cam1 • Cam2 • Cam3 • Cam4 • Cam5

📋 AVAILABLE COMMANDS:
/start - Welcome and detailed help
/schedule - Interactive camera scheduling 
/list - View all current schedules
/status - See active cameras right now
/cameras - List all available cameras
/stop CamName - Stop specific camera
/help - Show help message
/test - Test bot connection

⚡ INSTANT SCHEDULING (Just send these messages):
• "Cam1 00:00-06:00" - Schedule midnight to 6 AM
• "Cam1 all" - Schedule 24/7 monitoring
• "Cam1 off" - Stop monitoring

🎯 DETECTION TYPES:
• PERSON ALERTS: Only on scheduled cameras

📡 COMMUNICATION:
• Email: ✅ Configured
• Telegram: ✅ Active - Multiple chats

🤖 BOT FEATURES:
✅ Auto-welcome for new users - NO /start required
✅ Send any message to get instant welcome and help
✅ Commands work immediately on first interaction
✅ Casual greetings ("hello", "hi") show quick help
✅ Error handling with informative messages
✅ Connection monitoring and auto-recovery

👋 USER EXPERIENCE:
• First-time users get auto-welcomed with quick help
• Existing users get immediate command processing
• Send "hello" or any text to get started instantly
• All commands work without preliminary setup
• Bot remembers welcomed users for smooth experience

🎉 SYSTEM READY!
• Send ANY message to bot to get started (no /start needed)
• Bot will auto-welcome and show available commands
• Example: Send "Cam1 all" to start 24/7 person monitoring

The bot is now truly ready for instant use without requiring /start command!

✅ Bot Started Successfully
All systems online and ready for commands!
New users are auto-welcomed.
```

### Gmail Startup Message
```
Subject: 🔥 Person DETECTION SYSTEM - READY

ENHANCED SYSTEM READY - AUTO-WELCOME BOT ACTIVE
==================================================
Time: 2025-09-18 16:22:49
Platform: Raspberry Pi 4
Status: SUCCESS
==================================================

ENHANCED PERSON DETECTION SYSTEM READY!
SYSTEM STATUS: OPERATIONAL

PERSON DETECTION: AI Models Active
- Person Detection (person.onnx)
- Real-time monitoring with pixel-level tracking
- Adaptive brightness thresholds
- Active on ALL 5 cameras

TELEGRAM BOT: READY WITH AUTO-WELCOME
Available Cameras: Cam1, Cam2, Cam3, Cam4, Cam5

DETECTION TYPES:
- PERSON ALERTS: Only on scheduled cameras

COMMUNICATION:
- Email: Configured and Ready
- Telegram: Active with Multiple Chat Support

SYSTEM READY!
Telegram bot is ready for instant commands.

Bot Started Successfully - All systems operational!
```


### Person Alert Message (Telegram)
```
🚨 ALERT - PERSON DETECTED - Cam1
==================================================

Alert Number: #1
Persons Detected: 1
Highest Confidence: 79.0%
Location: Camera Cam1
Time: 2025-09-14 15:45:05
Evidence: Cam1_PERSON_Alert1_2025-09-14_15-45-05.jpg

Detection Details:
• Person 1: 79.0% confidence

Scheduled Monitoring System:
• Multi-frame validation: PASSED
• Detection threshold: 60%
• Buffer validation: 3 frames
• Alert cooldown: 5 minutes
• Session alerts: 1

[PERSON DETECTION IMAGE ATTACHED]
```

---

## 🛠️ Troubleshooting

### Common Issues

#### Gmail Not Sending Emails
- ✅ Check 2-Step Verification is enabled
- ✅ Verify app password is correct (16 characters)
- ✅ Ensure sender email is correct in google.txt
- ✅ Check internet connection

#### Telegram Bot Not Responding  
- ✅ Verify bot token is correct in tel.txt
- ✅ Check chat ID is accurate
- ✅ Ensure bot is not blocked
- ✅ Send `/start` to reactivate bot

#### Camera Detection Issues
- ✅ Check camera connections (USB)
- ✅ Verify camera permissions: `sudo chmod 666 /dev/video*`
- ✅ Test camera: `vcgencmd get_camera`
- ✅ Check system logs: `/home/pi/person_detection/enhanced_detection.log`

#### System Not Auto-Starting
```bash
# Check service status
sudo systemctl status person-detection.service

# View logs
sudo journalctl -u person-detection.service -f

# Restart service
sudo systemctl restart person-detection.service
```

### Log File Locations
- **Detection Log:** `detection_log.txt`
- **System Log:** `enhanced_detection.log`
- **Schedules:** `active_schedules.json`
- **Camera Config:** `camera_schedule.json`

### Support Commands
```bash
# Check system status
/status

# Test bot connection  
/test

# View current schedules
/list

# Get help
/help
```

---

## 🎯 Quick Start Checklist

- [ ] Create two Gmail accounts (sender + receiver)
- [ ] Enable 2-Step Verification and generate App Password
- [ ] Create google.txt file with correct format
- [ ] Create Telegram bot via @BotFather
- [ ] Get bot token and chat IDs
- [ ] Create tel.txt file with correct format
- [ ] Install system on Raspberry Pi
- [ ] Configure auto-start service
- [ ] Test both Gmail and Telegram alerts
- [ ] Set up custom alert sounds
- [ ] Schedule your cameras using bot commands

**🎉 Congratulations! Your Detection System is now ready to protect your property 24/7!**

---

*For additional support, check the system logs and use bot commands for troubleshooting. The system is designed to be maintenance-free once properly configured.*