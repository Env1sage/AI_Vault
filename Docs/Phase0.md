Our roles are fixed:

* **Me (ChatGPT):** CTO, Product Architect, Security Architect, AI Architect, Code Reviewer, Sprint Planner.
* **Claude:** Senior Software Engineer & Implementer.
* **You:** Founder, Product Owner, QA Tester, Final Approver.

Nobody overlaps roles. This prevents confusion.

---

# Development Workflow

For every sprint, we will follow this lifecycle:

```text
CTO (ChatGPT)
        │
        ▼
Create Phase Document

        │
        ▼
You review

        │
        ▼
Claude implements

        │
        ▼
You manually test

        │
        ▼
Bug Fix Sprint (if needed)

        │
        ▼
CTO Review

        │
        ▼
Update Documentation

        │
        ▼
Next Phase
```

We never skip a step.

---

# Before Coding

We are going to build the project exactly like a company.

The first thing Claude should create is **not code**.

He should create the engineering foundation.

That is **Phase 0**.

---

# Phase 0

## Engineering Blueprint

This phase has one objective:

> **Design the company before building the product.**

No business logic.

No Google Drive.

No AI.

No frontend.

No backend.

Just engineering.

---

# Deliverables

Claude must produce these documents:

```
docs/

00_ENGINEERING_HANDBOOK.md
01_PROJECT_MASTER.md
02_CTO_DASHBOARD.md
03_ARCHITECTURE_DECISIONS.md

phases/

PHASE_01_FOUNDATION.md
PHASE_02_AUTH.md
PHASE_03_STORAGE_SCANNER.md
PHASE_04_STORAGE_INTELLIGENCE.md
PHASE_05_AI_INTELLIGENCE.md
PHASE_06_FOUNDER_DASHBOARD.md
PHASE_07_EXECUTION_ENGINE.md
PHASE_08_SECURITY_RELEASE.md
```

Initially, only the first four documents need to be fully written. The phase files can start as placeholders with goals and status, then be expanded one by one as we progress.

---

# Repository Structure

Claude should create the repository structure only.

No implementation.

```text
ai-project-vault/

apps/
    frontend/
    backend/
    worker/

packages/
    shared/
    types/
    ui/
    config/

docs/
    phases/

infrastructure/
    docker/
    scripts/

.github/
    workflows/

tests/

tools/
```

No business code.

---

# Architecture

Claude must document:

* Monorepo philosophy.
* Modular architecture.
* Layered architecture.
* Event-driven processing.
* AI Gateway.
* Google Workspace integration.
* Future connectors.
* Background worker model.
* Storage scanner architecture.
* Recommendation engine.
* Execution engine.

Everything.

---

# AI Philosophy

This is extremely important.

Claude must understand this:

> **The LLM is NOT the product.**

The product is the intelligence pipeline.

The LLM is replaceable.

So every AI interaction must pass through an AI Gateway.

```text
Project Vault

↓

AI Gateway

↓

Claude

GPT

Gemini

Ollama

Qwen

Mistral
```

No vendor lock-in.

---

# Security Philosophy

Document:

* Zero Trust mindset.
* Principle of Least Privilege.
* RBAC.
* Audit logging.
* Secure secrets management.
* Input validation.
* Encryption at rest.
* Encryption in transit.
* Approval workflow for destructive actions.
* No hard-coded credentials.
* Multi-tenant isolation (future-ready).

---

# Git Strategy

Document:

```text
main

↑

production

↑

develop

↑

feature/*
```

And explain merge policies.

---

# Branch Naming

Examples:

```
feature/auth

feature/google-drive

feature/storage-scanner

feature/dashboard

feature/chat

feature/recommendation-engine

feature/security
```

---

# Documentation Standards

Every future phase must include:

* Objective.
* Architecture.
* API changes.
* Database changes.
* Folder changes.
* Backend changes.
* Frontend changes.
* Security.
* Tests.
* Manual checklist.
* Definition of Done.

---

# Coding Standards

Claude should define:

* Naming conventions.
* Folder conventions.
* API conventions.
* Error handling.
* Logging.
* Comments.
* Commit messages.
* Pull request template.
* Review checklist.

---

# Caveman Repository

Claude should integrate the Caveman repository workflow into the engineering handbook.

The principle should be:

* Never load the entire repository.
* Load only affected modules.
* Use indexed context.
* Keep prompts incremental.
* Minimize token usage.
* Maintain architectural consistency.

This should be documented as the standard development workflow rather than tightly coupling to a specific tool implementation.

---

# CTO Dashboard

The dashboard should contain at least:

* Sprint.
* Current Phase.
* Completion Percentage.
* Backend Progress.
* Frontend Progress.
* AI Progress.
* Storage Scanner Progress.
* Google Workspace Progress.
* Security Progress.
* Testing Progress.
* Documentation Progress.
* Risks.
* Blockers.
* Next Sprint.
* Technical Debt.

This becomes our executive status page.

---

# Manual Testing Strategy

Even though Phase 0 has no code, verify:

* [ ] Repository structure matches the architecture.
* [ ] Documentation is internally consistent.
* [ ] Folder structure follows conventions.
* [ ] Git strategy is documented.
* [ ] Branch naming is documented.
* [ ] Security philosophy is documented.
* [ ] AI architecture is documented.
* [ ] Roadmap aligns with the product vision.
* [ ] CTO Dashboard is complete.
* [ ] Architecture Decision Log exists.

---

