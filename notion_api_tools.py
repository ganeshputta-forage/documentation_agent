from notion_client import Client
import requests
import json
from langchain.tools import tool
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser

from pydantic import BaseModel
import logging
import sys
import re
from datetime import datetime
import os
from dotenv import load_dotenv


logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more details
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to console
        logging.FileHandler("notion_agent.log")  # Save logs to a file
    ]
)
load_dotenv()
# NOTION_API_KEY = "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"
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
# print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
# print(NOTION_API_KEY)
# print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
# Initialize the Notion client
notion = Client(auth=NOTION_API_KEY)

async def validate_notion_page(notion_page_id):
    """
    Checks if the given Notion Page ID is valid and accessible.
    Returns True if valid, else False.
    """
    url = f"https://api.notion.com/v1/pages/{notion_page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28"
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return True  # ✅ Notion Page is valid
    else:
        print(f"❌ Invalid Notion Page ID: {notion_page_id}. Error: {response.json()}")
        return False  # ❌ Invalid Page ID





# Helper Function to get Notion Content because it is recursive
def fetch_content_by_given_block_page_id_helper_func(parent_page_id, number_stack=None, level=0):
    if number_stack is None:
        number_stack = []

    url_to_get_all_content = f"https://api.notion.com/v1/blocks/{parent_page_id}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    try:
        response = requests.get(url_to_get_all_content, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        return [f"{'.'.join(map(str, number_stack))} Data not fetched for ObjectId {parent_page_id}"]

    page_content_json_data = response.json()
    results_list = page_content_json_data.get("results", [])

    over_all_data = []

    for index, each_result in enumerate(results_list, start=1):
        object_type = each_result.get("type")
        has_children = each_result.get("has_children", False)
        object_data = each_result.get(object_type, {})
        rich_text_list = object_data.get("rich_text", [])

        text_data = "".join([text_item["text"]["content"] for text_item in rich_text_list if "text" in text_item])

        # Update the numbering stack for this level
        if len(number_stack) > level:
            number_stack[level] = index  # Update existing level number
        else:
            number_stack.append(index)  # Append new level number
        
        hierarchy_number = ".".join(map(str, number_stack[:level + 1]))

        if text_data:
            over_all_data.append(f"{hierarchy_number} - {text_data} {{id: {each_result['id']}}}")

        # Recursively fetch children with updated numbering
        if has_children:
            child_content = fetch_content_by_given_block_page_id_helper_func(each_result["id"], number_stack[:], level + 1)
            over_all_data.extend(child_content)

    return over_all_data


@tool   # It requires Notion PageId
def fetch_notion_page_content(notion_page_id_info: dict):
    """
    Fetches content from a Notion page using the provided dictionary containing the Notion Page ID.

    This function extracts block content from a Notion page by retrieving the "notion_page_id" 
    from the input dictionary. It utilizes a helper function for recursive fetching to handle 
    hierarchical content efficiently. The extracted content is then formatted into a single 
    string, with each point separated by a newline.

    Args:
        notion_page_id_info (dict): A dictionary which contains below keys
            - notion_page_id(str) : The unique identifier which represents a Notion Page Id

    Returns:
        str: A single string containing the extracted content from the Notion page, 
             with each point separated by a newline.
    """
    NOTION_PAGE_ID = notion_page_id_info.get("notion_page_id")
    all_content_list = fetch_content_by_given_block_page_id_helper_func(NOTION_PAGE_ID)
    over_all_content_list_from_notion_page = "\n".join(all_content_list)
    return over_all_content_list_from_notion_page




# Helper Fucntion to just retrieve type of block from given blockId
def retrieve_notion_block_type(blockId):
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    url_to_get_object = f"https://api.notion.com/v1/blocks/{blockId}"
    try:
        print("⌛⌛ Getting Object , Please wait ⌛⌛")
        obj_response = requests.get(url_to_get_object , headers=headers)
        print("🟢🟢🟢 Object Arrived , Got Response 🟢🟢🟢")
        response_data_json = obj_response.json()
        object_type = response_data_json.get("type" , "")
        print(f"🟢🟢🟢  Found Return Type of Object , Object Type is {object_type}, Returning the Type now 🟢🟢🟢")
    except Exception as e:
        print(f"Exception Occured {e}")
    return object_type


@tool    # Just need ParentId under which points to be added 
def append_bulleted_list_to_block(adding_content_info: dict):
    """
    Adds bullet point content as child blocks to a given Notion block using its object ID.

    This function takes a Notion block's `objectId` and appends bullet points as 
    children to it using the Notion API. It prepares the request payload, sends a 
    PATCH request to update the block, and handles response validation.

    Parameters:
        adding_content_info (dict) : It consist  of below Keys
        - blockId (str): The unique identifier of the Notion block to which content will be added.
        - bullet_points_list (list[str]): A list of bullet points (strings) to be added as child blocks.

    Process:
    1. Determines the object type of the given `blockId` (though not actively used in the request).
    2. Constructs a payload with bullet points as `bulleted_list_item` blocks.
    3. Sends a PATCH request to the Notion API to add the content.
    4. Validates the response and prints success or failure messages.

    Notes:
    - The function defaults to adding `bulleted_list_item` blocks.
    - It currently does not support different types like numbered lists or paragraphs.
    - Error handling ensures the function logs failure details if the API request fails.

    Returns:
        None: The function prints logs indicating success or failure.
 
    """
    blockId = adding_content_info.get('blockId')
    bullet_points_list = adding_content_info.get('bullet_points_list')

    block_type = retrieve_notion_block_type(blockId)

    # logging.info("Preparing Payload to add content to ObjectId: %s", objectId)
    print(f"Preparing Payload to add content to ObjectId: {blockId}")

    # Prepare request payload
    data = {
        "children": [
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {"type": "text", "text": {"content": each_bullet_point}}
                    ]
                } 
            } for each_bullet_point in bullet_points_list
        ]
    }
    # logging.info("Payload Prepared: %s", data)
    print(f"Payload Prepared: {data}")

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    url_to_add_text = f"https://api.notion.com/v1/blocks/{blockId}/children"

    # logging.info("Sending request to add content to Notion...")
    print("Sending request to add content to Notion...")

    try:
        response = requests.patch(url_to_add_text, headers=headers, json=data)
        if response.status_code == 200:
            # logging.info("✅ Data successfully added to %s with object-type %s", blockId, block_type)
            print(f"✅ Data successfully added to {blockId} with object-type {block_type}")
        else:
            print(f"❌ Failed to add data. Status Code: {response.status_code}, Response: {response.text}")
            # logging.error("❌ Failed to add data. Status Code: %d, Response: %s", response.status_code, response.text)
    except Exception as e:
        # logging.exception("🚨 Error occurred while adding content to %s: %s", blockId, str(e))
        print(f"🚨 Error occurred while adding content to {blockId}: {str(e)}")

# append_bulleted_list_to_block.invoke(input = {"adding_content_info" : {"blockId": block_id, "list_of_bullet_points": [content]}})


# Helper Function for adding Toggle Item(Change Log) to given Notion_Page_ID
def append_Toggle_to_Notion_page_By_using_first_child_id(NOTION_PAGE_ID, toggle_item_text, existing_first_child_id):
    """
    Tool Name: add_change_log_toggle_item
    
    Description:
    This function adds a new toggle item to a given Notion page using a PATCH request. The new toggle item will be placed 
    as the first child after an existing child block. If the request is successful, it returns the Object ID of the newly added toggle item.

    Parameters:
    - NOTION_PAGE_ID (str): The ID of the Notion page where the toggle item should be added.
    - toggle_item_text (str): The text content for the toggle item.
    - existing_first_child_id (str): The ID of an existing child block to insert the toggle item after.

    Returns:
    - str: The Object ID of the newly added toggle item if successful, otherwise an empty string.
    
    Example Usage:
    ```python
    toggle_id = add_Change_Log_Toggle_Item_to_Notion_page_By_Id("notion_page_id", "New Change Log Entry", "existing_child_id")
    ```

    Notes:
    - Requires a valid Notion API Key (`NOTION_API_KEY` must be set as an environment variable or global variable).
    - Uses Notion API version "2022-06-28".
    - The function performs a PATCH request to modify the block's children.
    """

    url_to_add_toggle_Item_as_children = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload_to_add_Toggle_Element = {
        "children": [
            {
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": toggle_item_text},
                        }
                    ],
                }
            }
        ],
        "after": existing_first_child_id
    }

    # logging.info("⌚ Requesting to add a new Toggle Item ⌚")
    print("⌚ Requesting to add a new Toggle Item ⌚")
    
    try:
        # logging.info(f"⌚ Requesting to add Toggle Item after ObjectId: {existing_first_child_id} ⌚")
        print(f"⌚ Requesting to add Toggle Item after ObjectId: {existing_first_child_id} ⌚")
        response = requests.patch(url_to_add_toggle_Item_as_children, headers=headers, json=payload_to_add_Toggle_Element)
        response_json_data = response.json()

        if response.status_code == 200:
            toggle_block_id = response_json_data["results"][0]["id"]
            # logging.info(f"🟢 Toggle Item added successfully! Toggle ID: {toggle_block_id}")
            print(f"🟢 Toggle Item added successfully! Toggle ID: {toggle_block_id}")
            return toggle_block_id
        else:
            # logging.error(f"🔴 Failed to add toggle item. Status Code: {response.status_code}")
            print(f"🔴 Failed to add toggle item. Status Code: {response.status_code}")
            # logging.error(f"Response: {response.text}")
            print(f"Response: {response.text}")
            return ""

    except Exception as e:
        # logging.exception("🔴 Exception occurred while adding a toggle item")
        print("🔴 Exception occurred while adding a toggle item")
        return ""
    
@tool   # For adding a new Toggle Item with Bullet-points in list  used for adding Change Log
def append_toggle_with_bullets_for_change_log(adding_toggle_item_info: dict):
    """
    Tool Name: add_toggle_item_with_bullets
    
    Description:
    This function adds a new toggle item at the beginning of a given Notion page along with bullet points inside it. 
    The process involves:
    1. Fetching the first child block of the given Notion page using a GET request.
    2. Using the first block's ID to insert a new toggle item before it (ensuring the toggle item is placed at the top).
    3. Adding bullet points inside the newly created toggle item.

    Parameters:
    - NOTION_PAGE_ID (str): The ID of the Notion page where the toggle item should be added.
    - toggle_item_text (str): The text content for the toggle item.
    - bullet_points_list (list of str): A list of bullet point texts to be added inside the toggle item.

    Returns:
    - None: This function does not return anything explicitly but prints the status updates.

    Steps:
    1. Makes a GET request to retrieve the first child block of the Notion page.
    2. If an existing block is found, its ID is used to insert a new toggle item before it.
    3. Calls the `add_Change_Log_Toggle_Item_to_Notion_page_By_Id()` function to add the toggle item.
    4. If the toggle item is successfully added, it then calls `add_content_to_given_id()` to insert bullet points inside it.

    Example Usage:
    ```python
    add_Toggle_Item_with_Bullet_Points(
        "notion_page_id", 
        "New Toggle Heading", 
        ["Bullet Point 1", "Bullet Point 2", "Bullet Point 3"]
    )
    ```

    Notes:
    - Requires `NOTION_API_KEY` to be set as an environment/global variable for API authentication.
    - Uses Notion API version "2022-06-28".
    - The function ensures that the toggle item is always inserted at the first position on the Notion page.
    - If no existing children are found, the function will fail to add the toggle item.
    """
    print("TOGGLE INFO")
    print(adding_toggle_item_info)
    print("&&&&&&&&&*******************&&&&&&&&&&&")
    NOTION_PAGE_ID = adding_toggle_item_info.get("NOTION_PAGE_ID")
    toggle_item_text = adding_toggle_item_info.get("toggle_item_text") 
    bullet_points_list = adding_toggle_item_info.get("bullet_points_list")

    # logging.info("🧑‍🏭 Initiating toggle item addition. Fetching first child object ID from the given Notion page ID.")
    print("🧑‍🏭 Initiating toggle item addition. Fetching first child object ID from the given Notion page ID.")

    url_to_fetch_first_children = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children?page_size=1"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # logging.info("⌛ Requesting to get the first child data...")
    print("⌛ Requesting to get the first child data...")
    response = requests.get(url_to_fetch_first_children, headers=headers)
    # logging.info("🟩 Response received.")
    print("🟩 Response received.")
    first_block_id = None
    
    if response.status_code == 200:
        children = response.json().get("results", [])
        if children:
            first_block_id = children[0]["id"]  # Get the first block ID
            # logging.info(f"🟢 Found first child block ID: {first_block_id}")
            print(f"🟢 Found first child block ID: {first_block_id}")
        else:
            print("⚠️ No existing children found on the page.")
            # logging.warning("⚠️ No existing children found on the page.")
    else:
        # logging.error(f"❌ Failed to fetch child elements. Status Code: {response.status_code}")
        print(f"❌ Failed to fetch child elements. Status Code: {response.status_code}")
        return
    
    if first_block_id:
        # logging.info(f"🔄 Creating a new toggle item before block ID: {first_block_id}")
        print(f"🔄 Creating a new toggle item before block ID: {first_block_id}")
        new_toggle_item_id = append_Toggle_to_Notion_page_By_using_first_child_id(NOTION_PAGE_ID, toggle_item_text, first_block_id)
        # logging.info(f"🆕 New toggle item created with ID: {new_toggle_item_id}")
        print(f"🆕 New toggle item created with ID: {new_toggle_item_id}")
    else:
        # logging.error("❌ Could not retrieve an existing child element ID.")
        print("❌ Could not retrieve an existing child element ID.")
        return

    if new_toggle_item_id:
        # logging.info("🧑‍🏭 Adding bullet points to the newly created toggle item...")
        print("🧑‍🏭 Adding bullet points to the newly created toggle item...")
        append_bulleted_list_to_block.invoke(input={'adding_content_info': {'blockId': new_toggle_item_id, 'bullet_points_list': bullet_points_list}})
        # logging.info("✅ Bullet points added successfully.")
        print("✅ Bullet points added successfully.")
    else:
        # logging.error("❌ No new toggle item created. Cannot add bullet points.")
        print("❌ No new toggle item created. Cannot add bullet points.")

# append_toggle_with_bullets_for_change_log.invoke(input = {"addingToggleItemInfo" : {
#                 "NOTION_PAGE_ID": page_id,
#                 "toggle_item_text": f"Change Log {today_date}",
#                 "bullet_points_list": change_logs
#             }})



@tool     # Just needs ObjectId to update
def update_block_content(updating_block_info: dict):
    """
    This function updates the content of a Notion block specified by its `objectId`.
    It sends a PATCH request to the Notion API to modify the block's text content.

    Parameters:
    - updating_info (dict): A dictionary containing the following keys:
        - blockId (str): The unique ID of the Notion block to be updated.
        - new_text_content (str): The new text content that will replace the existing content.

    If successful, a confirmation message is printed. Otherwise, an error message is shown.

    Example usage:
    update_block_content.invoke({
        "blockId": "block_object_id",
        "new_text_content": "Updated content for the block"
    })
    """
    objectId = updating_block_info.get("blockId")
    new_text_content = updating_block_info.get("new_text_content")
    print(f"objectId is {objectId}")
    print(f"new_text_content is {new_text_content}")
    obj_type = retrieve_notion_block_type(objectId)
    
    # logging.info(f"Retrieving Notion block type for object ID: {objectId}")
    print(f"Retrieving Notion block type for object ID: {objectId}")
    
    url_to_update_block = f"https://api.notion.com/v1/blocks/{objectId}"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # logging.info("Preparing payload to update block content.")
    print("Preparing payload to update block content.")
    data = {
        obj_type: {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": new_text_content}
                }
            ]
        }
    }
    
    # logging.info("Sending request to update Notion block content...")
    print("Sending request to update Notion block content...")
    try:
        response = requests.patch(url_to_update_block, headers=headers, json=data)
        
        if response.status_code == 200:
            # logging.info(f"Content successfully updated in block {objectId}.")
            print(f"Content successfully updated in block {objectId}.")
        else:
            # logging.error(f"Failed to update content. Status code: {response.status_code}")
            print(f"Failed to update content. Status code: {response.status_code}")
            # logging.error(f"Response: {response.text}")
            print(f"Response: {response.text}")
    except Exception as e:
        # logging.exception(f"Error occurred while updating content in block {objectId}.")
        print(f"Error occurred while updating content in block {objectId}.")

# @tool
# def addNum(inputDict : dict):
#     """
#     Parameters:
#     - inputDict (dict): A dictionary containing the following keys:
#         - a (int)
#         - b (int)
#     """
#     a = inputDict.get("a")
#     b = inputDict.get("b")
#     print(a+b)

# update_block_content.invoke(input = { "updating_block_info"  :  {"blockId": block_id, "new_text_content": content}})

# delete_block.invoke(input = {"blockId": block_id})

@tool   # Just needs blockId to delete a block
def delete_block(deleting_block_info: dict):
    """
    Tool Name: delete_block

    Description:
    This function deletes (archives) a specific block in a Notion page using a dictionary 
    containing the Block ID as the key "block_id". It sends a PATCH request to mark the block 
    as archived, effectively hiding it from the Notion page.

    Parameters:
    - deleting_block_info (dict): A dictionary containing the Notion Block ID with the key "block_id".

    API Endpoint:
    - PATCH https://api.notion.com/v1/blocks/{block_id}

    Headers:
    - Authorization: Bearer token for authentication (requires NOTION_API_KEY).
    - Content-Type: application/json.
    - Notion-Version: "2022-06-28" (specifies the API version).

    Process:
    1. Extracts the `block_id` from the input dictionary.
    2. Constructs the API URL using the provided `block_id`.
    3. Sends a PATCH request to the Notion API to set the block’s `archived` status to True.
    4. Handles responses to confirm whether the deletion was successful or not.

    Returns:
    - bool: Returns True if the block was successfully deleted, otherwise False.

    Example Usage:
    ```python
    was_deleted = delete_block({"block_id": "block_id_12345"})
    if was_deleted:
        print("Block was successfully deleted!")
    else:
        print("Failed to delete the block.")
    ```

    Notes:
    - This method archives the block instead of permanently deleting it. Archived blocks can be restored.
    - Ensure the `NOTION_API_KEY` has the necessary permissions to modify the block.
    """
    block_id = deleting_block_info.get("blockId")
    url_to_delete_block = f"https://api.notion.com/v1/blocks/{block_id}"

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload = {"archived": True}

    try:
        print("⌛ Request to delete Block is initiated")
        response = requests.patch(url_to_delete_block, headers=headers, json=payload)
        response_json = response.json()

        if response.status_code == 200:
            print(f"✅ Block {block_id} deleted successfully!")
            return True
        else:
            print(f"❌ Failed to delete block {block_id}. API Response: {response_json}")
            return False

    except Exception as e:
        print("❌ Exception occurred while deleting the block")
        return False
    
# delete_block.invoke(input = {"deleting_block_info" : {"blockId": block_id}}) 

#####################################################################################################
# Fetching Existing Notion Pages Info
def fetch_data_from_notion_pages_data_database_table():      #  notion_page_id -  page_project_title
    notion_pages_info_database_id = "1a3e35223beb806e80acdc2563180fb1"
    # database_id = "1ade35223beb807c92b0e662f4ff95f7"
    HEADERS = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    url = f"https://api.notion.com/v1/databases/{notion_pages_info_database_id}/query"
    notion_pages_info_list = []
    # rows_info_dict = dict()

    
    response = requests.post(url, headers=HEADERS)
    data = response.json()
    if "results" not in data:
        raise Exception(f"Error fetching Notion database: {data}")
    for page in data["results"]:
        properties = page["properties"]
        
        notion_page_id = properties["notion_page_id"]["title"][0]["text"]["content"] if properties["notion_page_id"]["title"] else ""
        page_project_title = properties["page_project_title"]["rich_text"][0]["text"]["content"] if properties["page_project_title"]["rich_text"] else ""
        # rows_info_dict[notion_page_id] = action_item_database_id
        notion_pages_info_list.append({
            "notion_page_id": notion_page_id,
            "page_project_title": page_project_title
        })
    # Handle pagination
    url = data.get("next_cursor")
    return notion_pages_info_list

###############################################################################################################



###############################################################################################################

# adding action item for given list of assignees
def add_page_to_action_items_database_table_by_id(database_id, data):
    print("Went into adding page")
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    # Extracting data
    action_item_text = data.get("action_item", "")
    status_text = data.get("status", "")  # Multi-select should be a list
    assigned_to_list = data.get("assigned_to", [])  # List of assignees

    # Formatting Status (Multi-select)
    # status_options = [{"name": status} for status in status_list]

    # Convert assigned_to_list to a JSON-formatted string
    assigned_to_text = json.dumps(assigned_to_list)  

    # Constructing the Notion API payload
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Action Item": {
                "title": [{"text": {"content": action_item_text}}]
            },
            "Status": {
                "multi_select": [
                        {"name": status_text}  # Status should be inside a list
                    ]
            },
            "Assigned To": {
                "rich_text": [{"text": {"content": assigned_to_text}}]
            }
        }
    }

    # Making the request
    response = requests.post(url, headers=headers, json=payload)

    # Handling the response
    if response.status_code == 200:
        print(" 🟢🟢action item added")
        # return response.json()
    else:
        # return {
        #     "error": response.json(),
        #     "status_code": response.status_code
        # }
        print("❌ Action item not added")

#############################################################################################################
# Getting Notion Pages Id along with its corresponding Action Items table Id
def get_each_notion_page_action_items_table_id_mapping():
    database_id = "1ade35223beb807c92b0e662f4ff95f7"
    HEADERS = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    # rows = []
    rows_info_dict = dict()

    while url:
        response = requests.post(url, headers=HEADERS)
        data = response.json()

        if "results" not in data:
            raise Exception(f"Error fetching Notion database: {data}")

        for page in data["results"]:
            properties = page["properties"]
            
            notion_page_id = properties["notion_page_id"]["title"][0]["text"]["content"] if properties["notion_page_id"]["title"] else ""
            action_item_database_id = properties["action_item_database_id"]["rich_text"][0]["text"]["content"] if properties["action_item_database_id"]["rich_text"] else ""
            rows_info_dict[notion_page_id] = action_item_database_id
            # rows.append({
            #     "notion_page_id": notion_page_id,
            #     "action_item_database_id": action_item_database_id
            # })

        # Handle pagination
        url = data.get("next_cursor")
    return rows_info_dict

##########################################################################################################################

def add_each_notion_page_action_items_table_id_mapping(notion_page_id , action_items_table_id):
    database_id = "1ade35223beb807c92b0e662f4ff95f7"
    HEADERS = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    url = "https://api.notion.com/v1/pages"
    
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "notion_page_id": {
                "title": [{"text": {"content": notion_page_id}}]
            },
            "action_item_database_id": {
                "rich_text": [{"text": {"content": action_items_table_id}}]
            }
        }
    }

    response = requests.post(url, headers=HEADERS, data=json.dumps(payload))
    
    if response.status_code == 200:
        print("🟢🟢 NotionPageId along with ActionItemsDatabaseId Page added successfully!")
        return response.json()
    else:
        print(f"❌❌ Error: {response.status_code}, {response.text}")
        return None
###########################################################################################################
###########################################################################################################

"""
@tool  # Adding action item based on users id
def add_page_to_database(data):
    
    database_id_1 = "184e35223beb8072b2f8fc8d22260d67"
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    # Clean JSON input
    # data = data.replace("json", "").replace("```", "").strip()
    # message = AIMessage(content=f'```\n{data}\n```')

    # Parse the response
    # output_parser = JsonOutputParser()
    # data = output_parser.invoke(message)
    # list_of_users_url = "https://api.notion.com/v1/users"

    # users_response = requests.get(list_of_users_url , headers=headers)
    # response_json = users_response.json()
    # results = response_json.get("results")
    # user_ids_list = []
    # for each_user in results:
    #     if each_user.get("type") == "person":
    #         user_ids_list.append(each_user.get("id"))
    # # print(json.dumps(results , indent=4))
    # print(user_ids_list)
    #   ['a7fe2364-3f0c-453f-9cc5-1273a54024f7']  user_ids list
    try:
        action_data = data.get("action_data", "")
        status = data.get("status", "")
        assignee_email = data.get("assigned_to", "")

        database_id_1 = "196e35223beb81228d00c817b034f906"

        # Notion API Payload
        payload = {
            "parent": {"database_id": database_id_1},
            "properties": {
                "Action Item": {
                    "title": [{"text": {"content": action_data}}]
                },
                "Status": {
                    "multi_select": [
                        {"name": status}  # Status should be inside a list
                    ]
                },
                "Assigned To": {
                    "people": [
                        {"object": "user", "id": "a7fe2364-3f0c-453f-9cc5-1273a54024f7"}
                    ]
                }
            }
        }

        print("Payload to be sent to Notion API:", json.dumps(payload, indent=4))

        # Make the POST request to Notion API
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            print("✅ Page added successfully!")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")

    except json.JSONDecodeError as e:
        print(f"⚠️ JSON Parse Error: {e}")
    except Exception as e:
        print(f"⚠️ Exception occurred: {e}")
"""

def fetch_data_from_meetings_history_database_table(DATABASE_ID):
    DATABASE_ID = "197e35223beb80039714f0cd468bce2e"
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

# Headers for authentication
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"  # Use the latest Notion API version
    }
    response = requests.post(url, headers=headers)
    # print(json.dumps(response.json() , indent=4))
    if response.status_code == 200:
        data = response.json()

        # Extract relevant data from each row
        all_pages = []
        for page in data.get("results", []):
            properties = page.get("properties", {})

            meeting_name = properties.get("meeting_name", {}).get("title", [])
            meeting_name_text = meeting_name[0].get("text", {}).get("content", "") if meeting_name else "Unnamed"

            # happened_date = properties.get("happened_date", {}).get("date", {}).get("start", "No Date")
            happened_date = properties.get("happened_date", {}).get("rich_text", [])
            happened_date_text = happened_date[0].get("text", {}).get("content", "No Date") if happened_date else "No Date"

            all_pages.append({
                "meeting_name": meeting_name_text,
                "happened_date": happened_date_text
            })

        # Print extracted rows
        # print(json.dumps(all_pages, indent=4))

    else:
        # print(f"Error: {response.status_code}, {response.text}")
        return [{"error" : f"Error: {response.status_code}, {response.text}"}]
    return all_pages


def add_page_to_meetings_history_database_table(adding_page_info):
    DATABASE_ID = "197e35223beb80039714f0cd468bce2e"
    database_id_1 = DATABASE_ID
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    meeting_name = adding_page_info.get("meeting_name")
    happened_date = adding_page_info.get("happened_date")
    # meeting_date = adding_page_info.get("meeting_date")
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "meeting_name": {
                "title": [{"text": {"content": meeting_name}}]
            },
            "happened_date": {
                "rich_text": [{"text": {"content": happened_date}}]
            }
        }
    }
    
    print("Payload to be sent to Notion API:", json.dumps(payload, indent=4))

    # Make the POST request to Notion API
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("✅ Page added successfully!")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

#########################################################################################

#######################################################################################
# Related to Existing Notion Pages Data
# getting existing notion_pages list data
def fetch_data_from_existing_notion_pages_data_database_table(DATABASE_ID=""):

    DATABASE_ID = "1a3e35223beb806e80acdc2563180fb1"
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

# Headers for authentication
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"  # Use the latest Notion API version
    }
    response = requests.post(url, headers=headers)
    # print(json.dumps(response.json() , indent=4))
    if response.status_code == 200:
        data = response.json()

        # Extract relevant data from each row
        all_pages = []
        for page in data.get("results", []):
            properties = page.get("properties", {})

            meeting_name = properties.get("notion_page_id", {}).get("title", [])
            meeting_name_text = meeting_name[0].get("text", {}).get("content", "") if meeting_name else "Unnamed"

            # happened_date = properties.get("happened_date", {}).get("date", {}).get("start", "No Date")
            # happened_date = properties.get("page_project_title", {}).get("rich_text", [])
            # happened_date_text = happened_date[0].get("text", {}).get("content", "No Project Title") if happened_date else "No Date"

            page_project_title = properties.get("page_project_title", {}).get("rich_text", [])
            page_project_title_text = page_project_title[0].get("text", {}).get("content", "No Project Title") if page_project_title else "No Date"

            all_pages.append({
                "notion_page_id": meeting_name_text,
                "page_project_title": page_project_title_text
            })

        # Print extracted rows
        # print(json.dumps(all_pages, indent=4))

    else:
        # print(f"Error: {response.status_code}, {response.text}")
        return [{"error" : f"Error: {response.status_code}, {response.text}"}]
    return all_pages

# adding should also be included
def add_new_notion_page_data_to_existing_notion_pages_database(notion_page_id , page_project_title):
    DATABASE_ID = "1a3e35223beb806e80acdc2563180fb1"
    url = "https://api.notion.com/v1/pages"
    
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "notion_page_id": {  # Ensure this matches the exact column name in your Notion database
                "title": [{"type": "text", "text": {"content": notion_page_id}}]
            },
            "page_project_title": {  # Ensure this matches the exact column name in your Notion database
                "rich_text": [{"type": "text", "text": {"content": page_project_title}}]
            }
        }
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        print("✅ Successfully added a new row to Notion database!")
        print("New Page ID:", response.json().get("id"))
    else:
        print(f"❌ Error adding row: {response.status_code}, {response.text}")




##########################################################################################################
##########################################################################################################
def fetch_data_from_latest_projects_data_database_table(DATABASE_ID):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    # Headers for authentication
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"  # Use the latest Notion API version
    }
    
    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        data = response.json()

        # Extract relevant data from each row
        all_pages = []
        for page in data.get("results", []):
            properties = page.get("properties", {})

            # Extract page ID (title property)
            meeting_name = properties.get("notion_page_id", {}).get("title", [])
            meeting_name_text = meeting_name[0].get("text", {}).get("content", "") if meeting_name else "Unnamed"

            # Extract project title (rich_text)
            happened_date = properties.get("page_project_title", {}).get("rich_text", [])
            happened_date_text = happened_date[0].get("text", {}).get("content", "No Date") if happened_date else "No Date"

            # Extract latest_data (list of rich_text values)
            latest_data = properties.get("latest_data", {}).get("rich_text", [])
            latest_data_text = [item.get("text", {}).get("content", "") for item in latest_data]

            all_pages.append({
                "notion_page_id": meeting_name_text,
                "page_project_title": happened_date_text,
                "latest_data": json.loads(latest_data_text[0])
            })

    else:
        return [{"error": f"Error: {response.status_code}, {response.text}"}]

    return all_pages

#############################################################################################################
#
def get_latest_projects_row_data(row_id):
    """
    Retrieves a specific row from the "Latest Projects Data" Notion database based on the given row ID.

    This function queries the Notion database using its API and filters the data to match the provided 
    `row_id`, which corresponds to the `notion_page_id` field in the database.

    Args:
        row_id (str): The unique identifier of the Notion page (notion_page_id) to fetch.

    Returns:
        dict or None: A dictionary containing the following keys if a matching row is found:
            - "notion_page_id" (str): The unique identifier of the Notion page.
            - "page_project_title" (str): The title of the associated project.
            - "latest_data" (dict): A JSON-parsed dictionary containing additional project data.
        
        If no matching row is found, the function returns `None`.

    Raises:
        Exception: If the API request fails, an error message is printed and `None` is returned.

    Note:
        - The function requires a valid Notion API key stored in `NOTION_API_KEY`.
        - The Notion API version used is "2022-06-28".
        - The `notion_page_id`, `page_project_title`, and `latest_data` fields should match 
          the column names in the Notion database.
        - The `latest_data` field is expected to contain JSON-encoded text, which is parsed into a dictionary.
    """

    database_id = "1a5e35223beb80d49b99efdbdf21e4be"
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # Query to filter by notion_page_id
    query = {
        "filter": {
            "property": "notion_page_id",
            "title": {
                "equals": row_id  # Assuming notion_page_id is a "title" column
            }
        }
    }

    response = requests.post(url, headers=headers, json=query)

    if response.status_code == 200:
        data = response.json()
        if len(data["results"]) > 0:
            row = data["results"][0]["properties"]
            
            # Extract specific fields
            notion_page_id = row["notion_page_id"]["title"][0]["text"]["content"] if row["notion_page_id"]["title"] else None
            page_project_title = row["page_project_title"]["rich_text"][0]["text"]["content"] if row["page_project_title"]["rich_text"] else None
            latest_data = [item["text"]["content"] for item in row["latest_data"]["rich_text"]] if row["latest_data"]["rich_text"] else None
            
            return {
                "notion_page_id": notion_page_id,
                "page_project_title": page_project_title,
                "latest_data": json.loads(latest_data[0])
            }
        else:
            print("❌ No matching row found in the database.")
            return None
    else:
        print(f"❌ Error fetching row: {response.status_code}, {response.text}")
        return None
    
##########################################################################################################
#
def add_latest_project_details_row_data(latest_project_row_data_details):
    latest_notion_page_id = latest_project_row_data_details.get("notion_page_id")
    page_project_title = latest_project_row_data_details.get("page_project_title")
    latest_project_data = latest_project_row_data_details.get("latest_data")
    print("In the function of adding latest_project_details_row_data for new_meeting_topic 🧑‍🏭❌❌❌❌🧑‍🏭🧑‍🏭🟢🟢👍🟩✔️🟢🧑‍🏭🔴❌👁️⌛⏰👍🥲🟩✔️🟢🧑‍🏭🔴❌👁️⌛😂🥲😂✔️🟩🟢🧑‍🏭")
    
    database_id = "1a5e35223beb80d49b99efdbdf21e4be"
    url = f"https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # Convert list of strings to a string representation of a list
    latest_project_data_str = json.dumps(latest_project_data)
    
    # Payload to insert data into the Notion database
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "notion_page_id": {"title": [{"text": {"content": latest_notion_page_id}}]},
            "page_project_title": {"rich_text": [{"text": {"content": page_project_title}}]},
            "latest_data": {"rich_text": [{"text": {"content": latest_project_data_str}}]}
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        print("✅ Row successfully added to Notion database.")
        return response.json()
    else:
        print(f"❌ Error adding row: {response.status_code}, {response.text}")
        return None
    

def update_latest_project_details_row_data(latest_project_row_data_details):
    notion_page_id = latest_project_row_data_details.get("notion_page_id")
    latest_project_data = latest_project_row_data_details.get("latest_data")
    database_id = "1a5e35223beb80d49b99efdbdf21e4be"
    
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # Step 1: Query the database to find the page with the matching notion_page_id
    query_payload = {
        "filter": {
            "property": "notion_page_id",
            "rich_text": {"equals": notion_page_id}
        }
    }
    
    response = requests.post(url, headers=headers, json=query_payload)
    data = response.json()
    
    if "results" not in data or len(data["results"]) == 0:
        print("No matching page found in the database.")
        return
    
    # Extract the page ID of the matching row
    page_id = data["results"][0]["id"]
    
    # Step 2: Update the "latest_data" property in the matched row
    update_url = f"https://api.notion.com/v1/pages/{page_id}"
    latest_project_data_str = json.dumps(latest_project_data)
    
    update_payload = {
        "properties": {
            "latest_data": {
                "rich_text": [{"text": {"content": latest_project_data_str}}]
            }
        }
    }
    
    update_response = requests.patch(update_url, headers=headers, json=update_payload)
    
    if update_response.status_code == 200:
        print("Successfully updated the Notion row.")
    else:
        print("Failed to update the Notion row.", update_response.text)




###################################################################################

# latest_project_row_data_details = {
#     "notion_page_id" : 
# }
# update_latest_project_details_row_data()

# latest_project_details_data = {
#     "notion_page_id" : "newly_created_notion_page_id",
#     "page_project_title" : "new_project_name",
#     "latest_data" : ["point1" , "point2" , "point3"]
# }
# add_latest_project_details_row_data(latest_project_details_data)
    
def get_actual_page_id(database_id, modified_row_id):
    """Fetch the actual Notion page_id (UUID) using the modified row_id stored in notion_page_id column."""
    
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # Query Notion database to find row with given notion_page_id
    query = {
        "filter": {
            "property": "notion_page_id",  # Ensure this matches the column name in your Notion table
            "rich_text": {
                "equals": modified_row_id
            }
        }
    }

    response = requests.post(url, headers=headers, json=query)

    if response.status_code == 200:
        data = response.json()
        print(data)
        if len(data["results"]) > 0:
            actual_page_id = data["results"][0]["id"]  # The actual UUID of the page
            print(f"✅ Found Notion Page ID (UUID): {actual_page_id}")
            return actual_page_id
        else:
            print("❌ No matching row found in the database.")
            return None
    else:
        print(f"❌ Error fetching row: {response.status_code}, {response.text}")
        return None


def update_latest_data(row_id, new_data_list):
    """Update latest_data column for the given row ID, storing the list as a string."""
    url = f"https://api.notion.com/v1/pages/{row_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # Convert list to a string representation (formatted as JSON-like list)
    formatted_text = json.dumps(new_data_list, indent=2)  

    data = {
        "properties": {
            "latest_data": {  # Ensure this matches the exact column name in Notion
                "rich_text": [{"type": "text", "text": {"content": formatted_text}}]
            }
        }
    }

    response = requests.patch(url, headers=headers, json=data)

    if response.status_code == 200:
        print("✅ Successfully updated latest_data")
    else:
        print(f"❌ Error updating latest_data: {response.status_code}, {response.text}")

def process_updating_notion_page_latest_data(ROW_PRIMARY_ID , NEW_LATEST_DATA):
    DATABASE_ID = "1a5e35223beb80d49b99efdbdf21e4be"
    actual_page_id = get_actual_page_id(DATABASE_ID , ROW_PRIMARY_ID)

    if actual_page_id:
        print(f"You can now use this page_id for updates: {actual_page_id}")
    else:
        print("⚠️ Could not find the page_id.")
    update_latest_data(actual_page_id , NEW_LATEST_DATA)

# process_updating_notion_page_latest_data("196e35223beb806a8889f2524d28bdaf" , [
#   "SEMrush integration completed added successfully.",
#   "Addressed API authentication errors.",
#   "Backup automation approach using Selenium implemented."
# ])


#################################################################################################


# def get_notion_row(row_id):
#     url = f"https://api.notion.com/v1/pages/{row_id}"
#     headers = {
#         "Authorization": f"Bearer {NOTION_API_KEY}",
#         "Notion-Version": "2022-06-28"
#     }

#     response = requests.get(url, headers=headers)

#     if response.status_code == 200:
#         data = response.json()
#         print(data)
#         print("✅ Successfully retrieved row data:")
#         return data
#     else:
#         print(f"❌ Error fetching row: {response.status_code}, {response.text}")
#         return None

    
# not- need
def get_table_content(table_id):
    url_to_get_table_content = f"https://api.notion.com/v1/blocks/{table_id}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    try:
        response = requests.get(url_to_get_table_content, headers=headers)
        # with open("Results/table_data.json" , "w") as file:
        #     json.dump(json_data , file , indent = 4)
        #     print(" ✔️ ✔️ ✔️ ✔️ ✔️ ✔️ ✔️ Table data dumped ✔️ ✔️ ✔️ ✔️ ✔️ ✔️ ✔️ ")
        # response.raise_for_status()  # Raise an error for non-200 responses
    except requests.RequestException as e:
        return ["❌ Exception occurred while fetching: {e}"]
    
    table_json_data = response.json()
    results_list = table_json_data.get("results" , [])
    overall_table_data = []
    for each_result in results_list:
        object_type = each_result.get("type")
        if object_type != "table_row":
            continue
        object_data = each_result.get(object_type , [])  # data is in dict
        cells_data = object_data.get("cells")    # cell_data is a list of lists , each list represents a cell
        each_row_data = []
        for each_row_cell in cells_data:    
            cell_data_list = [
                    text_obj["text"]["content"] 
                    for text_obj in each_row_cell 
                    if "text" in text_obj and "content" in text_obj["text"]
                ]
            each_cell_text = "".join(cell_data_list)
            each_row_data.append(each_cell_text)
        formatted_each_row_data = "  |  ".join(each_row_data)
        overall_table_data.append(formatted_each_row_data)
    
    return overall_table_data
###########################################################################################################





###########################################################################################################
# Down tools for adding content in a new Given Page
def append_toggle_to_given_page(NOTION_PAGE_ID , toggle_item_text):

    url_to_add_toggle_Item_as_children = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload_to_add_Toggle_Element = {
        "children": [
            {
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": toggle_item_text}
                        }
                    ],
                    "is_toggleable": True  # Enables toggle functionality
                }
            }
        ]
    }

    print("⌚ Requesting to add a new Toggle Item ⌚")
    
    try:
        # logging.info(f"⌚ Requesting to add Toggle Item after ObjectId: {existing_first_child_id} ⌚")
        # print(f"⌚ Requesting to add Toggle Item after ObjectId: {existing_first_child_id} ⌚")
        response = requests.patch(url_to_add_toggle_Item_as_children, headers=headers, json=payload_to_add_Toggle_Element)
        response_json_data = response.json()

        if response.status_code == 200:
            toggle_block_id = response_json_data["results"][0]["id"]
            # logging.info(f"🟢 Toggle Item added successfully! Toggle ID: {toggle_block_id}")
            print(f"🟢 Toggle Item added successfully! Toggle ID: {toggle_block_id}")
            return toggle_block_id
        else:
            # logging.error(f"🔴 Failed to add toggle item. Status Code: {response.status_code}")
            print(f"🔴 Failed to add toggle item. Status Code: {response.status_code}")
            # logging.error(f"Response: {response.text}")
            print(f"Response: {response.text}")
            return ""

    except Exception as e:
        # logging.exception("🔴 Exception occurred while adding a toggle item")
        print("🔴 Exception occurred while adding a toggle item")
        return ""

def append_new_topic_toggle_under_given_toggle_id(existing_toggle_id, new_topic_toggle_text):
    """
    Appends a new toggle block as a child under an existing toggle block in a Notion page
    and returns the ID of the created toggle block.

    Parameters:
        existing_toggle_id (str): The ID of the existing toggle block where the new toggle should be appended.
        new_topic_toggle_text (str): The text for the new toggle block.

    Returns:
        str: The ID of the newly created toggle block, or None if the request fails.
    """
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    url = f"https://api.notion.com/v1/blocks/{existing_toggle_id}/children"

    payload_to_add_Toggle_Element = {
        "children": [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": new_topic_toggle_text}
                        }
                    ],
                    "is_toggleable": True  # Enables toggle functionality
                }
            }
        ]
    }

    response = requests.patch(url, headers=headers, json=payload_to_add_Toggle_Element)
    
    if response.status_code == 200:
        created_block = response.json()
        new_block_id = created_block.get("results", [{}])[0].get("id")
        print(f"✅ Toggle block added successfully! ID: {new_block_id}")
        return new_block_id  # Return the new toggle block's ID
    else:
        print(f"❌ Failed to add toggle block: {response.text}")
        return None

def add_bulleted_list_with_subpoints(parent_toggle_id, bullet_points):
    """
    Adds a bulleted list under a given toggle block in Notion, with optional sub-bullet points.

    Parameters:
        parent_toggle_id (str): The ID of the toggle block under which the bulleted list will be added.
        bullet_points (list of dict): A list where each dictionary represents a bullet point and may contain sub-bullets.

    Example bullet_points structure:
        [
            {"sub_topic": "Main Bullet 1", "bullet_points": ["Sub-point 1.1", "Sub-point 1.2"]},
            {"sub_topic": "Main Bullet 2", "bullet_points": ["Sub-point 2.1"]}
        ]
    
    Returns:
        list: A list of IDs of the created bullet items.
    """
    
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    url = f"https://api.notion.com/v1/blocks/{parent_toggle_id}/children"
    
    # Constructing the payload with bullet points and sub-bullets
    children = []
    
    for bullet in bullet_points:
        main_bullet = {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": bullet["sub_topic"]}}]
            }
        }
        
        # If sub-bullets exist, add them as children of the main bullet
        if "bullet_points" in bullet and bullet["bullet_points"]:
            main_bullet["bulleted_list_item"]["children"] = [
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": sub_text}}]
                    }
                }
                for sub_text in bullet["bullet_points"]
            ]
        
        children.append(main_bullet)
    
    payload = {"children": children}

    response = requests.patch(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        created_blocks = response.json()
        bullet_ids = [block["id"] for block in created_blocks.get("results", [])]
        print(f"✅ Bulleted list added successfully! IDs: {bullet_ids}")
        return bullet_ids  # Return the list of created bullet IDs
    else:
        print(f"❌ Failed to add bulleted list: {response.text}")
        return None

@tool
def proceeding_to_changes_node(llm_response_content):
    """
    Processes the LLM response containing JSON data related to meeting changes.

    This tool is used when the current meeting summary topic is an existing one.
    It takes the LLM-generated JSON string and extracts the list of changes.

    Parameters:
    llm_response_content (str): A JSON-formatted string received from the LLM response.

    Steps:
    1. Cleans the JSON string by removing Markdown formatting (````json ... ````) if present.
    2. Parses the cleaned string into a Python dictionary.
    3. Extracts the list of changes under the "changes" key.
    4. Prints the cleaned JSON string, extracted changes list, and the original LLM response.

    Returns:
    None (prints extracted information for debugging/logging purposes).
    """
    print("**************  Received Content below ********")
    print(llm_response_content)
    print("***************************************************")
    cleaned_json_str = re.sub(r'^```json\n|\n```$', '', llm_response_content.strip())
    print(cleaned_json_str)
    json_data = json.loads(cleaned_json_str)
    changes_list = json_data.get("changes", [])
    print(changes_list)
    # print(llm_response_content)


def add_heading_to_page(NOTION_PAGE_ID ,heading_text):
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    url = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children"

    payload_to_add_Toggle_Element = {
        "children": [
            {
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": heading_text}
                        }
                    ],
                    "is_toggleable": False # Enables toggle functionality
                }
            }
        ]
    }

    response = requests.patch(url, headers=headers, json=payload_to_add_Toggle_Element)
    
    if response.status_code == 200:
        created_block = response.json()
        new_block_id = created_block.get("results", [{}])[0].get("id")
        print(f"✅ Heading block added successfully! ID: {new_block_id}")
        return True  # Return the new toggle block's ID
    else:
        print(f"❌ Failed to add toggle block: {response.text}")
        return None
    



def create_notion_table(parent_block_id):
    url = "https://api.notion.com/v1/databases"

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    payload = {
        "parent": {"type": "page_id", "page_id": parent_block_id},
        "title": [{"type": "text", "text": {"content": "Action Items Table"}}],
        "properties": {
            "Action Item": {
                "title": {}
            },
            "Status": {
                "multi_select": {
                    "options": [
                        {"name": "Not Started", "color": "gray"},
                        {"name": "Block", "color": "red"},
                        {"name": "Completed", "color": "green"},
                        {"name": "In Progress", "color": "blue"},
                    ]
                }
            },
            "Assigned To": {
                "rich_text": {}
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        database_id = response.json().get("id")
        print(f"Database created successfully! ID: {database_id}")
        return database_id
    else:
        print(f"Error: {response.status_code}, {response.json()}")
        return None

##########################################################################################################
###########################################################################################################

# newly_created_database_id = create_notion_table("196e35223beb806a8889f2524d28bdaf")
# print(newly_created_database_id)
# print("database creation completed")
# action_item_to_add = [{
#         "action_item" : "This is the First thing to do",
#         "status" : "In Progress",
#         "assigned_to" : ["Ganesh Putta" , "Kethavath"]
#     },
#     {
#         "action_item" : "This is the Second thing to do",
#         "status" : "Completed",
#         "assigned_to" : ["Ganesh Putta" , "Shahbaaz Singh"]
#     }
# ]


# for each_item in action_item_to_add:
# add_page_to_action_items_database_table_by_id(newly_created_database_id , each_item)





##########################################################################

# appended_toggle_block_id = append_toggle_to_given_page("196e35223beb806a8889f2524d28bdaf" , "Latest Notes - 12/02/25")
# print(f"appended_toggle_block_id is {appended_toggle_block_id}")

# new_topic_toggle_id = append_new_topic_toggle_under_given_toggle_id(appended_toggle_block_id , "This is Topic-1")
# print(f"new_topic_toggle_id is {new_topic_toggle_id}")

# under_topics_content = [
#                 {
#                     "sub_topic": "Project Overview",
#                     "bullet_points": [
#                         "Importance of concluding discussions this week.",
#                         "Development to commence next week.",
#                         "High-level diagram provided by Pritesh Singh to outline the process flow."
#                     ]
#                 }
#             ]

# add_bulleted_list_with_subpoints("198e3522-3beb-8122-986d-cd08e069a4a4" , under_topics_content)

# append_bulleted_list_to_block.invoke(input = {"adding_content_info" : {"blockId": "198e3522-3beb-8146-bb03-c3020975ed8b", "bullet_points_list": ["This is sub-topic point-1" , "This is sub-topic point-2"]}})
# add_heading_to_page("196e35223beb806a8889f2524d28bdaf" , "This is related to Change Logs")
###############################################################################
# fetch_data_from_database("197e35223beb80039714f0cd468bce2e")
# add_page_to_database.invoke(input = {"data" : {"action_data":"Gmail account for the bot" , "status":"Not Started" , "assigned_to":"puttaganesh7386@gmail.com"}})
# eachPageId = "196e35223beb806a8889f2524d28bdaf"
# text_content_of_notion_page = fetch_notion_page_content.invoke(input = {"notion_page_id_info" : {"notion_page_id" : eachPageId}})
# print(text_content_of_notion_page)


# Documentation Agent Notion Page Id :- 18ae35223beb804fbfb3cce77e9a94fb
# Marketing Agent Notion Page Id :-  196e35223beb806a8889f2524d28bdaf

# over_all_notion_data = "\n".join(result_text_list)
# print(over_all_notion_data)

# add_Toggle_Item_with_Bullet_Points.invoke(input = { 'addingToggleItemInfo' : { 'NOTION_PAGE_ID': "18ae35223beb804fbfb3cce77e9a94fb" ,'toggle_item_text': "Change Log - 05-02-25" , 'bullet_points_list' : ["This is test Bullet-item-100 , changes -20 👍👍👍👍" , "This is test Bullet-Item- 200, changes - 30 👍👍👍👍"]}})
# table_data = get_table_content("18ae3522-3beb-8030-b78c-d34069e39547")
# for each_row in table_data:
#     print(each_row)

# append_bulleted_list_to_block.invoke(input = { 'adding_content_info' :  {'objectId' : "190e3522-3beb-8128-96f7-dcee950cdc41" ,'bullet_points_list' : [" This text is related adding change log in Toggle-40  " ," This text is related adding change log in Toggle - 50 " ] }})

# add_Toggle_Item_with_Bullet_Points.invoke(input = {'addingToggleItemInfo' : {"NOTION_PAGE_ID" :"18be3522-3beb-80f6-b019-e2f6bd5a0e02" , "toggle_item_text" : "This toggle added by uing LLM tool " , 'bullet_points_list' : ["This is point change-1" , "This is Point change-2"] } })


# update_block_content.invoke(input = {'updating_info' : {
#     'objectId' : "18be3522-3beb-80e0-a5e2-ec955ac2316a",
#     'new_text_content' : "Current schema has been changed by Pritesh and final consolidated output is edited in Google Sheet"
# }})

# delete_block.invoke("18be3522-3beb-8114-a2cc-d753a16375ff")
# print(type_of_obj)

# update_block_content.invoke(input = { 
#     "updating_block_info": { 
#         "objectId": "18be3522-3beb-80a1-ad55-fbe11468e930",  
#         "new_text_content": "Objective to expand to ~500,000 companies (original scope updated in Change Log)"  
#     }  
# })


# append_bulleted_list_to_block.invoke(input = {
#     "adding_content_info" : {
#         "blockId" : "18be3522-3beb-803a-91c0-e1fcc3424d31",
#         "bullet_points_list" : ["Bhoopendra Sharma mentioned connecting with marketing team to understand requirements for integrating oxygen plugin as discussed in the meeting."]
#     }
# })

# change_logs = [
#             "Updated the expansion objective to ~500,000 companies per the latest meeting summary.",
#             "Appended discussion points about the schema and consolidated outputs in Google Sheets."
#         ]

# today_date = datetime.today().strftime('%Y-%m-%d')
# page_id = "18ae35223beb804fbfb3cce77e9a94fb"
# append_toggle_with_bullets_for_change_log.invoke(input = {"addingToggleItemInfo" : {
#                 "NOTION_PAGE_ID": page_id,
#                 "toggle_item_text": f"Change Log {today_date}",
#                 "bullet_points_list": change_logs
#             }})
# {
#                 "LineId": "5.5.3.1",
#                 "objectId": "18be3522-3beb-803a-91c0-e1fcc3424d31",
#                 "ChangeType": "append",
#                 "function_to_be_used": "append",
#                 "ContentForChange": "Bhoopendra Sharma mentioned connecting with marketing team to understand requirements for integrating oxygen plugin as discussed in the meeting."
#             }
# addNum.invoke(input = {'inputDict' : {'a':10 , 'b':20} })

# {
#                 "LineId": "5.5.3.1",
#                 "objectId": "18be3522-3beb-803a-91c0-e1fcc3424d31",
#                 "ChangeType": "append",
#                 "function_to_be_used": "append",
#                 "ContentForChange": "Bhoopendra Sharma mentioned connecting with marketing team to understand requirements for integrating oxygen plugin as discussed in the meeting."
#             }


# add_page_to_meetings_history_database_table("197e35223beb80039714f0cd468bce2e" , {"meeting_name" : "Axial Project" , "happened_date" : "Feb 12 ,2025"})





# delete_block.invoke(input = {"deleting_block_info" : {"blockId": "18be3522-3beb-80bd-8c98-f10ec3f65f81"}})  


# fetched_notion_pages_data = fetch_data_from_notion_pages_data_database_table("1a3e35223beb806e80acdc2563180fb1")
# print(fetched_notion_pages_data)

# fetched_notion_pages_data = fetch_data_from_latest_projects_data_database_table("1a5e35223beb80d49b99efdbdf21e4be")
# for each_page in fetched_notion_pages_data:
#     data = each_page["latest_data"]
#     print(data)
    # json_data = json.loads(data[0])
    # print(json_data)

# print(fetched_notion_pages_data)
# process_updating_notion_page_latest_data("196e35223beb806a8889f2524d28bdaf" , [
#   "SEMrush integration completed added successfully.",
#   "Addressed API authentication errors.",
#   "Backup automation approach using Selenium implemented."
# ])
# retrieved_data = get_latest_projects_row_data("196e35223beb806a8889f2524d28bdaf")
# print(retrieved_data)

# Step 1: Get row data from the correct database
# DATABASE_ID = "1a5e35223beb80d49b99efdbdf21e4be"
# ROW_ID = "mar_196e35223beb806a8889f2524d28bdaf"





# def fetch_database_properties(database_id):
#     url = f"https://api.notion.com/v1/databases/{database_id}"
#     headers = {
#         "Authorization": f"Bearer {NOTION_API_KEY}",
#         "Notion-Version": "2022-06-28"
#     }
#     response = requests.get(url, headers=headers)
#     print(json.dumps(response.json(), indent=4))

# fetch_database_properties("1a5e35223beb80d49b99efdbdf21e4be")

"""
notion_page_to_action_items_table_id_matching  = {
    "18ae35223beb804fbfb3cce77e9a94fb" : "18be35223beb801e9930d555918b1a43",
    "196e35223beb806a8889f2524d28bdaf" : "196e35223beb81228d00c817b034f906"
}

action_item_data = {"action_item" : "This is to do by EOD" , "status" : "Not Started" , "assigned_to" : ["person-1" , "person-2"]}

add_page_to_action_items_database_table_by_id("196e35223beb81228d00c817b034f906" , action_item_data)

"""


# existing_notion_pages_list_info = fetch_data_from_existing_notion_pages_data_database_table()

# print(existing_notion_pages_list_info)










# PAGE_ID  = "184e35223beb80a7b2d4c87ad4933b49"
# def get_sub_pages_info_by_parent_page():
#     url_to_get_sub_pages = f"https://api.notion.com/v1/blocks/{PAGE_ID}/children"
#     headers = {
#         "Authorization" : f"Bearer {NOTION_API_KEY}",
#         "Content-Type": "application/json",
#         "Notion-Version": "2022-06-28"
#     }

#     try:
#         response = requests.get(url_to_get_sub_pages, headers=headers)

#         # Debugging: Print the response status and text
#         print("Response Status Code:", response.status_code)
#         print("Response JSON:", response.text)

#         if response.status_code == 200:
#             sub_pages_data_json = response.json()
#             # print(sub_pages_data_json)

#             # # Save JSON to file
#             with open("pagesresult.json", "w", encoding="utf-8") as json_file:
#                 json.dump(sub_pages_data_json, json_file, indent=4)

#             print("✔️ JSON data dumped successfully!")
#         else:
#             print(f"❌ API Error: {response.status_code}")
#             print("Error details:", response.json())
#     except Exception as e:
#         print("❌❌❌❌❌❌❌❌❌ Some thing Happened")
#         print(f"Error occured while fetching sub-pages of parent with id as {PAGE_ID}")



# data = '''json
# {
#   "in_progress": "tools provided for llm is working and need to be optimized",
#   "actions_to_be_taken": "checking QA of tools for llm",
#   "actions_taken": "connected with QA team",
#   "resources": "a website",
#   "action_taken_date": "2025-01-01"
# }
# '''
# data = data.replace("json" , "")
# message = AIMessage(content=f'```\n{data}\n```')

# # Initialize the output parser
# output_parser = JsonOutputParser()

#     # Parse the response
# parsed_output = output_parser.invoke(message)
# print(parsed_output)

# get_sub_pages_info_by_parent_page()

# database_id_1 = "184e35223beb8072b2f8fc8d22260d67"

# @tool
# def get_data_from_Database_id_1(input_data=None):
#     """
#     Fetches data from the specified Notion database.

#     Returns:
#         dict: JSON response containing the database query results.
#     """
#     database_id_1 = "184e35223beb8072b2f8fc8d22260d67"
#     url = f"https://api.notion.com/v1/databases/{database_id_1}/query"
#     headers = {
#         "Authorization": f"Bearer {NOTION_API_KEY}",
#         "Content-Type": "application/json",
#         "Notion-Version": "2022-06-28",
#     }
#     payload = {"page_size": 100}
#     try:
#         response = requests.post(url, headers=headers, json=payload)
#         if response.status_code == 200:
#             data = response.json()  # Retrieve the JSON data
#             return data  # Return the data instead of saving it to a file
#         else:
#             print(f"Error fetching data: {response.status_code} - {response.text}")
#             return None
#     except Exception as e:
#         print(f"Exception occurred: {e}")
#         return None


# """
# def fetch_content_by_given_block_page_id_helper_func(parent_page_id):
#     url_to_get_all_content = f"https://api.notion.com/v1/blocks/{parent_page_id}/children"
#     headers = {
#         "Authorization": f"Bearer {NOTION_API_KEY}",
#         "Content-Type": "application/json",
#         "Notion-Version": "2022-06-28"
#     }
    
#     try:
#         response = requests.get(url_to_get_all_content, headers=headers)
#         response.raise_for_status()
#     except requests.RequestException as e:
#         return {"id": parent_page_id, "error": "Data not fetched", "children": []}
    
#     page_content_json_data = response.json()
#     results_list = page_content_json_data.get("results", [])
    
#     def process_block(block):
#         object_type = block.get("type")
#         has_children = block.get("has_children", False)
#         object_data = block.get(object_type, {})
#         rich_text_list = object_data.get("rich_text", [])
        
#         text_data = "".join([text_item["text"]["content"] for text_item in rich_text_list if "text" in text_item])
        
#         processed_block = {
#             "id": block["id"],
#             "type": object_type,
#             "text": text_data,
#             "children": []
#         }

#         if has_children:
#             processed_block["children"] = fetch_content_by_given_block_page_id_helper_func(block["id"])  # Recursive call
        
#         return processed_block
    
#     return [process_block(block) for block in results_list]

# """


# 
# def fetch_content_by_given_block_page_id_helper_func(parent_page_id, indent=0):
#     # logging.info("Getting Content By Given Page Id method is invoked. Please wait for execution ")

#     url_to_get_all_content = f"https://api.notion.com/v1/blocks/{parent_page_id}/children"
#     headers = {
#         "Authorization": f"Bearer {NOTION_API_KEY}",
#         "Content-Type": "application/json",
#         "Notion-Version": "2022-06-28"
#     }

#     try:
#         response = requests.get(url_to_get_all_content, headers=headers)
#         response.raise_for_status()
#     except requests.RequestException as e:
#         # logging.error(f"Exception occurred while fetching data: {e}")
#         return [" " * indent + f"Data not fetched for ObjectId {parent_page_id}"]

#     page_content_json_data = response.json()
#     # logging.info(f"Successfully received response for ObjectID {parent_page_id}")

#     results_list = page_content_json_data.get("results", [])
#     over_all_data = []

#     for each_result in results_list:
#         object_type = each_result.get("type")
#         has_children = each_result.get("has_children", False)

#         object_data = each_result.get(object_type, {})
#         rich_text_list = object_data.get("rich_text", [])

#         text_data = "".join([text_item["text"]["content"] for text_item in rich_text_list if "text" in text_item])

#         if text_data:
#             over_all_data.append(" " * indent + "- " + text_data + f" id - {each_result['id']}")

#         # Recursively fetch children
#         if has_children:
#             child_content = fetch_content_by_given_block_page_id_helper_func(each_result["id"], indent + 2)
#             over_all_data.extend(child_content)

#     return over_all_data
#

# eachPageId = "18ae35223beb804fbfb3cce77e9a94fb"
# text_content_of_notion_page = fetch_notion_page_content.invoke(input = {"notion_page_id_info" : {"notion_page_id" : eachPageId}})
# print(text_content_of_notion_page)

# existing_notion_pages = fetch_data_from_existing_notion_pages_data_database_table()
# print(existing_notion_pages)


# latest_project_details_data = {
#     "notion_page_id" : "17827363738028737",
#     "page_project_title" : "new_project_name",
#     "latest_data" : ["point1" , "point2" , "point3"]
# }
# add_latest_project_details_row_data(latest_project_details_data)
# updated_latest_project_details_data = {
#     "notion_page_id" : "17827363738028737",
#     "latest_data" : ["updated-point1" , "updated-point2" , "updated-point3"]
# }
# update_latest_project_details_row_data(updated_latest_project_details_data)