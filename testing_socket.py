import os
import re
import json
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.web import WebClient
from slack_sdk.socket_mode.request import SocketModeRequest
from dotenv import load_dotenv

load_dotenv()

# Environment Variables (Set these before running the script)
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")  # Bot User Token (xoxb-...)
APP_LEVEL_TOKEN = os.getenv("SLACK_APP_TOKEN")  # App Token (xapp-...)
READ_AI_CHANNEL_ID = os.getenv("READ_AI_CHANNEL_ID")  # Slack channel ID where Read.ai sends summaries

# Initialize Slack Clients
slack_client = WebClient(token=SLACK_BOT_TOKEN)
socket_client = SocketModeClient(app_token=APP_LEVEL_TOKEN, web_client=slack_client)

# Regex to identify Read.ai summary messages (Optional: Adjust based on Read.ai's format)
SUMMARY_PATTERN = re.compile(r"Meeting Summary|Transcript|Notes", re.IGNORECASE)

def store_summary(summary_text):
    """ Store Read.ai summary text (Modify as needed for database, file storage, etc.) """
    with open("meeting_summaries.txt", "a", encoding="utf-8") as file:
        file.write(summary_text + "\n\n")
    print("Summary stored successfully!")

def handle_event(payload):
    """ Handles incoming Slack events and extracts Read.ai summaries """
    event = payload["event"]

    # Check if event is a message from the Read.ai channel
    if event.get("type") == "message" and event.get("channel") == READ_AI_CHANNEL_ID:
        message_text = event.get("text", "")
        
        # Check if the message is a Read.ai summary
        if SUMMARY_PATTERN.search(message_text):
            print(f"Read.ai Summary Detected: \n{message_text}")
            store_summary(message_text)  # Save the summary
        else:
            print("Message received but does not match Read.ai summary format.")

@socket_client.socket_mode_request_listeners.append
def on_event_request(client: SocketModeClient, req: SocketModeRequest):
    """ Listener for Slack Socket Mode events """
    if req.type == "events_api":
        handle_event(req.payload)
        client.ack(req)  # Acknowledge event

# Start listening for Read.ai summaries
if __name__ == "__main__":
    print("Listening for Read.ai summaries in Slack...")
    socket_client.connect()



