# from langchain.agents import initialize_agent, Tool
# from notion_api_tools import get_data_from_Database_id_1, add_page_to_database
# from langchain_openai import ChatOpenAI
# import os
# from dotenv import load_dotenv

# load_dotenv()

# tools = [
#     Tool(
#         name="GetDataFromNotion",
#         func=get_data_from_Database_id_1,
#         description="Fetches data from the specified Notion database and saves it to a JSON file."
#     ),
#     Tool(
#         name="AddPageToNotion",
#         func=add_page_to_database,
#         description=(
#             "Adds a new page to the Notion database. "
#             "Input should be a JSON object with the following keys: "
#             "in_progress (str), actions_to_be_taken (str), actions_taken (str), "
#             "resources (str), action_taken_date (str in ISO 8601 format)."
#         )
#     ),
# ]

# openai_api_key = os.getenv("OPENAI_API_KEY")
# llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=openai_api_key)

# # Create the agent
# agent = initialize_agent(tools, llm, agent_type="zero-shot-react-description", verbose=True)

# # Example usage
# text = "In Progress task is tools provided for llm is working and need to be optimized. Action to be taken is checking QA of tools for llm. Actions taken is connected with QA team, Resources provided is a website. Action taken date is 01-01-2025."

# # Define the prompt to extract and map values
# prompt = f"""
# Extract and categorize the following information from the provided text:
# 1. In Progress
# 2. Actions to be Taken
# 3. Actions Taken
# 4. Resources
# 5. Action Taken Date

# Here is the text:
# {text}

# Please output the extracted values as a **JSON string** with the following structure:
# {{
#   "in_progress": "<value>",
#   "actions_to_be_taken": "<value>",
#   "actions_taken": "<value>",
#   "resources": "<value>",
#   "action_taken_date": "<value>"
# }}

# Ensure the following:
# - The `action_taken_date` is formatted as "YYYY-MM-DD" (ISO 8601 format).
# - All extracted fields are properly mapped and included in the JSON output.

# Once you have the extracted JSON string, directly use the 'AddPageToNotion' tool with the **stringified JSON** as the input. The tool expects the StringifiedJSON string to contain the arguments:
# - 'in_progress' (str)
# - 'actions_to_be_taken' (str)
# - 'actions_taken' (str)
# - 'resources' (str)
# - 'action_taken_date' (str, formatted as "YYYY-MM-DD")

# Your output should be in the form of a valid **JSON string** that can be passed directly into the tool.
# """



# # Run the agent
# agent.invoke(prompt)

# # Now, the agent will extract values and call the add_page_to_database function
# # print()
