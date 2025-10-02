import requests
from bs4 import BeautifulSoup
import html
import re
import json


CAB_BASE_URL = "http://cab.brown.edu"


def fetch_subject_mapping() -> dict:
    
    print("[INFO] Fetching subject list from CAB...")
    try:
        response = requests.get(CAB_BASE_URL)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch CAB subjects: {e}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")

    # Locate <select id="crit-subject">
    select_element = soup.find("select", {"id": "crit-subject"})
    if not select_element:
        print("[ERROR] Could not find <select id='crit-subject'> in CAB HTML.")
        return {}

    subject_mapping = {}
    option_elements = select_element.find_all("option")

    # Regex to capture option value + subject name
    option_pattern = r'<option value="(\w+)">([^<]+)\s+\(\w+\)</option>'

    for option in option_elements:
        match = re.match(option_pattern, str(option))
        if match:
            subject_code = match.group(1)
            subject_name = html.unescape(match.group(2).strip())  # decode HTML entities
            subject_mapping[subject_code] = subject_name

    if not subject_mapping:
        print("[WARN] No subjects were parsed from CAB.")

    return subject_mapping


def save_mapping_to_json(data: dict, file_path: str):
    """
    Save subject mapping dictionary to JSON file.
    """
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        print(f"[INFO] Subject mapping saved to {file_path}")
    except Exception as e:
        print(f"[ERROR] Could not save JSON file: {e}")
