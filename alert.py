# pip install twilio smtplib


from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from ultralytics import YOLO
# Twilio SMS setup
def send_sms_alert(body):
    account_sid = "your_twilio_sid"
    auth_token = "your_twilio_auth_token"
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=body,
        from_="+1234567890",  # Your Twilio number
        to="+919876543210"   # Your phone
    )
    print("SMS sent:", message.sid)

# Email setup
def send_email_alert(subject, body, to_email):
    sender_email = "youremail@gmail.com"
    sender_password = "your_app_password"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
    print("Email sent to", to_email)



model = YOLO("yolo11m-cls.pt")

results = model.predict("test.jpg")  # Or frame from webcam
probs = results[0].probs.data.tolist()
class_names = results[0].names

fire_prob = 0
smoke_prob = 0

for idx, prob in enumerate(probs):
    if class_names[idx].lower() == "fire":
        fire_prob = prob * 100
    elif class_names[idx].lower() == "smoke":
        smoke_prob = prob * 100

print(f"Fire: {fire_prob:.2f}% | Smoke: {smoke_prob:.2f}%")

# Alert condition
if fire_prob >= 50 and smoke_prob >= 75:
    alert_msg = f"🚨 ALERT: Fire {fire_prob:.1f}% | Smoke {smoke_prob:.1f}% detected!"
    send_sms_alert(alert_msg)
    send_email_alert("🔥 Fire-SMoke Alert", alert_msg, "targetemail@example.com")
