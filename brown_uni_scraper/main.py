import json
import os
import html

from brown_uni_scraper.scrap_brown_courrses import get_course_metadata, parallel_get_course_details, clean_description
from brown_uni_scraper.scrap_brown_departments import fetch_and_parse_subjects


def build_structured_courses(course_list: list, course_details: dict, department_map: dict) -> list:
    """
    Build structured course metadata combining raw courses, details, and department info.
    """
    print("[INFO] Structuring course metadata...")
    structured_courses = []
    processed_courses = set()  # track unique (department_short, course_number) pairs
    
    for course in course_list:
        # skip if course details are missing
        course_info = course_details.get(course["code"])
        if not course_info:
            print(f"[WARN] Skipping {course['code']} (no details found)")
            continue

        # skip invalid courses: online only, taught by "Team", or cross-listed
        if (course["meets"] == "Course offered online") \
           or (course["instr"] == "Team") \
           or (course["stat"] == "X"):
            continue

        # e.g., "CSCI 0320" -> department_short = "CSCI", course_number = "0320"
        department_short, course_number = course["code"].split(" ")
        
        # avoid duplicates
        if (department_short, course_number) in processed_courses:
            continue
        processed_courses.add((department_short, course_number))
        
        structured_entry = {
            "department_full": department_map.get(department_short, department_short),
            "department_short": department_short,
            "code": course_number,
            "title": course["title"],
            "professor": course["instr"],
            "time": course["meets"],
            "description": clean_description(course_info["description"]),
            "writ": "WRIT" in course_info["attr_html"] \
                    or department_short in ["ENGL", "COLT", "LITA", "LITR"],
            "fys": "FYS" in course_info["attr_html"],
            "soph": "SOPH" in course_info["attr_html"],
            "rpp": "RPP" in course_info["attr_html"],
        }

        # build one-liner attributes string
        structured_entry["attributes"] = " ".join(
            attribute for attribute, exists in [
                ("writ", structured_entry["writ"]),
                ("fys", structured_entry["fys"]),
                ("soph", structured_entry["soph"]),
                ("rpp", structured_entry["rpp"]),
            ] if exists
        )

        structured_courses.append(structured_entry)
    
    return structured_courses


def scrape_courses(term: str, year: str, output_path: str):
    """
    Scrape course data, process it, and save as structured JSON.
    """
    # fetch raw course data
    raw_courses = get_course_metadata(term, year)
    course_details = parallel_get_course_details(raw_courses)
    department_mapping = fetch_and_parse_subjects()
    
    # structure the course metadata
    processed_courses = build_structured_courses(raw_courses, course_details, department_mapping)

    # write to file
    print(f"[INFO] Writing {len(processed_courses)} processed courses to file...")
    json_output = json.dumps(processed_courses, ensure_ascii=False, indent=4, sort_keys=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(json_output)

    print("[INFO] Done!")


if __name__ == "__main__":
    TERM = "winter"
    YEAR = "2026"
    
    scrape_courses(TERM, YEAR, f"../data/{TERM}{YEAR}/courses.json")
