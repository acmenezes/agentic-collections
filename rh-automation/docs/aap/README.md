# AAP Documentation

Platform governance, deployment, and troubleshooting references for Ansible Automation Platform.

## Documents

| Document | Purpose | Use Case |
|----------|---------|----------|
| [governance-readiness.md](governance-readiness.md) | 7-domain platform governance assessment against Red Hat best practices | UC1: Governance Assessment |
| [deployment-governance.md](deployment-governance.md) | Risk classification, check mode, rollback, phased rollout | UC2: Governed Deployment |
| [job-troubleshooting.md](job-troubleshooting.md) | Event parsing, host correlation, failure patterns | UC3: Forensic Troubleshooting |

## How to Use

These documents are read by skills at runtime. The skill reads the document FIRST, then queries MCP tools, then interprets results using the document's decision tables and Red Hat citations.

```
Skill reads document → Queries MCP → Interprets with Red Hat knowledge → Reports with citations
```
