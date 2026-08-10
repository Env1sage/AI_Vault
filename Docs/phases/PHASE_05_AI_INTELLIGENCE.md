Thank you. Looking at our roadmap, **Phase 5 is where AI Project Vault actually becomes an AI product.**

Everything before this has been building the foundation:

* ✅ Phase 0 — Engineering Blueprint
* ✅ Phase 1 — Engineering Foundation
* ✅ Phase 2 — Identity & Organization Platform
* ✅ Phase 3 — Google Workspace Connector Platform
* ✅ Phase 4 — Storage Discovery & Scanner Engine

Now we begin transforming raw metadata into **organizational knowledge**.

---

# PHASE 05

# Metadata Intelligence & Knowledge Engine

---

# Executive Summary

Phase 5 transforms AI Project Vault from a storage inventory system into a **knowledge platform**.

After Phase 4, the platform knows:

* Which files exist
* Where they are located
* Their metadata
* Folder hierarchy
* Ownership

However, metadata alone cannot answer business questions like:

* "Which marketing campaign assets belong together?"
* "Which documents are contracts?"
* "Which presentations are outdated?"
* "Which folders contain duplicate project work?"
* "Which files are likely to be important?"

This phase introduces the **Knowledge Engine**, responsible for understanding storage beyond file names and folder structures.

The Knowledge Engine builds structured knowledge that later powers:

* AI Chat
* Semantic Search
* Recommendations
* Duplicate Detection
* Knowledge Graph
* Founder Dashboard
* Automation Engine

This phase focuses on **understanding**, not decision-making.

---

# Mission

Design and implement a provider-independent Knowledge Engine that enriches scanned storage with normalized business metadata while maintaining a clear separation between deterministic processing and AI-assisted analysis.

---

# Objectives

By the end of this phase:

* Every indexed file has enriched metadata.
* Supported file types can be classified.
* Business categories are assigned where confidence is sufficient.
* Relationships between files begin to emerge.
* A searchable knowledge layer exists.
* The platform is ready for embeddings and semantic search.
* The engine remains modular so additional extractors can be added later.

---

# Why This Phase Exists

The scanner tells us **what exists**.

The Knowledge Engine tells us **what it means**.

Example:

Scanner Result:

```
Q3_Final_v12.pptx
```

Knowledge Engine Result:

```
Document Type:
Presentation

Department:
Marketing

Campaign:
Summer Launch

Status:
Final Version

Related Assets:
Banner.psd
Social_Posts.zip
Campaign_Brief.docx

Confidence:
94%
```

Only after this enrichment can AI produce meaningful answers.

---

# Deliverables

## Metadata Enrichment Engine

Implement a modular enrichment pipeline.

Each processor should operate independently.

Suggested processors include:

* File Type Classifier
* MIME Validator
* Extension Normalizer
* Folder Context Analyzer
* Naming Pattern Analyzer
* Ownership Analyzer
* Sharing Analyzer
* Version Detection
* Duplicate Candidate Detector (candidate generation only)
* Language Detection (where practical)

Each processor should contribute structured metadata rather than free-form text.

---

## Content Extraction Framework

Create an extensible extraction framework.

Support common formats such as:

* PDF
* DOCX
* XLSX
* PPTX
* TXT
* Markdown

Image, audio, and video processing should be scaffolded but can be deferred if needed.

Extraction should expose normalized text to downstream components without embedding AI-specific logic into the extractor.

---

## Knowledge Model

The Knowledge Engine should build relationships between:

* Files
* Folders
* Owners
* Departments
* Projects (where inferred)
* Campaigns (where inferred)
* Time periods
* Shared resources

Relationships should be stored in a way that future graph capabilities can consume them.

---

## Classification Pipeline

Implement deterministic classification first.

Examples:

* Invoice
* Contract
* Presentation
* Spreadsheet
* Image
* Design Asset
* Source Code
* Archive
* Documentation

Where deterministic rules are insufficient, the architecture should allow optional AI-assisted classification in later iterations.

---

## Relationship Discovery

Identify relationships such as:

* Files in the same project.
* Similar naming conventions.
* Sequential versions.
* Shared ownership.
* Common folders.
* Shared lifecycle.

Store relationships with confidence scores.

---

## Search Preparation

Prepare the data model for future semantic search by:

* Normalizing extracted text.
* Recording searchable attributes.
* Defining interfaces for embedding generation.

Do **not** generate embeddings in this phase.

---

## Worker Responsibilities

Workers should execute enrichment jobs asynchronously.

Responsibilities include:

* Processing newly scanned files.
* Reprocessing updated files.
* Tracking enrichment progress.
* Recording processor failures.
* Supporting resumable enrichment jobs.

---

## Frontend Deliverables

Extend the interface with:

* File detail view.
* Metadata panel.
* Classification information.
* Relationship summary.
* Enrichment status.
* Processing progress.

No AI chat or recommendation UI yet.

---

## Database Deliverables

Introduce entities or extensions for:

* Enriched Metadata
* Classification Results
* Relationships
* Processing Jobs
* Extraction Results
* Knowledge Attributes

Design them to remain provider-neutral and extensible.

---

# Architecture Impact

The Knowledge Engine sits directly after the Storage Scanner.

```text
Google Workspace
        │
        ▼
Connector Platform
        │
        ▼
Storage Scanner
        │
        ▼
Knowledge Engine
        │
        ▼
Knowledge Store
        │
        ▼
Future AI Services
```

The Knowledge Engine must not call the AI Gateway directly unless explicitly configured. Most enrichment should remain deterministic.

---

# Design Principles

The Knowledge Engine must:

* Be modular.
* Be deterministic where possible.
* Be provider-agnostic.
* Produce explainable outputs.
* Support incremental processing.
* Allow individual processors to be enabled or disabled.
* Never overwrite raw scan data.
* Record confidence scores where inference is used.

---

# Security Requirements

* Respect organization boundaries.
* Process only authorized files.
* Do not expose extracted content across tenants.
* Audit enrichment jobs.
* Sanitize extracted text before storage where appropriate.
* Never modify original files.

---

# Logging & Observability

Log:

* Enrichment job started.
* Processor execution.
* Extraction success/failure.
* Classification results.
* Relationship generation.
* Processing duration.
* Retry attempts.

Expose metrics for throughput and failure rates.

---

# Error Handling

Handle:

* Unsupported file formats.
* Corrupted documents.
* Extraction failures.
* Missing metadata.
* Partial processing.
* Worker interruptions.
* Timeout conditions.

Failures should affect only the relevant processor, not the entire pipeline.

---

# Testing Strategy

### Unit Tests

* Metadata processors.
* Classification rules.
* Relationship builders.
* Extraction adapters.

### Integration Tests

* Scanner → Knowledge Engine.
* Knowledge persistence.
* Worker orchestration.
* Incremental enrichment.

### End-to-End Tests

* Scan a sample workspace.
* Enrichment runs automatically.
* Metadata appears in the UI.
* Relationships are generated.
* Failed documents do not block the pipeline.

---

# Acceptance Criteria

This phase is successful when:

* Files receive enriched metadata.
* Classification works consistently.
* Relationships are generated.
* Enrichment is asynchronous.
* Processing is resumable.
* Future embedding generation can plug in without redesign.
* Knowledge remains provider-neutral.

---

# Manual QA Checklist (Founder)

Verify:

* [ ] Metadata is richer than raw scanner output.
* [ ] File classifications are accurate for supported formats.
* [ ] Relationships between related files appear logical.
* [ ] Unsupported files fail gracefully.
* [ ] Reprocessing updated files works correctly.
* [ ] No original file is modified.
* [ ] Enrichment jobs recover after interruption.
* [ ] Logs provide enough information for debugging.
* [ ] Documentation is updated.
* [ ] CI passes successfully.

---

# Definition of Done

Phase 5 is complete only when:

* Metadata enrichment is operational.
* Classification pipeline is functional.
* Relationship discovery is implemented.
* Knowledge data is persisted correctly.
* Tests pass.
* Manual QA passes.
* Documentation is updated.
* The platform is ready for embedding generation and semantic search in Phase 6.

---

# Claude Execution Prompt

>




---

# Founder Verification Checklist

Approve this phase only if every answer is **YES**:

* [ ] Does the platform understand more than basic file metadata?
* [ ] Are classifications accurate for supported document types?
* [ ] Are file relationships meaningful and explainable?
* [ ] Is the enrichment pipeline asynchronous and resilient?
* [ ] Can processors fail independently without stopping the entire pipeline?
* [ ] Is the design ready for embeddings and semantic search without major refactoring?
* [ ] Does the implementation remain provider-agnostic?
* [ ] Are logs, audit records, and documentation complete?
* [ ] Has Claude produced the Phase Completion Report?
* [ ] Is the platform now ready to build the AI Intelligence Layer in Phase 6?

---

## CTO Note

This phase defines the long-term intelligence quality of AI Project Vault. Avoid turning every problem into an LLM call. A strong deterministic Knowledge Engine will reduce AI costs, improve explainability, and make the platform faster and more predictable. The AI layer in the next phase should enhance this knowledge—not replace it.
