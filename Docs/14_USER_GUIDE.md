# 14 — Version 1 User Guide

Status: **Living document**, introduced in Phase 10. Written for the person actually using the product day-to-day — a founder, an admin, a team member — not for a developer. For technical setup, see the [README](../README.md) and [Deployment Handbook](04_DEPLOYMENT_HANDBOOK.md).

---

## What AI Project Vault does

It connects to your organization's Google Workspace, builds a real understanding of what's actually in your storage, tells you what's worth doing about it, and — only when you explicitly say yes — does it for you. It never changes anything in your Drive without your approval.

## Getting started

### 1. Sign in
Sign in with your Google account. Your organization is created automatically the first time someone from your domain signs in; the first person to sign in becomes the organization's **owner**.

### 2. Connect Google Workspace
Go to **Storage Connections** and connect your Google Workspace account. This is a separate step from signing in — signing in proves who you are, connecting grants the platform permission to actually read (and, later, act on) your Drive content. You'll see exactly what permission is being requested before you approve it.

### 3. Run your first scan
From the **Scans** page, start a scan. This builds an inventory of every file and folder the connected account can see — read-only, nothing is changed. Larger Drives take longer; you can watch progress live.

### 4. Let it think
Once a scan finishes, three more stages run automatically, in order, with no action needed from you:
- **Enrichment** — classifying files, extracting readable text, finding relationships between files (duplicates, versions, shared ownership).
- **Embedding** — building the semantic index that powers search and chat.
- **Recommendations** — generating concrete, explainable suggestions based on everything above.

Watch progress on the **Scans** page; when all three finish, your **Dashboard** populates.

## The Dashboard

Your home base — connected storage at a glance, how much of it is understood vs. still pending, recent AI-generated insights, and your top-priority recommendation. It refreshes automatically and reflects the latest completed pipeline run.

## Search & Chat

**Search** finds files by meaning, not just filename — it understands what you're asking for, ranks results by relevance, and shows you why each result matched. **Chat ("Ask Vault")** lets you ask questions in plain English and get an answer with citations back to the actual files it used — never a made-up answer about files it didn't actually find.

Ask Vault answers two kinds of questions:

- **Storage questions** — "How much storage am I using?", "What's taking the most space?", "Show me duplicates.", "What are my largest files?", "Find files that haven't been used in a year.", "What should I clean up first?" — these are answered directly from your organization's real Storage Intelligence data (the same numbers you'd see on the Storage Intelligence page), never estimated or guessed. The chat message shows a small label naming which lookup answered it (e.g. "Storage overview").
- **File-content questions** — "What does the payroll file say?", "Find the presentation about the marketing strategy." — these search across your actual file names and content and cite the specific files the answer came from.

Ask Vault is **read-only**. It will never delete, move, rename, or modify a file, and it will never tell you a file is "safe to delete" — for cleanup, it points you to the relevant Storage Intelligence page, where you review and decide yourself.

## Recommendations

The **Recommendations** page lists everything the platform has flagged — organized by category (storage cleanup, security, collaboration, etc.), each with a plain-language explanation, a confidence score, and an estimated impact. Click into any one for the full detail: exactly which files it affects and why.

## Taking action

Recommendations don't do anything by themselves. To act on one:

1. From a recommendation's detail page, create an **execution plan** — a precise, itemized list of exactly what would change (which files, what action, in what order).
2. Review the plan on the **Execution Center** — every step is visible before you decide.
3. **Approve** it. Only an owner or admin can approve, and approving a high-risk plan requires an extra confirmation click — it should be genuinely hard to approve something risky by accident.
4. Once approved, the platform carries it out and shows you real-time progress on the **Execution History** page. Every action can be rolled back — nothing is ever permanently deleted; files go to Google Drive's own Trash, exactly as if you'd deleted them yourself by hand.

## Automation

If you find yourself approving the same kind of action repeatedly, you can automate it — carefully.

- **Workflows** (under **Automation**) let you build a repeatable sequence: a trigger (a schedule, an event like "scan completed," or a manual button), optional conditions, and one or more actions.
- **Policies** are the safety valve for automated execution — a workflow's action step can only run without asking you every single time if it's covered by a policy you (an owner or admin) specifically created and published. Creating a policy is a deliberate, versioned decision — never a default, never silent.
- Even when a policy auto-approves something, it shows up in your **Execution History** exactly like a manual approval would — automation is a second kind of approval, not a way around approval.
- Start from a **Template** (Templates Gallery) — six ready-made workflows for common patterns (archiving inactive files, a weekly storage health report, duplicate review, and others) that you customize rather than build from scratch.

## Notifications

In-app notifications tell you about things worth knowing — a workflow finished, an approval is waiting on you, a scheduled report is ready. Check the **Notifications** page. (Email notifications aren't turned on yet in this version — everything shows up in-app.)

## Who can do what

- **Owner/Admin:** everything — connect storage, approve executions, create/publish workflows and policies, manage organization settings.
- **Member:** view dashboards, search, chat, browse recommendations — cannot approve executions or manage automation.

## Getting help

If something looks wrong or you're unsure what an action will do, don't approve it — every plan shows its full detail before you commit, and nothing happens without your explicit sign-off. For technical issues, see the [Operations Runbook](09_OPERATIONS_RUNBOOK.md) or contact your organization's technical administrator.
