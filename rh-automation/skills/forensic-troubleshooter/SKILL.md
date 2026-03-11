---
name: forensic-troubleshooter
description: |
  Orchestrates forensic analysis of failed jobs with event extraction, host correlation, and resolution advisory.

  Use when:
  - "Job #X failed", "Why did the deployment fail?"
  - "Analyze the failure", "What went wrong?"
  - "Root cause analysis of job #X"

  NOT for deployment (use governance-deployer) or platform assessment (use governance-assessor).
model: inherit
color: yellow
---

# Forensic Troubleshooter

## Prerequisites

**Required MCP Servers**: `aap-mcp-job-management`, `aap-mcp-inventory-management`
**Required Skills**: `aap-mcp-validator`, `job-failure-analyzer`, `host-fact-inspector`, `resolution-advisor`, `execution-summary`

## When to Use This Skill

Use this skill when:
- User reports a failed job and wants to understand why
- User asks for root cause analysis of a job failure
- User asks to analyze job errors or failure events
- After a governed deployment fails (follow-up from governance-deployer)

Do NOT use when:
- User wants to deploy (use `governance-deployer` skill)
- User wants to assess platform readiness (use `governance-assessor` skill)
- User wants to check host facts without a failure context (use `host-fact-inspector` skill directly)

## Workflow

### 1. Validate MCP Connectivity

**Invoke the aap-mcp-validator skill**:
- Validate `aap-mcp-job-management` and `aap-mcp-inventory-management`
- If any server fails: report and stop

### 2. Analyze Job Failure

**Invoke the job-failure-analyzer skill**:
- The skill reads job-troubleshooting.md
- Retrieves job status, extracts failure events, analyzes host summaries
- Classifies the failure (Platform / Code / Configuration)
- Reconstructs failure timeline
- Reports structured analysis with Red Hat citations

**Document Consultation** (performed by the skill):
The job-failure-analyzer skill reads [job-troubleshooting.md](../../docs/aap/job-troubleshooting.md) and reports its consultation.

### 3. Correlate with Host Facts

**Invoke the host-fact-inspector skill**:
- The skill reads job-troubleshooting.md
- Looks up affected hosts from the failure analysis
- Retrieves host variables/facts
- Correlates errors with host system state
- Reports correlation findings

**Document Consultation** (performed by the skill):
The host-fact-inspector skill reads [job-troubleshooting.md](../../docs/aap/job-troubleshooting.md) for correlation patterns.

### 4. Provide Resolution Advisory

**Invoke the resolution-advisor skill**:
- The skill reads error-classification.md and job-troubleshooting.md
- Determines the resolution path based on error classification and host correlation
- Provides Red Hat documentation-backed resolution steps
- Identifies related governance gaps

**Document Consultation** (performed by the skill):
The resolution-advisor skill reads [error-classification.md](../../docs/references/error-classification.md) and [job-troubleshooting.md](../../docs/aap/job-troubleshooting.md).

### 5. Generate Execution Summary

**Invoke the execution-summary skill**:
- Generate audit trail showing: documents consulted, failure classification basis, host correlations, resolution recommendations

## Dependencies

### Required Skills
- `aap-mcp-validator` - MCP server validation
- `job-failure-analyzer` - Event extraction and classification
- `host-fact-inspector` - Host fact correlation
- `resolution-advisor` - Resolution recommendations
- `execution-summary` - Audit trail

### Required MCP Servers
- `aap-mcp-job-management` - Job events and host summaries
- `aap-mcp-inventory-management` - Host facts for correlation

### Reference Documentation
- [job-troubleshooting.md](../../docs/aap/job-troubleshooting.md) - Event parsing, failure patterns, correlation
- [error-classification.md](../../docs/references/error-classification.md) - Error taxonomy and resolution paths
