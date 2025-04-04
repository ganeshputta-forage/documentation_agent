from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def extract_meeting_summary_selenium(read_ai_url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run without opening browser
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.get(read_ai_url)
    time.sleep(5)  # Wait for the page to load

    # Extract title
    try:
        title = driver.find_element(By.TAG_NAME, "h1").text
    except:
        title = "No Title Found"

    # Extract summary
    try:
        summary = driver.find_element(By.CLASS_NAME, "summary-class").text
    except:
        summary = "No Summary Found"

    # Extract action items
    try:
        action_items = driver.find_element(By.CLASS_NAME, "action-items-class").text
    except:
        action_items = "No Action Items Found"

    driver.quit()

    return {
        "Meeting Title": title,
        "Summary": summary,
        "Action Items": action_items
    }

# Example usage:
read_ai_meeting_url = "https://app.read.ai/analytics/meetings/01JJ6EDC2MB58XMGSTG62Q56FW?t=329"
meeting_data = extract_meeting_summary_selenium(read_ai_meeting_url)
print(meeting_data)
