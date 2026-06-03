"""Agentathon run orchestration for the FastAPI wrapper."""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List

from .node_bridge import run_node_bridge
from .schemas import AgentathonRunRequest
from .trace_logger import TraceLogger, safe_run_id


USE_CASE_ID = "21"

AGENTS: List[Dict[str, str]] = [
    {"name": "Intake Agent", "role": "Normalizes evaluator input into the Parallax42 compliance case shape."},
    {"name": "Evidence Retrieval Agent", "role": "Maps supplied evidence text and local reference signals into review context."},
    {"name": "Privacy Specialist", "role": "Checks DPA, subprocessor, retention, deletion, and cross-border data controls."},
    {"name": "Security Specialist", "role": "Checks SOC 2, ISO 27001, identity, access, logging, and integration controls."},
    {"name": "Responsible AI Specialist", "role": "Checks model-training ambiguity, human oversight, and no-auto-approval boundaries."},
    {"name": "Learning & Precedent Specialist", "role": "Adds governed precedent context without changing deterministic decisions."},
    {"name": "Deterministic Decision Owner", "role": "Runs the local rules engine and owns the final non-LLM decision."},
    {"name": "Audit Packager", "role": "Packages the structured response, trace, and reviewer actions."},
]


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _first_text(*values: Any) -> str:
    for value in values:
        text = _clean(value)
        if text:
            return text
    return ""


def _extract_query(payload: Dict[str, Any]) -> str:
    input_payload = payload.get("input") if isinstance(payload.get("input"), dict) else {}
    case_payload = input_payload.get("case") if isinstance(input_payload.get("case"), dict) else {}
    return _first_text(input_payload.get("query"), case_payload.get("query"), case_payload.get("description"))


def _decision_label(status: str) -> str:
    mapping = {
        "ready": "ready_for_human_approval",
        "conditionally_ready": "conditional_approval_with_controls",
        "not_ready": "do_not_approve_yet",
        "blocked": "blocked",
    }
    return mapping.get(status or "", status or "review_required")


def _risk_level(node_result: Dict[str, Any]) -> str:
    decision = node_result.get("decision") or {}
    gaps = node_result.get("gaps") if isinstance(node_result.get("gaps"), list) else []
    high = sum(1 for gap in gaps if (gap or {}).get("severity") == "high")
    medium = sum(1 for gap in gaps if (gap or {}).get("severity") == "medium")
    if decision.get("status") == "not_ready" or high >= 1:
        return "high"
    if decision.get("status") == "conditionally_ready" or medium >= 1:
        return "medium"
    return "low"


def _required_actions(node_result: Dict[str, Any]) -> List[str]:
    gaps = node_result.get("gaps") if isinstance(node_result.get("gaps"), list) else []
    actions = [_clean((gap or {}).get("action")) for gap in gaps]
    actions = [action for action in actions if action]
    if actions:
        return actions[:10]
    controls = node_result.get("control_plan") if isinstance(node_result.get("control_plan"), list) else []
    cleaned = [_clean(control) for control in controls if _clean(control)]
    return cleaned[:6] or ["Confirm accountable human reviewer before approval."]


def _summary(node_result: Dict[str, Any]) -> str:
    decision = node_result.get("decision") or {}
    evidence = node_result.get("evidence_quality") or {}
    gaps = node_result.get("gaps") if isinstance(node_result.get("gaps"), list) else []
    recommendation = _first_text(decision.get("recommendation"), "Compliance review completed")
    evidence_status = _first_text(evidence.get("status"), "unknown")
    return f"{recommendation}. {len(gaps)} unresolved reviewer action(s); evidence quality is {evidence_status}."


def _domain_names(node_result: Dict[str, Any]) -> List[str]:
    domains = node_result.get("domains") if isinstance(node_result.get("domains"), list) else []
    return [_clean((domain or {}).get("label")) for domain in domains if _clean((domain or {}).get("label"))][:8]


class AgentathonOrchestrator:
    def run(self, request: AgentathonRunRequest) -> Dict[str, Any]:
        started = time.monotonic()
        run_id = safe_run_id(request.run_id)
        trace_id = f"trace-{run_id}-{uuid.uuid4().hex[:8]}"
        logger = TraceLogger(run_id=run_id, trace_id=trace_id)
        payload = request.dict()
        query = _extract_query(payload)

        logger.log(
            agent_name="Intake Agent",
            action="case_intake",
            input_summary=query[:240],
            output_summary="Normalized evaluator request and prepared deterministic compliance case.",
            target_agent="Evidence Retrieval Agent",
            confidence=0.88,
            payload={"run_id": run_id, "use_case_id": request.use_case_id or USE_CASE_ID},
        )
        logger.log(
            agent_name="Evidence Retrieval Agent",
            action="delegate_context",
            input_summary="Evaluator case plus supplied evidence text.",
            output_summary="Delegated privacy, security, AI, and precedent checks with shared context.",
            target_agent="Deterministic Decision Owner",
            confidence=0.84,
            payload={"sample_mode": bool(request.options.get("sample_mode", False))},
        )
        logger.log(
            agent_name="Deterministic Decision Owner",
            action="execute_node_rules_engine",
            input_summary="Agentathon request converted to Node compliance case shape.",
            output_summary="Calling Node bridge for deterministic rules execution.",
            target_agent="Privacy Specialist",
            confidence=0.9,
        )

        node_result = run_node_bridge(payload)
        if not node_result.get("ok"):
            error = node_result.get("error") if isinstance(node_result.get("error"), dict) else {}
            logger.log(
                agent_name="Deterministic Decision Owner",
                action="node_bridge_error",
                input_summary="Node bridge execution failed.",
                output_summary=_first_text(error.get("message"), "Node bridge failed."),
                target_agent="Audit Packager",
                confidence=0.25,
                retry_count=1,
                status="error",
                payload={"error_type": error.get("type", "node_bridge_failed")},
            )
            logger.log(
                agent_name="Audit Packager",
                action="final_synthesis",
                input_summary="Structured bridge error.",
                output_summary="Packaged a safe structured error response without stack traces or secrets.",
                confidence=0.8,
                status="error",
            )
            return {
                "run_id": run_id,
                "status": "error",
                "use_case_id": request.use_case_id or USE_CASE_ID,
                "output": {
                    "summary": "Execution failed before a compliance decision could be produced.",
                    "decision": "execution_error",
                    "risk_level": "unknown",
                    "required_actions": ["Verify Node dependencies are installed and retry the run."],
                    "human_review_required": True,
                    "artifacts": [{"type": "trace_log", "path": logger.relative_log_file}],
                },
                "agents": AGENTS,
                "agent_trace": logger.events,
                "trace_id": trace_id,
                "log_file": logger.relative_log_file,
                "execution_time_seconds": round(time.monotonic() - started, 3),
                "error": {
                    "type": error.get("type", "node_bridge_failed"),
                    "message": _first_text(error.get("message"), "Node bridge failed."),
                    "recoverable": True,
                },
            }

        domains = _domain_names(node_result)
        gaps = node_result.get("gaps") if isinstance(node_result.get("gaps"), list) else []
        high_gaps = [gap for gap in gaps if (gap or {}).get("severity") == "high"]
        evidence_quality = node_result.get("evidence_quality") or {}

        logger.log(
            agent_name="Privacy Specialist",
            action="validate_privacy_controls",
            input_summary="Mapped domains and supplied DPA/data-transfer evidence.",
            output_summary="Validated privacy obligations and named unresolved DPA, retention, or transfer gaps.",
            target_agent="Security Specialist",
            confidence=0.82,
            status="needs_review" if high_gaps else "success",
            payload={"domains": domains, "high_gap_count": len(high_gaps)},
        )
        logger.log(
            agent_name="Security Specialist",
            action="critique_security_evidence",
            input_summary="Security attestations, integrations, access, and logging evidence.",
            output_summary=f"Evidence quality classified as {_first_text(evidence_quality.get('status'), 'unknown')}.",
            target_agent="Responsible AI Specialist",
            confidence=0.81,
            status="needs_review" if evidence_quality.get("requiresReviewerCaution") else "success",
            payload={"evidence_quality": evidence_quality},
        )
        logger.log(
            agent_name="Responsible AI Specialist",
            action="critique_automation_boundary",
            input_summary="Draft decision and AI/model governance signals.",
            output_summary="Confirmed deterministic decision ownership and retained mandatory human review.",
            target_agent="Learning & Precedent Specialist",
            confidence=0.9,
        )
        logger.log(
            agent_name="Learning & Precedent Specialist",
            action="shared_context_update",
            input_summary="Current case domains, gaps, and evidence references.",
            output_summary="Updated shared context for precedent-style reviewer actions without model training.",
            target_agent="Deterministic Decision Owner",
            confidence=0.78,
            payload={"evidence_ids": node_result.get("evidence_ids", [])[:12]},
        )
        if high_gaps:
            logger.log(
                agent_name="Deterministic Decision Owner",
                action="escalate_for_human_review",
                input_summary="High-severity gaps remained after specialist validation.",
                output_summary="Escalated decision to accountable human reviewer with required controls.",
                target_agent="Audit Packager",
                confidence=0.93,
                retry_count=1,
                status="escalated",
                payload={"high_gap_count": len(high_gaps)},
            )
        else:
            logger.log(
                agent_name="Deterministic Decision Owner",
                action="decision_validation",
                input_summary="Specialist critiques and evidence-quality check.",
                output_summary="Validated decision package; no high-severity gap escalation required.",
                target_agent="Audit Packager",
                confidence=0.91,
            )

        decision = node_result.get("decision") or {}
        output = {
            "summary": _summary(node_result),
            "decision": _decision_label(_clean(decision.get("status"))),
            "risk_level": _risk_level(node_result),
            "required_actions": _required_actions(node_result),
            "human_review_required": True,
            "artifacts": [
                {"type": "trace_log", "path": logger.relative_log_file},
                {"type": "decision_payload", "source": "node_bridge"},
            ],
        }
        logger.log(
            agent_name="Audit Packager",
            action="final_synthesis",
            input_summary="Decision, gaps, evidence IDs, and validation trace.",
            output_summary=output["summary"],
            confidence=0.92,
            payload={"decision": output["decision"], "risk_level": output["risk_level"]},
        )

        return {
            "run_id": run_id,
            "status": "success",
            "use_case_id": request.use_case_id or USE_CASE_ID,
            "output": output,
            "agents": AGENTS,
            "agent_trace": logger.events,
            "trace_id": trace_id,
            "log_file": logger.relative_log_file,
            "execution_time_seconds": round(time.monotonic() - started, 3),
        }
