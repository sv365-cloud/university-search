import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv
from langchain.document_loaders import PyPDFLoader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
import numpy as np


logging.basicConfig(
    filename="rag_queries.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)


class RAGConfig:
    DATABASE_PATH = "database"
    EMBEDDING_MODEL = "models/text-embedding-004"
    LLM_MODEL = "gemini-2.0-flash"
    LLM_TEMPERATURE = 0.0
    MAX_OUTPUT_TOKENS = 10000
    RETRIEVER_K = 50
    RETRIEVER_FETCH_K = 70


class RAGBackend:
    def __init__(self, json_files: List[str] = None, pdf_files: List[str] = None):
        self.json_files = [
            "primary_data/winter2026/winter_2026_courses.json",
            "primary_data/spring2026/spring_2026_courses.json",
            "primary_data/fall2025/fall_2025_courses.json",
            "primary_data/spring2025/spring_2025_courses.json"
        ]
        self.lsu_uni_files = [
            "secondary_data/LSU_courses.json"
        ]
        self.pdf_files = [
            "secondary_data/2025-26-bulletin.pdf",
            "secondary_data/universitycourses.pdf"
        ]

        load_dotenv()
        self.config = RAGConfig()
        self.embeddings = self._initialize_embeddings()
        self.vector_store = self._load_vector_store()
        self.llm = self._initialize_llm()
        self.prompt_template = self._create_prompt_template()

    def _initialize_embeddings(self) -> GoogleGenerativeAIEmbeddings:
        return GoogleGenerativeAIEmbeddings(model=self.config.EMBEDDING_MODEL)

    def _initialize_llm(self):
        return ChatGoogleGenerativeAI(
            model=self.config.LLM_MODEL,
            temperature=self.config.LLM_TEMPERATURE,
            max_output_tokens=self.config.MAX_OUTPUT_TOKENS
        )

    def _load_documents(self) -> List[Document]:
        all_documents: List[Document] = []

        # Load JSON documents
        for file_path in self.json_files:
            if not os.path.exists(file_path):
                continue
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                content = (
                    f"Title: {item.get('title', '')}\n"
                    f"Code: {item.get('code', '')}\n"
                    f"Department: {item.get('department_full', '')} ({item.get('department_short', '')})\n"
                    f"Professor: {item.get('professor', '')}\n"
                    f"Time: {item.get('time', '')}\n"
                    f"Description:\n{item.get('description', '')}"
                )
                all_documents.append(Document(
                    page_content=content,
                    metadata={
                        "title": item.get("title", ""),
                        "code": item.get("code", ""),
                        "department": item.get("department_short", ""),
                        "professor": item.get("professor", ""),
                        "time": item.get("time", ""),
                        "source": Path(file_path).name
                    }
                ))

        # Load PDF documents
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        for pdf_path in self.pdf_files:
            if not os.path.exists(pdf_path):
                continue
            loader = PyPDFLoader(pdf_path)
            pdf_docs = loader.load()
            for i, doc in enumerate(pdf_docs, start=1):
                doc.metadata["source"] = Path(pdf_path).name
                doc.metadata["page"] = i
            split_docs = text_splitter.split_documents(pdf_docs)
            all_documents.extend(split_docs)

        # Load LSU JSON documents
        lsu_file_path = "secondary_data/LSU_courses.json"
        if os.path.exists(lsu_file_path):
            with open(lsu_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                content = (
                    f"Department: {item.get('Dept', '')}\n"
                    f"Course Number: {item.get('Num', '')}\n"
                    f"Course Name: {item.get('Name', '')}\n"
                    f"Description:\n{item.get('Desc', '')}\n"
                    f"Requirements: {item.get('Reqs', '')}\n"
                    f"University: {item.get('university_name', '')}"
                )
                all_documents.append(Document(
                    page_content=content,
                    metadata={
                        "Dept": item.get("Dept", ""),
                        "Num": item.get("Num", ""),
                        "Name": item.get("Name", ""),
                        "Reqs": item.get("Reqs", ""),
                        "university_name": item.get("university_name", ""),
                        "source": Path(lsu_file_path).name
                    }
                ))

        logging.info(f"Loaded {len(all_documents)} total documents (JSON + PDF + LSU JSON).")
        return all_documents


    def _load_vector_store(self) -> FAISS:
        index_file = os.path.join(self.config.DATABASE_PATH, "index.faiss")
        if os.path.exists(index_file):
            logging.info("Loading existing vector store...")
            return FAISS.load_local(
                self.config.DATABASE_PATH,
                self.embeddings,
                allow_dangerous_deserialization=True
            )

        logging.info("Creating new vector store from documents...")
        documents = self._load_documents()
        vector_store = FAISS.from_documents(documents=documents, embedding=self.embeddings)
        os.makedirs(self.config.DATABASE_PATH, exist_ok=True)
        vector_store.save_local(self.config.DATABASE_PATH)
        logging.info("Vector store saved locally.")
        return vector_store

    def _create_prompt_template(self) -> PromptTemplate:
        template = """
            You are a helpful **Course Advisor** assisting students in finding the most suitable courses.  
            Use only the provided course data to answer. If the information is not available in the context, say so.  
            Be clear, concise, and student-friendly in your response.  

            ---
            ### Context (retrieved data):
            {context}

            ### Student's Question:
            {question}

            ### Your Response (structured and helpful):
            - Provide a direct answer to the student's question.  
            - If relevant, list matching courses with **Title, Code, Department, Professor, and Meeting Time**.  
            - Summarize in a way that makes it easy for students to decide.  
            - If no relevant course is found, say: *"No exact match found, but here are related options."*  
        """
        return PromptTemplate.from_template(template)


    def get_response(self, question: str, body_search: str = None) -> Dict[str, Any]:
        start_time = time.time()
        logging.info(f"Query received: {question}")

        try:
            # Prepare search kwargs for hybrid search
            search_kwargs = {}
            if body_search:
                search_kwargs["body_search"] = body_search

            # Perform MMR search with hybrid keyword
            docs = self.vector_store.max_marginal_relevance_search(
                query=question,
                k=self.config.RETRIEVER_K,
                fetch_k=self.config.RETRIEVER_FETCH_K,
                search_kwargs=search_kwargs 
            )

            # Embed query
            query_embedding = self.embeddings.embed_query(question)

            # Embed retrieved documents
            doc_contents = [doc.page_content for doc in docs]
            doc_embeddings = self.embeddings.embed_documents(doc_contents)

            # Compute cosine similarities and add to metadata
            for i, doc in enumerate(docs):
                q_norm = np.linalg.norm(query_embedding)
                d_norm = np.linalg.norm(doc_embeddings[i])
                sim = 0.0 if q_norm == 0 or d_norm == 0 else np.dot(query_embedding, doc_embeddings[i]) / (q_norm * d_norm)
                doc.metadata['score'] = sim

            # Log retrieved documents & scores
            logging.info("Retrieved Documents:")
            for doc in docs:
                score = doc.metadata.get('score', 'N/A')
                logging.info(f"- Source: {doc.metadata.get('source', 'unknown')} | Page: {doc.metadata.get('page', 'N/A')} | Score: {score}")

            # Build context from retrieved docs including metadata
            context_parts = []
            for doc in docs:
                meta_str = "Metadata:\n" + "\n".join([f"{k}: {v}" for k, v in doc.metadata.items()])
                context_parts.append(meta_str + "\nContent:\n" + doc.page_content)
            context = "\n\n---\n\n".join(context_parts)

            # Format prompt
            input_dict = {"context": context, "question": question}
            prompt = self.prompt_template.format(**input_dict)

            # Invoke LLM
            response = self.llm.invoke(prompt).content

            elapsed_time = time.time() - start_time
            logging.info(f"Response time: {elapsed_time:.2f}s")

            # Prepare retrieved courses (filter to those with 'code')
            retrieved_courses = [
                {**doc.metadata, "content": doc.page_content}
                for doc in docs if "code" in doc.metadata
            ]

            return {
                "answer": response,
                "retrieved_courses": retrieved_courses
            }

        except Exception as e:
            logging.error(f"Error processing query: {str(e)}")
            raise ValueError(f"Error processing query: {str(e)}")


    def evaluate(self, labeled_set_file: str) -> List[Dict[str, Any]]:
        
        if not os.path.exists(labeled_set_file):
            raise FileNotFoundError(f"Labeled set file not found: {labeled_set_file}")

        # Load labeled set from JSON
        with open(labeled_set_file, "r", encoding="utf-8") as f:
            labeled_set = json.load(f)

        results = []

        for item in labeled_set:
            start_time = time.time()

            # Retrieve documents from FAISS
            docs = self.vector_store.max_marginal_relevance_search(
                query=item["query"],
                k=self.config.RETRIEVER_K,
                fetch_k=self.config.RETRIEVER_FETCH_K
            )

            # Compute similarity scores manually
            query_embedding = self.embeddings.embed_query(item["query"])
            doc_contents = [doc.page_content for doc in docs]
            doc_embeddings = self.embeddings.embed_documents(doc_contents)

            for i, doc in enumerate(docs):
                q_norm = np.linalg.norm(query_embedding)
                d_norm = np.linalg.norm(doc_embeddings[i])
                sim = np.dot(query_embedding, doc_embeddings[i]) / (q_norm * d_norm) if q_norm != 0 and d_norm != 0 else 0.0
                doc.metadata['score'] = float(sim)  # ✅ Convert to native float to avoid JSON serialization issues

            latency = time.time() - start_time

            # Log for evaluation
            logging.info(f"Evaluation query: {item['query']}")
            logging.info(f"Evaluation latency: {latency:.2f}s")
            for doc in docs:
                score = doc.metadata.get('score', 'N/A')
                logging.info(f"- Eval Retrieved: Source: {doc.metadata.get('source', 'unknown')} | "
                            f"Code: {doc.metadata.get('code', 'N/A')} | Score: {score}")

            # Compute precision and recall
            retrieved_codes = [doc.metadata.get("code") for doc in docs if "code" in doc.metadata]
            relevant = set(item["relevant_codes"])
            retrieved = set(retrieved_codes)
            tp = len(relevant & retrieved)
            precision = tp / len(retrieved) if retrieved else 0.0
            recall = tp / len(relevant) if relevant else 0.0

            results.append({
                "query": item["query"],
                "precision": precision,
                "recall": recall,
                "latency": latency
            })

        # Log overall results
        logging.info(f"Evaluation results: {results}")

        # Optionally save results to JSON
        results_file = "evaluation_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)
        logging.info(f"Evaluation results saved to {results_file}")

        return results