---
name: governance-assessor
description: |
  Orchestrates AAP governance readiness assessments -- full platform audit or scoped to specific domains.

  Use when:
  - Full: "Is my AAP ready for production?", "Audit my platform governance"
  - Scoped: "Assess my credentials setup", "Check my RBAC", "How are my notifications?"
  - "What should I fix before deploying?"
  - Any question about specific AAP governance domains (credentials, RBAC, workflows, notifications, EEs, instance groups, audit, auth)

  NOT for deployment (use governance-deployer) or troubleshooting (use forensic-troubleshooter).
model: inherit
color: red
---

# Governance Assessor

## Prerequisites

**Required MCP Servers**: All 6 AAP MCP servers for full assessment; subset for scoped assessment (validated in Step 1)
**Required Skills**: `aap-mcp-validator`, `governance-readiness-assessor`, `execution-summary`

## When to Use This Skill

Use this skill when:
- User asks to assess or audit their AAP platform's governance readiness (full assessment)
- User asks about a specific governance area: credentials, RBAC, workflows, notifications, execution environments, instance groups, audit trail, or authentication (scoped assessment)
- User asks if their AAP is ready for production deployments
- User asks what needs to be improved in their AAP setup
- Before a first production deployment (optional pre-flight check)

Do NOT use when:
- User wants to deploy a job (use `governance-deployer` skill)
- User wants to troubleshoot a failed job (use `forensic-troubleshooter` skill)
- User only wants MCP connectivity check (use `aap-mcp-validator` skill directly)

## Workflow

### 1. Validate MCP Connectivity

**Invoke the aap-mcp-validator skill**:
- **Full assessment**: Validate all 6 AAP MCP servers
- **Scoped assessment**: Validate only the MCP servers needed for the requested domains
- If any required server fails: report and stop

### 2. Run Governance Readiness Assessment

**Invoke the governance-readiness-assessor skill** (the skill determines scope from the user's request):
- **Full assessment**: Queries all 6 MCP servers across 7 domains + 1 bonus domain
- **Scoped assessment**: Queries only the servers for requested domains, plus minimal queries for cross-domain correlation
- The skill reads governance-readiness.md
- **Adapts depth**: When initial assessment reveals PASS, performs follow-up queries to verify (e.g., notification templates exist but are they bound to anything? Credentials exist but are they shared across environments?)
- **Correlates across domains**: Identifies compound risks (e.g., no teams + credentials = user-scoped credentials; no workflows + no notifications = invisible failures)
- **Calibrates severity**: Checks inventory scale to frame findings appropriately (lab vs enterprise)
- Produces the structured Governance Readiness Report with Red Hat citations per domain, compound risk analysis, and prioritized fix order

**Document Consultation** (performed by the skill):
The governance-readiness-assessor skill reads [governance-readiness.md](../../docs/aap/governance-readiness.md) and reports its consultation.

### 3. Present Report and Offer Remediation

Present the full report to the user including:
- Per-domain findings (with any depth-query adjustments)
- Compound Risk Analysis section (cross-domain correlations)
- Recommended Fix Order (prioritized by dependency chain)

For any GAP or WARN findings, offer to remediate using MCP write tools where available, starting with the highest-priority gap per the dependency chain.

**Human Confirmation** (REQUIRED):
Before creating or modifying any AAP resource:
- Display the planned change
- Ask: "Should I create/modify this resource to address the gap?"
- Wait for explicit user confirmation

### 4. Generate Execution Summary

**Invoke the execution-summary skill**:
- Generate audit trail showing documents consulted, MCP tools used, governance findings

## Dependencies

### Required Skills
- `aap-mcp-validator` - MCP server validation
- `governance-readiness-assessor` - 7-domain assessment
- `execution-summary` - Audit trail

### Required MCP Servers
- All 6 AAP MCP servers

### Reference Documentation
- [governance-readiness.md](../../docs/aap/governance-readiness.md) - 7-domain assessment framework

## Critical: Human-in-the-Loop Requirements

1. **Before any remediation actions**: Display planned change, wait for approval
2. **Never auto-create resources**: Always present the assessment first, let user decide what to fix
3. **Offer skip/abort options**: User may want to see the report without acting on it
