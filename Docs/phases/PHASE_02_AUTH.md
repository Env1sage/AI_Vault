**Status: Implemented — see [`PHASE_02_COMPLETION_REPORT.md`](PHASE_02_COMPLETION_REPORT.md) for what was built, the session/auth strategy (ADR-013), and what's left for the founder's manual test.**

---

Perfect. Now we're switching from **architecture** to **implementation**.

I also want to make one correction to our roadmap before we start.

## Roadmap Adjustment

Originally we had:

* Phase 1 → Foundation
* Phase 2 → Authentication
* Phase 3 → Scanner

After reviewing the product again, I think there's a better engineering order.

```
Phase 0 → Engineering Blueprint ✅

Phase 1 → Engineering Foundation ✅

Phase 2 → Identity & Organization Platform

Phase 3 → Google Workspace Connector

Phase 4 → Storage Scanner

Phase 5 → Metadata & Knowledge Engine

Phase 6 → AI Intelligence Engine

Phase 7 → Founder Dashboard

Phase 8 → Execution Engine

Phase 9 → Security, Performance & Release
```

This separation makes each phase smaller, easier to test, and cheaper for Claude to implement.

---

# PHASE 02

# Identity & Organization Platform

---

# Executive Summary

This phase establishes the **identity layer** of AI Project Vault.

Before the platform can understand files, it must understand **who owns them**.

The outcome of this phase is that an organization can securely authenticate, create its workspace inside AI Project Vault, manage users and roles, and prepare for Google Workspace integration.

**No Google Drive APIs are implemented in this phase.** Authentication and organization management only.

---

# Objectives

By the end of this phase:

* Users can sign in securely with Google.
* Organizations are created and managed.
* Roles and permissions exist.
* Sessions are secure.
* APIs are protected.
* The frontend has authenticated routes.
* The platform is ready for Google Workspace connection in Phase 3.

---

# Deliverables

### Backend

Implement:

* Google OAuth 2.0 login
* JWT access tokens
* Refresh token flow
* Session management
* Logout
* User profile API
* Organization CRUD (basic)
* RBAC middleware
* Authentication middleware

Do **not** implement storage features.

---

### Frontend

Create:

* Login page
* Authentication callback
* Dashboard shell
* User profile page
* Organization settings page
* Unauthorized page
* Loading and session recovery

No business dashboard yet.

---

### Database

Create only the entities required for identity:

* Organization
* User
* Role
* UserRole (if your model requires it)
* Session / Refresh Token
* Audit Log (authentication events)

Keep the schema extensible for future multi-tenant growth.

---

# Architecture Impact

This phase introduces the Identity domain.

It becomes the entry point for every future request.

Every future API must receive:

* Authenticated user
* Organization context
* Role context

No endpoint created after this phase should bypass the authentication middleware.

---

# Repository Changes

Expected new modules:

```
backend/
    auth/
    users/
    organizations/
    roles/

frontend/
    auth/
    profile/
    organization/

packages/
    auth-types/
```

Claude may adjust internal structure if it remains consistent with the Engineering Handbook.

---

# Implementation Notes

Claude is free to make implementation decisions regarding:

* Folder organization inside modules
* Service decomposition
* Dependency Injection
* Validation strategy
* Repository pattern (if appropriate)

Claude **must not** change:

* Authentication architecture
* RBAC philosophy
* Token strategy
* Security model
* API conventions

---

# Security Requirements

Mandatory:

* Encrypt sensitive tokens before persistence.
* Never log OAuth credentials.
* Validate every JWT.
* Protect all authenticated routes.
* Implement role guards.
* Apply rate limiting to authentication endpoints.
* Validate all incoming payloads.
* Use secure cookie settings if cookies are used.
* Use HTTPS-ready configuration.

---

# API Scope

Minimum endpoints:

```
POST   /auth/login
POST   /auth/logout
POST   /auth/refresh

GET    /users/me

GET    /organizations/current
PATCH  /organizations/current
```

Additional endpoints may be added if they improve maintainability without changing the architecture.

---

# Acceptance Criteria

The phase is considered successful when:

* A new user can authenticate with Google.
* A user record is created or updated.
* An organization exists.
* JWT authentication works.
* Refresh tokens work.
* Protected routes reject unauthenticated users.
* Role guards function correctly.
* User profile information is returned correctly.
* Organization information is returned correctly.

---

# Manual QA Checklist (Founder)

Verify:

* [ ] Google login succeeds.
* [ ] Returning users are recognized correctly.
* [ ] New users are provisioned correctly.
* [ ] JWT expires as configured.
* [ ] Refresh token renews the session.
* [ ] Logout invalidates access.
* [ ] Protected routes reject anonymous requests.
* [ ] User profile displays correctly.
* [ ] Organization settings load.
* [ ] No authentication errors appear in logs.
* [ ] Tokens are never exposed in responses or logs.
* [ ] Docker environment still starts cleanly.
* [ ] CI passes.

---

# Definition of Done

Do not mark this phase complete unless:

* All deliverables are implemented.
* Authentication is production-ready.
* Security requirements are satisfied.
* Tests pass.
* Manual QA passes.
* Documentation is updated.
* No architectural changes were introduced without an ADR.

---

# Claude Execution Prompt

> 


---

# Founder Verification Checklist

Before approving this phase, answer **YES** to all of these:

* [ ] Can a new user sign in successfully?
* [ ] Can an existing user sign back in without duplicate records?
* [ ] Does every authenticated API require a valid session?
* [ ] Are roles enforced correctly?
* [ ] Are authentication failures handled cleanly?
* [ ] Are sensitive values absent from logs?
* [ ] Does the UI recover gracefully after a page refresh?
* [ ] Is the code modular and aligned with the Engineering Handbook?
* [ ] Have `PROJECT_MASTER.md`, `CTO_DASHBOARD.md`, and any required ADRs been updated?
* [ ] Has Claude produced a Phase Completion Report?

---

## CTO Note

One final recommendation for all future phases: **each phase should fit into a single Git feature branch** (for example, `feature/identity-platform`). That keeps pull requests focused, makes code reviews easier, and allows us to revert or refine a phase without affecting unrelated work. This discipline will pay off as the project grows.
