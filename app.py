import os
import requests
from flask import Flask
from twilio.rest import Client
from bs4 import BeautifulSoup

app = Flask(__name__)

# Twilio config (set in Render env vars)
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_PHONE_NUMBER")
MY_PHONE = os.getenv("MY_PHONE_NUMBER")

# Keep track of last headline sent
last_headline = None

def get_latest_story():
    url = "https://nypost.com/entertainment/"
    resp = requests.get(url, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")

    # NY Post headlines are usually in <h3> or <h4>
    article = soup.find("article")
    if not article:
        return None, None

    headline = article.get_text(strip=True)
    img = None
    img_tag = article.find("img")
    if img_tag:
        img = img_tag.get("src")

    return headline, img

def send_sms(headline, img_url):
    client = Client(TWILIO_SID, TWILIO_AUTH)
    message_body = f"NYPost Entertainment Update:\n{headline}"
    if img_url:
        client.messages.create(
            body=message_body,
            from_=TWILIO_FROM,
            to=MY_PHONE,
            media_url=[img_url]
        )
    else:
        client.messages.create(
            body=message_body,
            from_=TWILIO_FROM,
            to=MY_PHONE
        )

@app.route("/check", methods=["GET"])
def check_news():
    global last_headline
    headline, img = get_latest_story()
    if headline and headline != last_headline:
        send_sms(headline, img)
        last_headline = headline
        return f"Sent update: {headline}", 200
    return "No new updates", 200

@app.route("/")
def home():
    return "NYPost Twilio bot is running", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
