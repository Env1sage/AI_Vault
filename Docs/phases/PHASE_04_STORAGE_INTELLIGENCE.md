Thank you. I think we've found a workflow that will scale well. One thing I want to keep emphasizing is that **we're not writing prompts—we're writing the engineering playbook for a product that should still make sense two years from now.**

Now we're entering what I consider the **heart of Project Vault**.

Everything before this phase has been preparation.

This is where the product actually starts understanding customer data.

---

# PHASE 04

# Storage Discovery & Scanner Engine

---

# Executive Summary

This phase introduces the **Storage Scanner**, the first core intelligence component of AI Project Vault.

Until now, the platform could:

* Authenticate users
* Manage organizations
* Connect Google Workspace

After this phase, the platform will be able to **discover and index an organization's storage**.

This phase is intentionally **read-only**.

The scanner must never modify user data.

Its only responsibility is to build an accurate inventory of the connected storage.

This inventory becomes the foundation for every future capability:

* AI analysis
* Search
* Duplicate detection
* Knowledge graph
* Recommendations
* Dashboard analytics
* Execution Engine

If the scanner is inaccurate, every downstream feature becomes unreliable. Therefore, correctness, resumability, and observability are the priorities for this phase.

---

# Mission

Build a scalable, fault-tolerant Storage Scanner capable of discovering and indexing organizational storage while remaining completely provider-agnostic.

The scanner should treat Google Drive as the first connector implementation, but its internal logic must never depend on Google-specific APIs.

---

# Objectives

By the end of this phase:

* An organization can initiate a storage scan.
* The scanner traverses the connected storage hierarchy.
* Files and folders are indexed into the database.
* File metadata is normalized into a common model.
* Incremental scan support is designed (full implementation may be partial depending on provider capabilities).
* Scan jobs can pause, retry, and resume.
* Scan progress is visible to users.
* No file contents are downloaded yet unless absolutely required for metadata extraction.

---

# Deliverables

### Scanner Engine

Implement:

* Storage traversal service.
* Queue-based scan execution.
* Folder hierarchy discovery.
* File discovery.
* Metadata normalization.
* Progress tracking.
* Scan cancellation.
* Scan retry mechanism.
* Scan resume support.
* Incremental scan architecture.
* Initial change-token strategy (where provider supports it).

---

### Metadata Collection

For every discovered object, collect standardized metadata where available:

* File ID
* Provider ID
* Name
* Parent folder
* Full path
* File type / MIME type
* Size
* Created timestamp
* Modified timestamp
* Last viewed timestamp
* Owner
* Shared status
* Permissions summary
* Version identifier
* Checksum / hash if available from the provider
* Scan timestamp

Do **not** download full file contents in this phase.

---

### Folder Structure

The scanner should reconstruct:

* Root drives
* Shared drives
* Nested folders
* Parent-child relationships

The database should represent the storage hierarchy independently of the provider.

---

### Worker Responsibilities

The Worker service becomes the execution engine for scan jobs.

Responsibilities include:

* Creating scan tasks.
* Processing scan queues.
* Reporting progress.
* Handling retries.
* Recovering interrupted scans.
* Recording failures.

Workers must remain stateless so they can scale horizontally.

---

### Frontend Deliverables

Create:

* Scan dashboard.
* Scan progress indicator.
* Current scan status.
* Last successful scan.
* Scan history (basic).
* Retry button.
* Cancel scan action.
* Empty state for first-time users.

No AI insights or analytics are shown yet.

---

### Database Deliverables

Introduce normalized entities such as:

* StorageSource
* Folder
* File
* ScanJob
* ScanEvent
* ScanProgress

Design them around provider-neutral identifiers and relationships so additional connectors can reuse them.

---

# Architecture Impact

The scanner sits between the Connector Platform and every downstream intelligence service.

```text
Google Workspace Connector
            │
            ▼
      Storage Scanner
            │
            ▼
     Metadata Database
            │
            ▼
 Future Intelligence Engine
```

No downstream module should communicate directly with Google Drive.

---

# Implementation Notes

Claude has flexibility regarding:

* Queue implementation details.
* Traversal algorithm.
* Pagination handling.
* Internal batching strategy.
* Retry strategy.
* Memory optimization.

Claude **must not** change:

* Provider abstraction.
* Read-only behavior.
* Metadata normalization model.
* Worker architecture.

---

# Performance Requirements

The scanner should be designed for scale from day one.

Engineering goals:

* Support organizations with large storage footprints.
* Stream processing instead of loading everything into memory.
* Batch database writes where appropriate.
* Respect provider API rate limits.
* Recover gracefully after interruption.
* Allow future horizontal scaling of workers.

The implementation should prioritize correctness and resilience over raw speed.

---

# Error Handling

Handle:

* API rate limiting.
* Revoked connector credentials.
* Network interruptions.
* Partial scans.
* Deleted files during scanning.
* Permission-denied folders.
* Shared drive access changes.
* Worker crashes.
* Duplicate scan requests.

Every failure should be recoverable where practical.

---

# Security Requirements

Mandatory:

* Scanner operates in read-only mode.
* Never modify provider data.
* Respect provider permissions.
* Never expose private metadata across organizations.
* Record all scan activity in audit logs.
* Ensure organization isolation throughout the scanning pipeline.

---

# Logging & Observability

Log:

* Scan started.
* Scan completed.
* Scan cancelled.
* Scan resumed.
* Files discovered.
* Folders discovered.
* Scan duration.
* Errors encountered.
* Retry attempts.

Expose metrics that will later feed operational dashboards.

---

# Testing Strategy

### Unit Tests

* Traversal logic.
* Metadata normalization.
* Progress calculation.
* Retry logic.

### Integration Tests

* Scanner ↔ Connector interaction.
* Scanner ↔ Database persistence.
* Worker queue execution.
* Scan cancellation and resume.

### End-to-End Tests

* Organization starts a scan.
* Progress updates correctly.
* Files appear in the inventory.
* Scan survives a worker restart.
* Scan completes successfully.

---

# Acceptance Criteria

This phase is successful when:

* A full storage inventory can be built.
* Metadata is stored consistently.
* Folder hierarchy is preserved.
* Scan jobs are resumable.
* Progress is visible.
* Failures do not corrupt scan state.
* Scanner remains provider-agnostic.

---

# Manual QA Checklist (Founder)

Verify:

* [ ] A scan can be started.
* [ ] Scan progress updates accurately.
* [ ] Cancelling a scan works safely.
* [ ] Retrying a failed scan works.
* [ ] Folder hierarchy is represented correctly.
* [ ] File metadata appears accurate.
* [ ] No file contents are modified.
* [ ] Scanner recovers after worker restart.
* [ ] Large scans remain stable.
* [ ] Logs contain meaningful operational information.
* [ ] Documentation has been updated.
* [ ] CI passes.

---

# Definition of Done

Phase 4 is complete only when:

* Storage scanning is production-ready.
* Metadata is normalized.
* Progress reporting works.
* Resume and retry mechanisms function.
* Tests pass.
* Manual QA passes.
* Documentation is updated.
* No AI analysis or file-content processing has been introduced.

---

# Claude Execution Prompt

> Read the Engineering Handbook only if architectural clarification is needed. Implement **Phase 4 – Storage Discovery & Scanner Engine**. Build a provider-agnostic, read-only scanner that traverses connected storage, normalizes metadata, stores inventory in the database, and executes through the worker queue. Focus on scalability, resumability, fault tolerance, and clean abstraction boundaries. Do not implement content analysis, embeddings, duplicate detection, search indexing, recommendations, or any AI functionality. Those belong to later phases. At the end, produce a Phase Completion Report covering database changes, APIs, worker behavior, performance considerations, tests, documentation updates, and any implementation decisions that future phases should know about.

---

# Founder Verification Checklist

Approve this phase only if all answers are **YES**:

* [ ] Can an organization successfully scan its connected storage?
* [ ] Is the scanner completely read-only?
* [ ] Does scan progress accurately reflect the current state?
* [ ] Can interrupted scans resume without starting over?
* [ ] Is metadata stored in a provider-neutral format?
* [ ] Are workers resilient to failures and restarts?
* [ ] Does the scanner avoid provider-specific logic outside the connector layer?
* [ ] Are logs, audit records, and documentation complete?
* [ ] Has Claude produced the Phase Completion Report?
* [ ] Is the platform now ready to build the Metadata & Knowledge Engine in Phase 5?

---

## CTO Note

This is the **foundation of the intelligence pipeline**. Resist the temptation to add AI features here. The scanner's only responsibility is to produce a trustworthy, normalized inventory of organizational storage. Every later capability—knowledge extraction, embeddings, recommendations, dashboards, and automation—depends on the quality of this foundation. A clean scanner now will save months of refactoring later.
