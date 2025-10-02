# main.py (separate file for FastAPI app)

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Dict, Any, List
from fastapi import Query


# Assuming the updated code above is in a file named rag.py
from rag_backend import RAGBackend

app = FastAPI(title="RAG Course Assistant API")

security = HTTPBasic()

# Hardcoded credentials (replace with env vars in production)
VALID_USERNAME = "user"
VALID_PASSWORD = "pass"

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != VALID_USERNAME or credentials.password != VALID_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

rag = RAGBackend()

class QueryRequest(BaseModel):
    question: str

@app.post("/query", response_model=Dict[str, Any])
def query_endpoint(request: QueryRequest, auth: HTTPBasicCredentials = Depends(verify_credentials)):
    result = rag.get_response(request.question)
    return result


@app.get("/evaluate", 
        response_model=List[Dict[str, Any]])
def evaluate_endpoint(
    labeled_set_file: str = Query("small_eval_set.json", 
                            description="Path to JSON labeled set"),
    auth: HTTPBasicCredentials = Depends(verify_credentials)
):
    
    results = rag.evaluate(labeled_set_file=labeled_set_file)
    return results
