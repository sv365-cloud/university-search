import grequests
import requests
import warnings
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

# Suppress BeautifulSoup warnings
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# CAB API endpoints
CAB_BASE_URL = "https://cab.brown.edu"
CAB_COURSE_SEARCH_URL = f"{CAB_BASE_URL}/api/?page=fose&route=search&is_ind_study=N&is_canc=N"
CAB_COURSE_DETAIL_URL = f"{CAB_BASE_URL}/api/?page=fose&route=details"


def build_cab_term_code(term: str, year: str) -> str:
    """
    Convert a given academic term (season + year) into CAB database code.
    
    Example:
        - spring 2023 -> "202220"
        - fall 2022   -> "202210"
    """
    academic_year = int(year) if term == "fall" else int(year) - 1
    term_suffix = "20" if term == "spring" else "10"
    return f"{academic_year}{term_suffix}"


def fetch_course_metadata(term: str, year: str) -> list:
    """
    Fetch metadata for all courses in a given term from CAB.
    """
    print(f"[INFO] Fetching course metadata for {term} {year}...")
    payload = {
        "other": {"srcdb": build_cab_term_code(term, year)},
        "criteria": [
            {"field": "is_ind_study", "value": "N"},
            {"field": "is_canc", "value": "N"},
        ],
    }
    response = requests.post(CAB_COURSE_SEARCH_URL, json=payload)
    response.raise_for_status()
    return response.json().get("results", [])


def fetch_course_details_parallel(course_list: list) -> dict:
    """
    Fetch detailed course information from CAB in parallel requests.
    
    Returns:
        dict: Mapping of course_code -> course_details
    """
    print(f"[INFO] Fetching details for {len(course_list)} courses in parallel...")

    def build_detail_payload(course: dict) -> dict:
        return {
            "group": f"code:{course['code']}",
            "key": f"crn:{course['crn']}",
            "srcdb": course["srcdb"],
            "matched": f"crn:{course['crn']}",
        }

    requests_batch = (grequests.post(CAB_COURSE_DETAIL_URL, json=build_detail_payload(course))
                      for course in course_list)
    responses = grequests.map(requests_batch)

    details_by_code = {}
    for response in responses:
        if response is None:
            print("[WARN] Skipping a course detail (no response)")
            continue

        try:
            response.raise_for_status()
            course_detail = response.json()
            details_by_code[course_detail["code"]] = course_detail
        except requests.exceptions.HTTPError as e:
            print(f"[ERROR] HTTP error while fetching details: {e}")
        except Exception as e:
            print(f"[ERROR] Unexpected error while processing details: {e}")

    return details_by_code


def strip_html_tags(text: str) -> str:
    """
    Clean course description text by removing HTML tags.
    """
    return BeautifulSoup(text, "html.parser").get_text()
