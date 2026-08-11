import uuid
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel


class PipelineReport(BaseModel):
    pipeline_id: str
    quality_gate: str
    flow: Optional[str] = None
    execution: Optional[str] = None


class ReleaseEvent(BaseModel):
    application: str
    version: str
    environment: str = "dev"
    approved: Optional[bool] = None
    operation: str = "deploy"
    previous_version: Optional[str] = None
    reason: Optional[str] = None
    execution: Optional[str] = None


class RbacCheck(BaseModel):
    profile: str
    action: str
    execution: Optional[str] = None


class ServiceAccountCheck(BaseModel):
    service_account: str
    operation: str
    execution: Optional[str] = None


class AuditEvent(BaseModel):
    actor: str
    action: str
    target: str
    execution: Optional[str] = None
    source: str = "kestra-poc"


class TenantCheck(BaseModel):
    tenant: str
    namespace: str
    execution: Optional[str] = None


class WorkerGroupCheck(BaseModel):
    zone: str
    os: str
    execution: Optional[str] = None


def register_governance_routes(app: FastAPI) -> None:
    @app.post("/governance/pipelines")
    def record_pipeline(report: PipelineReport):
        decision = "ALLOWED" if report.quality_gate == "pass" else "DENIED"
        return {"pipeline_event_id": f"PIPEVT-{uuid.uuid4().hex[:8].upper()}", "decision": decision, **report.model_dump()}

    @app.post("/governance/releases")
    def record_release(event: ReleaseEvent):
        return {"release_event_id": f"REL-{uuid.uuid4().hex[:8].upper()}", "status": "RECORDED", **event.model_dump()}

    @app.post("/governance/rbac/check")
    def rbac_check(check: RbacCheck):
        admin_actions = {"manage_rbac", "view_audit"}
        allowed = check.profile == "admin" or check.action not in admin_actions
        return {"decision": "ALLOWED" if allowed else "DENIED", "reason": "admin action requires admin profile" if not allowed else "profile authorized", **check.model_dump()}

    @app.post("/governance/service-accounts/check")
    def service_account_check(check: ServiceAccountCheck):
        allowed_operations = {"deploy_flow"}
        allowed = check.service_account == "svc-kestra-cicd" and check.operation in allowed_operations
        return {"decision": "ALLOWED" if allowed else "DENIED", "reason": "operation outside CI/CD service account perimeter" if not allowed else "operation authorized", **check.model_dump()}

    @app.post("/governance/audit")
    def audit_event(event: AuditEvent):
        return {"audit_id": f"AUD-{uuid.uuid4().hex[:8].upper()}", "status": "RECORDED", **event.model_dump()}

    @app.post("/governance/tenants/check")
    def tenant_check(check: TenantCheck):
        allowed = check.tenant == "admin" or check.namespace.startswith(f"poc.kestra.{check.tenant}")
        return {"decision": "ALLOWED" if allowed else "DENIED", "reason": "tenant namespace mismatch" if not allowed else "tenant namespace authorized", **check.model_dump()}

    @app.post("/governance/worker-groups/check")
    def worker_group_check(check: WorkerGroupCheck):
        worker_group = f"{check.os}-{check.zone}"
        return {"decision": "ALLOWED", "worker_group": worker_group, "zone": check.zone, "os": check.os, "execution": check.execution}
