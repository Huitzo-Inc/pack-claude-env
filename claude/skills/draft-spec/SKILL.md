---
description: Guided requirements gathering and specification for new Intelligence Packs and Dashboards
---

# /draft-spec

Run a structured, multi-phase requirements gathering process to produce a formal specification and architecture document for a new project.

## Usage

```
/draft-spec <project-name>
```

## Overview

This skill guides the user through 7 phases adapted from Spec-Driven Development for the Huitzo platform. It produces formal specification and architecture documents that feed into the docs-first workflow.

**This process is thorough and exhaustive by design.** The more context gathered, the better the output. Do not rush through phases.

## Steps

1. **Parse project name** from `$ARGUMENTS`.

2. **Ask project type**: "Is this a pack (Python commands), a dashboard (React frontend), or a full-stack project (pack + dashboard)?"

3. **Create spec directory**: `mkdir -p docs/spec/`

4. **Run through 7 phases sequentially.** Each phase must be explicitly confirmed by the user before advancing to the next.

### Phase 1 — Ideation (Brain Dump)

Ask the user to describe their idea freely:
- "What is this project? Describe it in your own words — don't worry about structure."
- "Who is the target user? What problem does it solve for them?"
- "What does success look like? How would you measure it?"

After the brain dump:
- Extract key themes
- Identify vague areas
- Ask follow-up questions for anything unclear
- **Do not advance until you have a clear understanding of the core idea**

### Phase 2 — Discovery (Structured Context)

Drill into domain, users, and workflows:
- "What domain does this operate in?" (e.g., insurance, finance, healthcare, logistics)
- "What is the user's workflow today without this tool?"
- "What data does the user have access to?"
- "What are the key entities in this domain and their relationships?"
- "What regulations or compliance requirements apply?"
- "Are there industry-specific terms we should define in a glossary?"

For every vague answer, ask: "Can you be more specific about...?"

### Phase 3 — Integration Mapping

Identify all external dependencies:
- "What external APIs or services does this need?"
- "What data sources? (databases, files, APIs, uploads)"
- "What authentication is needed for external services?"
- Present the Huitzo context services list and ask which are needed:
  - `ctx.llm` — Language models (text generation, analysis, structured output)
  - `ctx.http` — External HTTP APIs (domain-restricted)
  - `ctx.email` — Send emails (notifications, reports)
  - `ctx.storage` — Tenant-isolated key-value storage
  - `ctx.files` — File upload/download
  - `ctx.secrets` — User-provided API keys and credentials
  - `ctx.telegram` — Telegram messages
  - `ctx.ssh` — Remote command execution
  - `ctx.mcp` — Model Context Protocol servers
- "Does this need real-time updates? (WebSocket events)"
- For each external API: note the base URL, auth method, and rate limits

### Phase 4 — Data Contract Definition

Define schemas for every command and storage need:
- For each identified command:
  - Input arguments: name, type, required flag, validation rules, description
  - Return value: JSON structure with field types and descriptions
  - Error conditions: which SDK exceptions and when
  - Timeout estimate
- "What data needs to be persisted?"
  - Storage keys, scope (user/tenant/pack), TTL, data shape
- For dashboard projects:
  - "What state does the UI need to manage?"
  - "What data flows between the pack and the dashboard?"
  - Component props and types

### Phase 5 — Constraint Analysis

Capture non-functional requirements:
- "Performance requirements?" (timeout limits, response time SLAs, data volume)
- "Security constraints?" (data classification, encryption, PII handling)
- "Rate limits on external APIs?"
- "What happens when dependencies are unavailable?" (graceful degradation, fallbacks)
- "Scale expectations?" (concurrent users, data volume, storage size)
- "Any regulatory compliance?" (GDPR, HIPAA, SOC 2, industry-specific)

### Phase 6 — Specification Generation

Synthesize all phases into a formal specification. Write to `docs/spec/{project-name}-spec.md`:

Use the template from `templates/spec-template.md.tmpl`.

Sections: Overview, User Stories, Command Specifications (per command: name, args, returns, errors, services), Dashboard Specifications (per page/component), Non-Functional Requirements, Storage Schema, External Dependencies, Glossary.

### Phase 7 — Architecture Generation

Generate technical architecture. Write to `docs/spec/{project-name}-architecture.md`:

Sections: System Overview, Command Architecture (per command: implementation approach, LLM strategy), Dashboard Architecture (component tree, state management, routing), Storage Design (keys, scopes, TTLs), Integration Architecture (external services, auth, retry), Error Handling Strategy, Implementation Plan (ordered task list with dependencies).

5. **Print summary** of what was generated and next steps:
   - "Specification written to `docs/spec/{name}-spec.md`"
   - "Architecture written to `docs/spec/{name}-architecture.md`"
   - "Next: Use these to write command docs with `/draft-docs` and component docs"
