# Benchmark Report

## Baseline Evidence Already Available

Parallax42 deterministic golden-case evals passed:

```text
20/20 cases passed
100% pass rate
15/15 checks per case
```

Covered case themes include:

- high-risk AI SaaS missing DPA
- model-training exclusion gaps
- SOW continuity and exit gaps
- MSA liability and audit-rights gaps
- low-risk SaaS with no PII
- cross-border transfer uncertainty
- strong DPA/SOW evidence
- ambiguous contract type
- applicability decisions for AI, privacy, continuity, and low-criticality cases

## This Repo Baseline

Current checks cover:

- empty-case blocking
- AI/privacy/continuity/third-party detection
- ready or conditionally ready decision behavior
- online product health/Qdrant proof through Vercel product APIs
- Agentathon wrapper shape through `scripts/agentathon_preflight.py`
- Docker `/health` and `/run` smoke through GitHub Actions
- multi-agent traces with delegation, retry/fallback, critique, validation, escalation, and deterministic final ownership

Run:

```bash
npm run qa
npm run capture:evidence
python scripts/agentathon_preflight.py
python scripts/agentathon_preflight.py --run-api
```

Generated benchmark output is written to `evidence/benchmark-report.json`.

## Missing Before Submission

- Broader latency report for `POST /api/agent/run` across local and Vercel API surfaces.
- Live Parallax42 backend latency and fallback-rate report.
- Upload/OCR throughput report.
- Responsible AI test suite against prompt injection, unsupported approval language, bias-sensitive assumptions, and data minimization.
- Reliability run showing repeated executions with trace and decision consistency.
- Demo video still needs to be recorded and linked.
- Direct Compass strict verification requires valid Compass credentials; product Compass usage remains server-side through the hosted gateway/API boundary.

## Target Acceptance Threshold

Before submitting, the package should show:

- at least 95% pass rate on deterministic golden cases
- zero unsupported automatic approval outputs
- p95 local deterministic run latency under 500 ms
- p95 live backend no-upload run latency under an agreed operational threshold
- clear fallback labeling whenever live AI is unavailable
- no claim of enforced RBAC, enterprise-durable audit, arbitrary scanned-PDF OCR, or live CrewAI unless separate checks pass
