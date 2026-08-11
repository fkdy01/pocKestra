import os
import time
import uuid
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="POC Kestra Mock API", version="1.1.0")
failures_before_success = int(os.getenv("MOCK_API_FAILURES_BEFORE_SUCCESS", "2"))
attempts: Dict[str, int] = {}
operations: Dict[str, Dict] = {}
aap_jobs: Dict[str, Dict] = {}

CMDB_SERVERS: Dict[str, Dict] = {
    "srv-001": {"name": "srv-001", "os": "linux", "zone": "outils", "status": "ACTIVE"},
    "srv-002": {"name": "srv-002", "os": "linux", "zone": "admin", "status": "ACTIVE"},
    "srv-003": {"name": "srv-003", "os": "windows", "zone": "sccm", "status": "ACTIVE"},
    "win-srv-001": {"name": "win-srv-001", "os": "windows", "zone": "sccm", "status": "ACTIVE"},
}

REACHABILITY = {
    "outils": {"reachable": True, "expected": "allowed"},
    "admin": {"reachable": True, "expected": "allowed-for-admin-workers"},
    "exposition": {"reachable": True, "expected": "allowed-for-web-facing-tests"},
    "interdite": {"reachable": False, "expected": "blocked"},
}


class Ticket(BaseModel):
    correlation_id: str
    title: str
    severity: str = "medium"
    payload: Optional[dict] = None


class ChangeRequest(BaseModel):
    correlation_id: str
    title: str
    risk: str = "low"
    payload: Optional[dict] = None


class SccmDeployment(BaseModel):
    collection: str
    package: str
    requested_by: str = "kestra"


class VmRequest(BaseModel):
    name: str
    template: str
    cpu: int = 2
    memory_gb: int = 4


class AdMemberRequest(BaseModel):
    user: str
    reason: str = "POC"


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
    names = list(CMDB_SERVERS.keys())
    return names[:count]


@app.get("/cmdb/servers/{name}")
def cmdb_server(name: str):
    if name not in CMDB_SERVERS:
        raise HTTPException(status_code=404, detail={"message": "server not found", "name": name})
    return CMDB_SERVERS[name]


@app.post("/tickets")
def create_ticket(ticket: Ticket):
    ticket_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    return {"ticket_id": ticket_id, "status": "CREATED", **ticket.model_dump()}


@app.post("/itsm/changes")
def create_change(change: ChangeRequest):
    change_id = f"CHG-{uuid.uuid4().hex[:8].upper()}"
    return {"change_id": change_id, "status": "SCHEDULED", **change.model_dump()}


@app.post("/sccm/deployments")
def create_sccm_deployment(deployment: SccmDeployment):
    deployment_id = f"SCCM-{uuid.uuid4().hex[:8].upper()}"
    return {"deployment_id": deployment_id, "status": "CREATED", **deployment.model_dump()}


@app.post("/aap/job-templates/{template_id}/launch")
def launch_aap_job(template_id: str, payload: dict):
    job_id = f"AAP-{uuid.uuid4().hex[:8].upper()}"
    aap_jobs[job_id] = {"polls": 0, "template_id": template_id, "payload": payload}
    return {"job_id": job_id, "status": "running", "template_id": template_id}


@app.get("/aap/jobs/{job_id}")
def aap_job_status(job_id: str):
    if job_id not in aap_jobs:
        raise HTTPException(status_code=404, detail="unknown job")
    aap_jobs[job_id]["polls"] += 1
    status = "successful" if aap_jobs[job_id]["polls"] >= 1 else "running"
    return {"job_id": job_id, "status": status, "polls": aap_jobs[job_id]["polls"]}


@app.post("/vmware/vms")
def create_vm(vm: VmRequest):
    vm_id = f"VM-{uuid.uuid4().hex[:8].upper()}"
    return {"vm_id": vm_id, "status": "PROVISIONED", **vm.model_dump()}


@app.delete("/vmware/vms/{name}")
def delete_vm(name: str):
    return {"name": name, "status": "DELETED"}


@app.post("/ad/groups/{group}/members")
def add_group_member(group: str, request: AdMemberRequest):
    return {"group": group, "user": request.user, "status": "ADDED", "reason": request.reason}


@app.get("/zones/{zone}/reachability")
def zone_reachability(zone: str):
    if zone not in REACHABILITY:
        raise HTTPException(status_code=404, detail={"message": "unknown zone", "zone": zone})
    status = REACHABILITY[zone]
    if not status["reachable"]:
        raise HTTPException(status_code=403, detail={"zone": zone, **status})
    return {"zone": zone, **status}


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
