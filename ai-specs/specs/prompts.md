# Reusable Prompt Templates

These prompts are designed for use with Aider, Roo Code, Continue, and OpenCode
connected to the DeepLocal Forge stack. Copy and adapt as needed.

---

## Spec Generation (Modelo B — new projects)

### Enrich a User Story
```
/ask
Enrich the following user story. Add:
- Detailed acceptance criteria (Given/When/Then format)
- Edge cases and validation rules
- Technical considerations
- Testing scenarios
- Non-functional requirements (performance, security, accessibility)

Keep everything grounded in the existing codebase context.
Do not invent features not implied by the story.

User Story:
[paste story here]
```

### Generate Backend Implementation Plan
```
/architect
Think briefly (max 6 steps). Focus on the final plan.

Generate a backend implementation plan for:
[ticket ID and description]

The plan must cover:
1. Architecture impact (which modules are affected, which are new)
2. Step-by-step implementation order (validation → service → controller → routes → tests)
3. Test specifications for each layer (unit + integration)
4. Error handling strategy
5. Definition of Done checklist

Output format: markdown suitable for saving to ai-specs/changes/<TICKET>_backend.md
Constraints: see CONSTRAINTS.md. Standards: see ai-specs/specs/base-standards.mdc
```

### Generate Frontend Implementation Plan
```
/architect
Think briefly (max 6 steps). Focus on the final plan.

Generate a frontend implementation plan for:
[ticket ID and description]

The plan must cover:
1. Component tree (new components, updated components)
2. State management approach
3. API integration points
4. Accessibility requirements
5. Test specifications (unit + E2E happy path)
6. Definition of Done checklist

Output format: markdown suitable for saving to ai-specs/changes/<TICKET>_frontend.md
Standards: see ai-specs/specs/frontend-standards.mdc
```

---

## Architecture & Design

### Design a new module (Rust)
```
/architect
Before answering, reason briefly about:
1. Ownership model and lifetime relationships
2. Trait boundaries and abstractions
3. Error propagation strategy

Keep reasoning under 6 steps. Then produce:
- Module structure (files, public API)
- Trait definitions with ownership annotations
- No implementation code — design only

Goal: [describe the module]
Constraints: see CONSTRAINTS.md
```

### Design a new API endpoint
```
/architect
Think briefly (max 6 steps).

Design the API contract for:
[endpoint description]

Produce:
- OpenAPI 3.0 path spec (YAML snippet)
- Request/response schemas
- Error cases with status codes
- Business rule validations

Do not write implementation code yet.
```

### Review an architectural decision
```
/ask
Review this architectural decision:
[describe the decision]

Evaluate:
1. Does it fit the existing architecture (see ARCHITECTURE.md)?
2. Does it violate any constraint (see CONSTRAINTS.md)?
3. What are the long-term maintenance implications?
4. Are there simpler alternatives?

Be concise. Flag only real concerns, not style preferences.
```

---

## Code Review & Quality

### Critic Pass (post-refactor)
```
/ask
Critically review the last code modification.
For each issue found, use exactly this format:

Bug: <one-line description>
File: <filename>
Line: <line number or range>
Explanation: <why it is a problem>
Fix: <concrete suggestion>

Focus on: hidden bugs, performance regressions, incorrect ownership/lifetime
assumptions, edge cases not covered, violations of CONSTRAINTS.md.
If no issues found, respond only: "No issues found."
```

### Debugging (root cause first)
```
/ask
I am seeing this error:
[paste error / stack trace]

Before suggesting fixes:
1. Identify the root cause (not the symptom)
2. Trace the data flow to find where it originates
3. State your hypothesis clearly: "The root cause is X because Y"

Only then propose a single minimal fix.
Do not suggest multiple fixes at once.
```

### Update architecture memory
```
/ask
Review the changes made in this session.
Identify any architectural decisions that should be recorded.

For each decision, produce a markdown entry in this format:
## [Category]
- **Decision**: [what was decided]
- **Reason**: [why]
- **Date**: [today's date]

Append to ARCHITECTURE.md. Only include real decisions — not obvious implementation details.
```

---

## RAG Queries (rag-bot)

### Query a document corpus
```
[System: inject ai-specs/specs/base-standards.mdc as context]

You are a documentation assistant. Answer ONLY from the provided context.
If the answer is not in the context, say: "I cannot find this in the available documents."
Never use your own knowledge. Always cite the exact passage.

Question: [user question]
```

---

## Multi-Agent (parallel tasks)

### Dispatch parallel subagents
```
/architect
Think briefly (max 4 steps).

I need to implement these independent tasks in parallel:
1. [task A — describe clearly]
2. [task B — describe clearly]
3. [task C — describe clearly]

For each task, produce:
- A self-contained instruction block that a subagent can execute independently
- Required context files to /add before starting
- Success criteria (how to verify it's done)

Assume each subagent has no knowledge of the others' work.
```
