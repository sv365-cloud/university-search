# app.py
import streamlit as st
from rag_backend import RAGBackend
import pandas as pd

# Initialize backend once
@st.cache_resource
def load_backend():
    return RAGBackend()

rag = load_backend()

# Page config
st.set_page_config(page_title="Course Finder", layout="wide")

st.title("Course Finder (RAG Powered)")

# Sidebar filters
st.sidebar.header("Filters")

dataset_filter = st.sidebar.multiselect(
    "Select Dataset",
    options=[path.split("/")[-1] for path in rag.json_files],
    default=[]
)

department_filter = st.sidebar.text_input("Department (e.g. CSCI, MATH, ENGL)", "")

meeting_day_filter = st.sidebar.text_input("Meeting Day (e.g. M, T, W, Th, F, TTh, MWF)", "")

k_results = st.sidebar.slider("Number of results", 5, 25, 10)

sort_by_score = st.sidebar.checkbox("Sort by similarity score", value=True)

# Query input
query = st.text_input("Enter your query:", placeholder="e.g. Computer Science courses about AI")

if query:
    with st.spinner("Retrieving courses..."):
        import time
        start_time = time.time()
        results = rag.get_response(query)
        elapsed_time = time.time() - start_time

    # Show response time
    st.markdown(f"⏱️ **Response Time:** {elapsed_time:.2f} seconds")

    st.subheader("Generated Answer")
    st.info(results["answer"])

    # Process retrieved courses
    courses = results["retrieved_courses"]

    if dataset_filter:
        courses = [c for c in courses if c.get("source") in dataset_filter]

    if department_filter:
        courses = [c for c in courses if c.get("department", "").lower().startswith(department_filter.lower())]

    if meeting_day_filter:
        courses = [c for c in courses if meeting_day_filter.lower() in c.get("time", "").lower()]

    if sort_by_score:
        courses = sorted(courses, key=lambda x: x.get("score", 0), reverse=True)

    courses = courses[:k_results]

    st.subheader(f"📄 Retrieved Courses ({len(courses)})")

    if not courses:
        st.warning("No courses matched your filters.")
    else:
        for course in courses:
            with st.container():
                st.markdown(
                    f"""
                    <div style="
                        padding:15px; 
                        border-radius:10px; 
                        margin-bottom:10px; 
                        background-color:#f8f9fa; 
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                        color: black;
                    ">
                        <h4 style="color:black;">{course.get("title","Unknown")} ({course.get("code","N/A")})</h4>
                        <p style="color:black;">
                            <b>Department:</b> {course.get("department","")}<br>
                            <b>Professor:</b> {course.get("professor","")}<br>
                            <b>Meeting Time:</b> {course.get("time","")}<br>
                            <b>Source:</b> {course.get("source","")}<br>
                            <b>Similarity Score:</b> {course.get("score",0):.3f}
                        </p>
                        <p style="color:black;"><b>Description:</b> {course.get("content","No description available").split("Description:")[-1].strip()}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


