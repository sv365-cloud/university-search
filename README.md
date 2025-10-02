# University Course Search with RAG

## Introduction

This project is an academic course search tool designed to answer natural language questions from students. It uses a Retrieval-Augmented Generation (RAG) pipeline to intelligently search university course catalogs and deliver accurate course recommendations.

The system ingests course data from multiple sources, processes it, and stores it efficiently to allow fast semantic search combined with keyword-based filtering.

The initial use case focuses on Brown University’s Courses @ Brown (CAB) but also integrates course catalogs from Louisiana State University (LSU). This hybrid approach saves students considerable time compared to manually searching large PDF bulletins or course catalog websites.

---

## 📂 Dataset

### 1. Primary Data Sources

Brown University course catalogs scraped from the official Search API using Python (`requests`, `BeautifulSoup`). Data stored in JSON format:

```
primary_data/winter2026/winter_2026_courses.json
primary_data/spring2026/spring_2026_courses.json
primary_data/fall2025/fall_2025_courses.json
primary_data/spring2025/spring_2025_courses.json
```

### 2. Secondary Data Sources

1. Brown University Bulletin PDF

   * Over 900+ pages covering courses, sports, university policies, and more.
   * Data extracted using PDF parsing .

2. Louisiana State University Course Catalog

   * Scraped with Selenium into structured JSON format.
   * Extracted fields include:

     * Course Code
     * Course Title
     * Professor Name
     * Description
     * Prerequisites

---


## ⚙️ System Architecture

The system follows a modular RAG-based architecture designed for flexibility and scalability:

1. **Data Ingestion Layer**

   * Collects course data from multiple sources:

     * JSON catalogs (scraped via APIs or Selenium).
     * University PDFs (parsed with `PyPDF2` / `pdfplumber`).
   * Cleans and standardizes data into a consistent JSON schema.

2. **Preprocessing & Embeddings**

   * Each course entry (title, description, professor, prerequisites, etc.) is processed.
   * Converted into vector embeddings using Google Gemini text-embedding-004.

3. **Vector Database (FAISS)**

   * Stores embeddings for fast similarity search.
   * FAISS chosen for its efficiency and ability to run locally without heavy infrastructure.

4. **Hybrid Retrieval Layer**

   * Combines semantic similarity search with keyword and metadata filtering.
   * Metadata filters include: department, dataset (university), and time (semester).
   * Results are ranked by similarity score.

5. **LLM Response Generation**

   * Top retrieved documents are passed to Gemini-Flash-2.0.
   * LLM generates a natural-language answer, citing course details.
   * If no relevant data is found, the system explicitly informs the user.

6. **Frontend & API Layer**

   * FastAPI backend exposes REST endpoints for programmatic queries.
   * Streamlit frontend provides an interactive UI for students to explore courses.

---


## 🧩 Design Decisions & Trade-offs

* **Multi-Source Data Architecture**
  - Brown University course catalogs (JSON from API)
  - Brown University bulletins (PDF parsing)
  - LSU course data for broader coverage
  - Trade-off: Complex data ingestion pipeline but provides comprehensive search across multiple formats and institutions.

* **FAISS vs. Pinecone/Weaviate**
  → FAISS chosen because it is lightweight, offline, and free.
  → Trade-off: lacks distributed scalability compared to Pinecone.

* **Google Gemini (Embeddings + LLM)**
  - Embeddings: `text-embedding-004` for semantic search
  - LLM: `gemini-2.0-flash` for answer generation
  - Free tier for prototyping, competitive quality, single-vendor simplicity
  - Trade-off: Vendor lock-in vs. avoiding multi-provider complexity

* **Hybrid Search (Keyword + Semantic)**
  → Pure semantic search sometimes retrieves unrelated results.
  → Adding keyword + metadata filters (department, dataset, time) increases precision.

* **FastAPI + Streamlit**
  → FastAPI for backend API and Streamlit for student-facing frontend.
  → Trade-off: Not a single monolithic app; but cleaner separation of concerns.

---

## Setup Instructions

### 🔹 Local Setup (With Docker)

#### Prerequisites

- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose (included with Docker Desktop)

#### Step 1: Clone Repo

```bash
git clone https://github.com/sv365-cloud/university-search.git
cd university-search
```

#### Step 2: Create `.env` file

Create a `.env` file with your Google Gemini API key:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

Get your API key from: https://makersuite.google.com/app/apikey

#### Step 3: Build and Run

```bash
docker-compose up --build
```

The app will be available at: **http://localhost:8501**

#### Step 4: Stop

```bash
docker-compose down
```

---

### 🔹 Local Setup (Without Docker)

#### Step 1: Clone Repo

```bash
git clone https://github.com/sv365-cloud/university-search.git
cd university-search
```

#### Step 2: Create Virtual Environment

```bash
python -m venv rag-env
source rag-env/bin/activate   # Linux/Mac
rag-env\Scripts\activate      # Windows
```

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 4: Set up Environment Variables

Create a `.env` file in the project root with your Google Gemini API key:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

Get your API key from: https://makersuite.google.com/app/apikey

#### Step 5: Run Backend (FastAPI)

```bash
uvicorn main:app --reload
```

Visit: `http://127.0.0.1:8000`

#### Step 6: Run Frontend (Streamlit)

```bash
streamlit run app.py
```

Visit: `http://localhost:8501`

---

### 🔹 AWS Deployment (EC2 Example)

1. **Launch an EC2 Instance** (Ubuntu 22.04 recommended).

   * Minimum: `t2.medium` (2 vCPUs, 4GB RAM).

2. **SSH into EC2**

```bash
ssh -i your-key.pem ubuntu@your-ec2-public-ip
```

3. **Install Dependencies**

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv -y
```

4. **Clone Repo & Setup**

```bash
git clone https://github.com/sv365-cloud/university-search.git
cd university-search
python3 -m venv rag-env
source rag-env/bin/activate
pip install -r requirements.txt
```

5. **Set up Environment Variables**

Create a `.env` file with your Google Gemini API key:

```bash
nano .env
```

Add this line:

```
GOOGLE_API_KEY=your_google_api_key_here
```

Save and exit (Ctrl+X, Y, Enter)

6. **Run Backend with Gunicorn**

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app -b 0.0.0.0:8000
```

7. **Expose Streamlit App**

```bash
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
```

8. **Configure AWS Security Group** to allow ports `8000` (FastAPI) and `8501` (Streamlit).

9. **Access Your App**

- Streamlit UI: `http://YOUR_EC2_PUBLIC_IP:8501`
- FastAPI Backend: `http://YOUR_EC2_PUBLIC_IP:8000`

Replace `YOUR_EC2_PUBLIC_IP` with your actual EC2 instance's public IP address.

---

## 📂 Adding Additional Datasets

To extend the system with new course catalogs (e.g., another university):

1. Scrape or Parse Data into structured JSON with the required fields:

```json
{
  "code": "CS101",
  "title": "Introduction to Computer Science",
  "department_full": "Computer Science",
  "department_short": "CSCI",
  "professor": "Dr. Smith",
  "time": "MWF 10:00-11:00",
  "description": "Basic programming and algorithms"
}
```

2. Save JSON File under `primary_data/` or `secondary_data/`.

3. Modify `rag_backend.py`** to include the new file path.

Open `rag_backend.py` and add your file to the list (lines 43-48):

```python
self.json_files = [
    "primary_data/winter2026/winter_2026_courses.json",
    "primary_data/spring2026/spring_2026_courses.json",
    "primary_data/fall2025/fall_2025_courses.json",
    "primary_data/spring2025/spring_2025_courses.json",
    "primary_data/your_new_file.json"  # Add your file here
]
```

4. **Re-generate Embeddings**

Delete the existing database and restart the app to rebuild:

**Local:**
```bash
rm -rf database/
streamlit run app.py
```

**Docker:**
```bash
docker-compose down
rm -rf database/
docker-compose up --build
```

The vector store will automatically rebuild with the new data on startup.

Now, queries will include the new university dataset seamlessly.

---

## Example Output

```json
{
  "answer": "Here are some courses related to AI and Machine Learning...",
  "retrieved_courses": [
    {
      "title": "Applied Machine Learning and AI",
      "code": "2550",
      "department": "Physics",
      "professor": "L. Gouskos",
      "time": "TTh 2:30-3:50p",
      "source": "winter_2026_courses.json",
      "score": 0.799,
      "content": "This graduate-level course explores integration of ML and AI techniques..."
    }
  ]
}
```

---

## 🛠 Tech Stack

* **Python**
* **BeautifulSoup, Requests, Selenium** – Scraping
* **PyPDF2, pdfplumber** – PDF parsing
* **FAISS** – Vector database
* **Google Gemini Embeddings** – Semantic search
* **Gemini-Flash-2.0** – LLM text generation
* **FastAPI** – Backend API
* **Streamlit** – Interactive frontend

---