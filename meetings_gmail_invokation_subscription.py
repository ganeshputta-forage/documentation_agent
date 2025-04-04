from flask import Flask, request, jsonify
import base64
from bs4 import BeautifulSoup
import json

app = Flask(__name__)

def extract_links(email_body):
    """Extracts all links from an email body."""
    soup = BeautifulSoup(email_body, "html.parser")
    links = soup.find_all("a")
    
    link_dict = {}
    for link in links:
        link_text = link.get_text(strip=True)
        link_url = link.get("href")
        if link_text and link_url:
            link_dict[link_text] = link_url
    
    return link_dict

@app.route('/email-webhook', methods=['POST'])
def email_webhook():
    """Handles incoming email notifications from Google Pub/Sub."""
    try:
        # 🔹 Parse incoming JSON data
        data = request.get_json()
        
        if not data or "message" not in data:
            return jsonify({"error": "Invalid request"}), 400

        # 🔹 Decode the Pub/Sub message payload
        message_data = data["message"].get("data")
        if not message_data:
            return jsonify({"error": "No email body received"}), 400
        
        email_body = base64.urlsafe_b64decode(message_data).decode("utf-8")

        # 🔹 Extract links from the email body
        extracted_links = extract_links(email_body)

        return jsonify({
            "status": "success",
            "extracted_links": extracted_links
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
