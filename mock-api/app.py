import os
import time
import uuid
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="POC Kestra Mock API", version="1.0.0")
failures_before_success = int(os.getenv("MOCK_API_FAILURES_BEFORE_SUCCESS", "2"))
attempts: Dict[str, int] = {}
operations: Dict[str, Dict] = {}

class Ticket(BaseModel):
    correlation_id: str
    title: str
    severity: str = "medium"
    payload: Optional[dict] = None

@app.get("/health")
def health():
    return {"status": "UP"}

@app.post("/echo")
async def echo(request: Request):
    body = await request.json()
    return {"received": body, "correlation_id": request.headers.get("X-Correlation-Id")}

@app.get("/unstable/{key}")
def unstable(key: str):
    current = attempts.get(key, 0) + 1
    attempts[key] = current
    if current <= failures_before_success:
        raise HTTPException(status_code=503, detail={"attempt": current, "message": "temporary failure"})
    return {"status": "OK", "attempt": current, "key": key}

@app.get("/delayed")
def delayed(seconds: int = 2):
    time.sleep(seconds)
    return {"status": "OK", "delay_seconds": seconds}

@app.get("/servers")
def servers(count: int = 5) -> List[str]:
    return [f"srv-{index:03d}" for index in range(1, count + 1)]

@app.post("/tickets")
def create_ticket(ticket: Ticket):
    ticket_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    return {"ticket_id": ticket_id, "status": "CREATED", **ticket.model_dump()}

@app.post("/operations")
def create_operation(payload: dict):
    operation_id = f"OP-{uuid.uuid4().hex[:8].upper()}"
    operations[operation_id] = {"polls": 0, "payload": payload}
    return {"operation_id": operation_id, "status": "RUNNING"}

@app.get("/operations/{operation_id}")
def operation_status(operation_id: str):
    if operation_id not in operations:
        raise HTTPException(status_code=404, detail="unknown operation")
    operations[operation_id]["polls"] += 1
    polls = operations[operation_id]["polls"]
    status = "DONE" if polls >= 3 else "RUNNING"
    return {"operation_id": operation_id, "status": status, "polls": polls}
