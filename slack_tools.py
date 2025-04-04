import requests
import time
from langchain.tools import tool
import re , json
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
import asyncio
import aiohttp
from dotenv import load_dotenv
import os
from slack_sdk import WebClient

load_dotenv()
SLACK_BOT_TOKEN  = os.getenv("SLACK_BOT_TOKEN")
# YOUR_BOT_USER_ID = os.getenv("YOUR_BOT_USER_ID")
YOUR_BOT_USER_ID = os.getenv("U08BWREB2VA")
# print(SLACK_BOT_TOKEN)
# print("Used environment variables")
client = WebClient(token=SLACK_BOT_TOKEN)

@tool
def retrieve_channel_id_by_name(channel_name):
    """
    Retrieves the Slack channel ID for a given channel name.

    This function calls the Slack API's `conversations.list` endpoint to fetch a list of all available channels 
    in the workspace. It then iterates through the list to find a channel matching the provided name.

    Args:
        channel_name (str): The name of the Slack channel (e.g., "doc_agent_msgs").

    Returns:
        str: The channel ID if found, otherwise returns None.

    Example Usage:
        channel_id = get_channel_id("doc_agent_msgs")
        print(channel_id)  # Output: "C08BRF3MZT7" (Example ID)

    Notes:
    - Requires a valid Slack Bot Token (`SLACK_BOT_TOKEN`) with `channels:read` permission.
    - If the provided channel name does not exist, the function returns `None`.
    """

    url = "https://slack.com/api/conversations.list"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    print("✔️✔️✔️✔️✔️✔️✔️✔️✔️")
    print(response)
    print("✔️✔️✔️✔️✔️✔️✔️✔️✔️")
    json_response = response.json()
    channels_list = json_response.get("channels")
    for each_channel in channels_list:
        print(each_channel)
        if each_channel.get("name") == channel_name:
            return each_channel.get("id")
        print("🟢🟢🟢🟢🟢🟢🟢🟢")

    return None  # Return None if channel not found

def get_bot_user_id(channel_id):
    try:
        # Get list of members in the channel
        response = client.conversations_members(channel=channel_id)
        members = response["members"]
        
        # Get bot user ID
        bot_info = client.auth_test()  # Fetch bot user info
        bot_user_id = bot_info["user_id"]

        if bot_user_id in members:
            return bot_user_id
        else:
            return "Bot is not a member of this channel."

    except Exception as e:
        return f"Error: {str(e)}"


# channel_id = get_channel_id("doc_agent_msgs")
# if channel_id:
#     print(f"✅ Channel ID: {channel_id}")
# else:
#     print("❌ Channel not found!")

# channel_id is C08BRF3MZT7
# @tool
# def post_message_to_channel(sending_msg_info):
#     """
#     Sends a message to a specified Slack channel using the Slack API.

#     This function posts a message to a Slack channel and retrieves the `thread_ts` (timestamp) 
#     of the sent message, which can be used for tracking replies in a threaded conversation.

#     Args:
#         sending_msg_info (dict): A dictionary containing:
#             - "channel_id" (str): The ID of the Slack channel where the message will be sent.
#             - "message" (str): The text message to be sent.

#     Returns:
#         str: The `thread_ts` (timestamp) of the sent message if successful, otherwise returns `None`.

#     Example Usage:
#         sending_msg_info = {
#             "channel_id": "C08BRF3MZT7",
#             "message": "Hello, team! Please provide an update."
#         }
#         thread_ts = send_slack_msg_to_channel(sending_msg_info)
#         print(thread_ts)  # Example output: "1738742430.840779"

#     Notes:
#     - Requires a valid Slack Bot Token (`SLACK_BOT_TOKEN`) with `chat:write` permission.
#     - If the message fails to send, the function prints an error and returns `None`.
#     - The returned `thread_ts` can be used to track responses in a thread.
#     """
#     channel_id = sending_msg_info.get("channel_id")
#     message = sending_msg_info.get("message")
#     #channel_id , message
#     url = "https://slack.com/api/chat.postMessage"
#     headers = {
#         "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
#         "Content-Type": "application/json"
#     }
#     data = {
#         "channel" : channel_id,
#         "text" : message
#     }

#     response = requests.post(url, headers=headers, json=data)
#     if response.status_code == 200 and response.json().get("ok"):
#         print("✅ Message sent successfully!")
#         sent_msg_json_response  = response.json()
#         thread_time_stamp = sent_msg_json_response["ts"]
#         return thread_time_stamp
#     else:
#         print("❌ Failed to send message:", response.json())
#     return None


async def post_message_to_channel(sending_msg_info):
    
    channel_id = sending_msg_info.get("channel_id")
    message = sending_msg_info.get("message")
    
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "channel": channel_id,
        "text": message
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                response_json = await response.json()
                if response_json.get("ok"):
                    print("✅ Message sent successfully!")
                    return response_json["ts"]
                else:
                    print("❌ Failed to send message:", response_json)
            else:
                print(f"❌ HTTP Error: {response.status}")
    return None



# @tool
# def fetch_replies_from_channel(getting_human_response_info):
#     """
#     Listens for and retrieves human responses from a Slack channel's threaded message.

#     This function continuously checks for replies in a Slack thread using the Slack API. 
#     It listens for human responses (not from the bot) in a thread, and returns the first human response it finds.

#     Args:
#         getting_human_response_info (dict): A dictionary containing:
#             - "CHANNEL_ID" (str): The ID of the Slack channel where the thread is located.
#             - "thread_ts" (str): The timestamp of the message (thread's parent message) to track responses.

#     Returns:
#         str: The text of the first human response to the thread, or `None` if no response is found.

#     Example Usage:
#         getting_human_response_info = {
#             "CHANNEL_ID": "C08BRF3MZT7",
#             "thread_ts": "1738742430.840779"
#         }
#         response = get_slack_response(getting_human_response_info)
#         print(response)  # Example output: "Sure, I will create the Notion page."

#     Notes:
#     - Requires a valid Slack Bot Token (`SLACK_BOT_TOKEN`) with `conversations:history` permission.
#     - The function checks the thread every 20 seconds until a human response is found or an error occurs.
#     - Returns only the first human response it detects, skipping the bot's own message.
#     - If there is a request failure or no response, it prints the error and exits the listening loop.
#     """
#     CHANNEL_ID = getting_human_response_info.get("CHANNEL_ID")
#     thread_ts = getting_human_response_info.get("thread_ts")

#     print("Got into listening Replies")
#     url = "https://slack.com/api/conversations.replies"
#     headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
#     params = {
#         "channel": CHANNEL_ID,
#         "ts": thread_ts  # Track responses to the specific message
#     }
#     while True:
#         try:
#             response = requests.get(url, headers=headers, params=params)     #  https://slack.com/api/conversations.replies/?channel=CHANNEL_ID&ts=thread_ts
#             if response.status_code == 200 and response.json().get("ok"):
#                 json_response = response.json()
#                 # print("🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢")
#                 # print(response.json())
#                 # print("🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢")
#                 messages = json_response.get("messages", [])
#                 # print("👁️👁️👁️👁️👁️👁️👁️👁️👁️👁️👁️")
#                 # print(len(messages))
#                 # print(messages)
#                 # print("👁️👁️👁️👁️👁️👁️👁️👁️👁️👁️👁️")

#                 YOUR_BOT_USER_ID = "B08CH4J2F88"
#                 if len(messages) > 1:  # The first message is the bot's message, so look for replies
#                     for msg in messages[1:]:  # Skip the first message
#                         if msg.get("user") != YOUR_BOT_USER_ID :  # Ensure it's a human response
#                             return msg.get("text")  # Return human response

#         except Exception as e:
#             print(e)
#             print("Request Failed , Ended listening to conversation")
#             break

#         time.sleep(20)


async def fetch_replies_from_channel(getting_human_response_info):
    CHANNEL_ID = getting_human_response_info.get("CHANNEL_ID")
    thread_ts = getting_human_response_info.get("thread_ts")

    print("🔍 Listening for replies...")

    url = "https://slack.com/api/conversations.replies"
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    params = {"channel": CHANNEL_ID, "ts": thread_ts}

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        json_response = await response.json()
                        if json_response.get("ok"):
                            messages = json_response.get("messages", [])
                            if len(messages) > 1:  # The first message is the bot's message, so look for replies
                                # print(f"message received {len(messages)}")
                                for msg in messages[1:]:  # Skip the first message
                                    # print("checked")
                                    if msg.get("user") != YOUR_BOT_USER_ID:  # Ensure it's a human response
                                        print("✅ Human response received!")
                                        return msg.get("text")  # Return human response

                    else:
                        print(f"❌ HTTP Error: {response.status}")

            except Exception as e:
                print(f"❌ Error: {e}")
                print("Request failed, stopping listening...")
                break

            await asyncio.sleep(3)  # Non-blocking sleep for 20 seconds

    return None




    
'''
def handle_sending_msg(llm_response_content: str):
    """
    Processes an LLM-generated JSON string, extracts relevant fields, and sends a message to Slack.

    This function:
    - Parses an LLM response using JsonOutputParser
    - Extracts `reason`, `new_topic_name`, and `status`
    - Sends a formatted message to Slack
    - Retrieves human responses from the Slack thread

    Parameters:
    llm_response_content (str): The JSON response from the LLM in string format.

    Returns:
    human_response (Any): Replies from users in the Slack thread.
    """

    print("**************  Received Content below ********")
    print(llm_response_content)
    print("***************************************************")
    
    # Convert LLM response string into an AIMessage object
    message = AIMessage(content=llm_response_content)

    # Parse JSON using JsonOutputParser
    output_parser = JsonOutputParser()
    try:
        json_data = output_parser.invoke(message)  # Properly parses the response
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return None  # Handle the parsing error gracefully

    # Extract relevant fields
    reason = json_data.get("reason", "")
    new_topic_name = json_data.get("new_topic_name", "")
    status = json_data.get("status", "")

    print(f"Reason: {reason}, New Topic Name: {new_topic_name}, Status: {status}")

    # Construct Slack message
    sending_msg = f"Hey, here is an update from the Agent:\n- **Reason:** {reason}\n- **New Topic Name:** {new_topic_name}\n- **Status:** {status}"

    # Define Slack channel ID
    channel_id = "C08BRF3MZT7"

    # Send message to Slack channel and get thread timestamp
    thread_ts = post_message_to_channel.invoke(
        input={"sending_msg_info": {"channel_id": channel_id, "message": sending_msg}}
    )

    # Fetch human responses from the Slack thread
    human_response = fetch_replies_from_channel.invoke(
        input={"getting_human_response_info": {"CHANNEL_ID": channel_id, "thread_ts": thread_ts}}
    )

    return human_response

# handle_sending_msg("This is making trial of sending message which is handled by thread" , 10)


'''


# def handle_sending_msg(meeting_topic):
#     """
#     Processes an LLM-generated JSON string, extracts relevant fields, and sends a message to Slack.

#     This function:
#     - Parses an LLM response using JsonOutputParser
#     - Extracts `reason`, `new_topic_name`, and `status`
#     - Sends a formatted message to Slack
#     - Retrieves human responses from the Slack thread

#     Parameters:
#     llm_response_content (str): The JSON response from the LLM in string format.

#     Returns:
#     human_response (Any): Replies from users in the Slack thread.
#     """

#     # print("**************  Received Content below ********")
#     # print(llm_response_content)
#     # print("***************************************************")
    
#     # # Convert LLM response string into an AIMessage object
#     # message = AIMessage(content=llm_response_content)

#     # # Parse JSON using JsonOutputParser
#     # output_parser = JsonOutputParser()
#     # try:
#     #     json_data = output_parser.invoke(message)  # Properly parses the response
#     # except Exception as e:
#     #     print(f"Error parsing JSON: {e}")
#     #     return None  # Handle the parsing error gracefully

#     # # Extract relevant fields
#     # reason = json_data.get("reason", "")
#     # new_topic_name = json_data.get("new_topic_name", "")
#     # status = json_data.get("status", "")

#     # print(f"Reason: {reason}, New Topic Name: {new_topic_name}, Status: {status}")

#     # Construct Slack message
#     # sending_msg = f"Hey, here is an update from the Agent:\n- **Reason:** {reason}\n- **New Topic Name:** {new_topic_name}\n- **Status:** {status}"
#     sending_msg = f"Hey , this is msg from your agent , give me newly created Notion PageId for the topic {meeting_topic}"
#     # Define Slack channel ID
#     channel_id = "C08BRF3MZT7"

#     # Send message to Slack channel and get thread timestamp
#     thread_ts = post_message_to_channel.invoke(
#         input={"sending_msg_info": {"channel_id": channel_id, "message": sending_msg}}
#     )

#     # Fetch human responses from the Slack thread
#     human_response = fetch_replies_from_channel.invoke(
#         input={"getting_human_response_info": {"CHANNEL_ID": channel_id, "thread_ts": thread_ts}}
#     )

#     return human_response

# human_response = handle_sending_msg("Axial Project Pipeline")
# print(human_response)


async def handle_sending_msg(meeting_topic):
    """
    Sends a message to a Slack channel and listens for a human response in the thread.

    Args:
        meeting_topic (str): The topic of the meeting for which a Notion PageId is requested.

    Returns:
        str: The first human response from the Slack thread, or None if no response is received.
    """
    sending_msg = f"Hey, this is a message from your agent. Give me the newly created Notion PageId for the topic {meeting_topic}."

    # Define Slack channel ID
    channel_id = "C08BRF3MZT7"

    # Send message to Slack channel and get thread timestamp
    thread_ts = await post_message_to_channel({"channel_id": channel_id, "message": sending_msg})

    if not thread_ts:
        print("❌ Failed to send message or retrieve thread timestamp.")
        return None

    print(f"📩 Message sent! Listening for replies in thread {thread_ts}...")

    # Fetch human responses from the Slack thread
    human_response = await fetch_replies_from_channel({"CHANNEL_ID": channel_id, "thread_ts": thread_ts})

    return human_response


###############################################################################################

def get_users_in_channel(channel_id):
    """
    Retrieves the list of user IDs in a given Slack channel.

    Args:
        channel_id (str): The ID of the Slack channel.

    Returns:
        list: A list of user IDs in the channel.
    """
    url = "https://slack.com/api/conversations.members"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    params = {"channel": channel_id}

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    print(data)

    if data.get("ok"):
        return data.get("members", [])  # Returns a list of user IDs
    else:
        print("Error fetching users:", data.get("error"))
        return []
    

def get_user_info(user_id):
    """
    Fetches detailed information for a given user.

    Args:
        user_id (str): The Slack user ID.

    Returns:
        dict: User details including name, real name, and email.
    """
    url = "https://slack.com/api/users.info"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    params = {"user": user_id}

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    if data.get("ok"):
        user = data.get("user", {})
        return {
            "id": user.get("id"),
            "name": user.get("name"),
            "real_name": user.get("real_name"),
            "email": user.get("profile", {}).get("email")  # Might require extra permissions
        }
    else:
        print(f"Error fetching user {user_id}: {data.get('error')}")
        return {}


async def main():
    meeting_topic = "AI and Blockchain"
    response = await handle_sending_msg(meeting_topic)
    print(response)

# asyncio.run(main())
# CHANNEL_ID = "C08BRF3MZT7"


# users_list = get_users_in_channel("C08BRF3MZT7")
# print(users_list)

# user_info_details = get_user_info(users_list[1])
# print(user_info_details)