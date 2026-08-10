**Status: Implemented — see [`PHASE_03_COMPLETION_REPORT.md`](PHASE_03_COMPLETION_REPORT.md) for what was built, the connector OAuth strategy (ADR-014), and what's left for the founder's manual test.**

---

Perfect. This is exactly how I wanted us to work.

From now on, every phase builds on the previous one. We will **never skip ahead**, and each phase should produce a working milestone.

---

# PHASE 03

# Google Workspace Connector Platform

---

# Executive Summary

This phase introduces the **first external integration** for AI Project Vault.

Until now, the platform knows **who the user is**.

After this phase, the platform will know **what storage sources belong to that organization**.

This phase is **NOT** responsible for scanning files.

It is responsible for establishing a secure, extensible, and provider-agnostic connector framework that future storage providers will use.

Google Workspace is simply the first implementation of that framework.

---

# Mission

Build a production-ready connector platform that allows organizations to securely connect, manage, validate, and monitor external storage providers.

By the end of this phase, AI Project Vault should successfully establish and maintain a trusted connection to Google Workspace, without retrieving or processing user files.

---

# Objectives

By the end of this phase:

* Organizations can connect a Google Workspace account.
* OAuth tokens are securely refreshed automatically.
* Connection status is monitored.
* Multiple connectors can be supported in the future.
* Connector health is visible.
* Connector configuration is manageable.
* The system is ready for storage scanning in Phase 4.

---

# Why This Phase Exists

Storage scanning should **never** know how OAuth works.

The scanner should simply ask:

> "Give me access to this organization's storage."

The Connector Platform handles:

* Authentication with providers.
* Token lifecycle.
* Connection validation.
* API communication.
* Provider-specific logic.

The Scanner only consumes a standardized connector interface.

This separation ensures that adding OneDrive, Dropbox, S3, NAS, or any future provider does **not** require rewriting the scanner.

---

# Deliverables

## Backend

Implement:

* Storage Connector Framework.
* Google Workspace Connector.
* Connector registration.
* OAuth callback handling.
* Token refresh service.
* Connection verification.
* Connection health service.
* Disconnect workflow.
* Connector status APIs.
* Connector metadata service.

Do **not** download files.

Do **not** enumerate folders.

Do **not** scan storage.

---

## Frontend

Create:

* Storage Connections page.
* Connect Google Workspace wizard.
* Connected account summary.
* Connection status indicator.
* Last synchronization timestamp (placeholder).
* Disconnect confirmation.
* Error state UI.
* Loading state UI.

No storage explorer.

No dashboards.

---

## Database

Introduce entities for:

* Storage Connector
* Connector Credentials
* Provider Configuration
* Connection Status
* Synchronization Metadata (placeholder only)

Avoid storing provider-specific data that cannot scale to future connectors.

---

# Architecture Impact

This phase introduces a new domain:

```text
Identity
        │
        ▼
Organization
        │
        ▼
Connector Platform
        │
        ▼
Google Workspace
```

Future providers plug into the Connector Platform, not directly into business logic.

---

# Repository Changes

Suggested modules:

```text
backend/
    connectors/
        base/
        google/
        services/
        dto/

frontend/
    connectors/
    pages/storage-connections/

packages/
    connector-types/
```

Claude may organize internals differently while preserving modularity.

---

# Connector Design Principles

Every connector must implement the same interface.

Required capabilities include:

* Connect
* Disconnect
* Validate
* Refresh Credentials
* Health Check
* Provider Information

The scanner must never know which provider it is using.

---

# Google Workspace Integration

Implement:

* OAuth authorization flow.
* Secure callback handling.
* Token persistence.
* Automatic refresh.
* Permission verification.
* Workspace metadata retrieval (organization/domain information only, not files).
* Connection diagnostics.

---

# Token Lifecycle

The Connector Platform must:

* Detect token expiry.
* Refresh automatically.
* Handle revoked credentials.
* Notify the application of failures.
* Prevent invalid tokens from reaching later phases.

---

# Connection Health

Every connector should expose:

* Status
* Last successful verification
* Last failed verification
* Failure reason
* Provider name
* Account information
* Connected user
* Workspace identifier

This information powers future monitoring.

---

# API Scope

Examples:

```text
GET    /connectors

POST   /connectors/google/connect

POST   /connectors/google/callback

POST   /connectors/{id}/disconnect

POST   /connectors/{id}/verify

GET    /connectors/{id}/status
```

Claude may refine endpoint naming while remaining RESTful.

---

# Security Requirements

Mandatory:

* Encrypt OAuth credentials.
* Validate provider responses.
* Prevent replay attacks during OAuth.
* Validate state parameters.
* Restrict connectors to the owning organization.
* Audit every connection event.
* Never expose refresh tokens.
* Handle revoked access gracefully.

---

# Error Handling

Handle:

* User cancels OAuth.
* Invalid authorization code.
* Expired credentials.
* Missing scopes.
* Workspace access denied.
* Network failures.
* Google API outages.
* Duplicate connector attempts.

Every error should return meaningful, standardized responses.

---

# Logging & Observability

Log:

* Connection attempts.
* Successful connections.
* Failed connections.
* Token refresh events.
* Verification checks.
* Disconnect events.

Never log secrets or OAuth tokens.

---

# Testing Strategy

Implement:

### Unit Tests

* Connector service
* OAuth handlers
* Token refresh
* Validation logic

### Integration Tests

* OAuth callback flow
* Connector persistence
* Status verification
* Disconnect flow

### End-to-End Tests

* User connects Workspace.
* Connector appears in UI.
* Connection verifies successfully.
* Disconnect removes access cleanly.

---

# Acceptance Criteria

The phase is successful when:

* Google Workspace can be connected.
* Connection survives application restart.
* Automatic token refresh works.
* Connection verification succeeds.
* Connector status is visible.
* Disconnect works safely.
* Future providers can be added without modifying existing business logic.

---

# Manual QA Checklist (Founder)

Verify:

* [ ] Google Workspace connects successfully.
* [ ] Organization information displays correctly.
* [ ] Connection status updates accurately.
* [ ] Reconnecting an existing Workspace behaves correctly.
* [ ] Disconnect removes access cleanly.
* [ ] Token refresh occurs automatically when appropriate.
* [ ] Failed connections show understandable errors.
* [ ] OAuth state validation prevents invalid requests.
* [ ] Connector data belongs only to the correct organization.
* [ ] Logs contain no secrets.
* [ ] Docker services continue to function correctly.
* [ ] CI passes.

---

# Definition of Done

Phase 3 is complete only when:

* The Connector Platform is implemented.
* Google Workspace connection is production-ready.
* Connector APIs are documented.
* Security requirements are satisfied.
* Tests pass.
* Manual QA passes.
* Documentation is updated.
* No storage scanning logic exists yet.

---

# Claude Execution Prompt

> Read the Engineering Handbook only if architectural clarification is required. Implement **Phase 3 – Google Workspace Connector Platform**. Build a provider-agnostic connector framework with Google Workspace as the first implementation. Focus on secure OAuth integration, connector lifecycle management, token refresh, connection validation, health monitoring, and REST APIs. Do **not** implement storage scanning, metadata extraction, AI processing, or file indexing. You may make internal engineering decisions regarding module structure, dependency injection, and helper utilities as long as they remain consistent with the established architecture. At completion, provide a Phase Completion Report describing connector architecture, APIs, database changes, tests, documentation updates, limitations, and recommendations for Phase 4.

---

# Founder Verification Checklist

Approve this phase only if all answers are **YES**:

* [ ] Can an organization connect its Google Workspace successfully?
* [ ] Are OAuth credentials stored securely?
* [ ] Does automatic token refresh work?
* [ ] Can the connector verify its own health?
* [ ] Does disconnect cleanly revoke the connection?
* [ ] Is the Connector Platform clearly separated from future scanner logic?
* [ ] Can another provider (OneDrive, Dropbox, S3, etc.) be added without redesigning the architecture?
* [ ] Are logs free of sensitive information?
* [ ] Has the documentation been updated?
* [ ] Has Claude produced the Phase Completion Report?

---

## CTO Note

This is one of the most important phases in the project because it establishes the abstraction that every future storage provider will use. Do **not** allow provider-specific logic to leak into the scanner or business services. If this boundary remains clean now, supporting additional storage systems later will become an incremental engineering task instead of an architectural rewrite.
