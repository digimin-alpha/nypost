# nypost_bot.py

import os
import requests
import hashlib
from twilio.rest import Client
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables from .env file for local testing
load_dotenv()

# Your Account SID and Auth Token from twilio.com/console
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
# Your Twilio phone number (e.g., "+15017122661")
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER")
# The phone number to send the message to (e.g., "+15558675310")
RECIPIENT_NUMBER = os.environ.get("RECIPIENT_NUMBER")
# The URL to the NY Post Entertainment section
NYPOST_URL = "https://nypost.com/entertainment/"

def get_content_hash():
    """
    Fetches the NY Post entertainment page, extracts key content, and returns a hash.
    This hash is used to detect if the content has changed since the last run.
    """
    print("Fetching content from NY Post...")
    try:
        response = requests.get(NYPOST_URL, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # We'll grab headlines and image links from the main article grid.
        articles = soup.select('article.post-item')
        
        content = []
        for article in articles:
            # Get the headline
            headline_element = article.select_one('h3.entry-heading a')
            if headline_element:
                headline = headline_element.get_text(strip=True)
                content.append(headline)
            
            # Get the image URL. Using a placeholder if no image is found.
            image_element = article.select_one('img')
            image_url = image_element['src'] if image_element and 'src' in image_element.attrs else 'No Image'
            content.append(image_url)
            
        # Join the list into a single string to create a hash.
        content_string = "".join(content)
        return hashlib.md5(content_string.encode('utf-8')).hexdiffest()
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page: {e}")
        return None

def send_update_message():
    """
    Sends an SMS message with the latest headlines and images using Twilio.
    """
    print("Content has changed! Sending message...")
    try:
        # Get the latest headlines and images for the message.
        response = requests.get(NYPOST_URL, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.select('article.post-item')

        messages = []
        media_urls = []
        for article in articles[:5]: # Get the top 5 stories
            headline_element = article.select_one('h3.entry-heading a')
            if headline_element:
                headline = headline_element.get_text(strip=True)
                messages.append(f"Headline: {headline}")
            
            image_element = article.select_one('img')
            if image_element and 'src' in image_element.attrs:
                image_url = image_element['src']
                if not image_url.startswith('data:'): # Exclude Base64 images
                    media_urls.append(image_url)

        message_body = "NY Post Entertainment Section Update:\n\n" + "\n\n".join(messages)

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Send a separate message for media since Twilio has media limits.
        if media_urls:
            client.messages.create(
                body=message_body,
                from_=TWILIO_NUMBER,
                to=RECIPIENT_NUMBER,
                media_url=media_urls
            )
        else:
            client.messages.create(
                body=message_body,
                from_=TWILIO_NUMBER,
                to=RECIPIENT_NUMBER
            )

        print("Message sent successfully.")

    except Exception as e:
        print(f"Error sending message with Twilio: {e}")

if __name__ == '__main__':
    # This script will run and check for changes.
    # We will use an environment variable to persist the last state.
    
    current_hash = get_content_hash()
    
    if current_hash:
        # Get the hash from the last successful run from the environment.
        last_hash = os.environ.get("LAST_HASH")
        
        if current_hash != last_hash:
            # Content has changed, so send the message.
            send_update_message()
            # In a production environment, you would update the LAST_HASH environment variable.
            # This is not possible directly from the script, so this logic is for a
            # stateless cron job that relies on the external system (Render) to update the env var.
            print("To make this work in Render, you need to update the LAST_HASH environment variable to:", current_hash)
        else:
            print("No changes detected. Nothing to do.")
