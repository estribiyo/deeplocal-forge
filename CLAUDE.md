# Claude Agent Configuration — DeepLocal Forge

## Model Configuration
This stack runs Claude via local Ollama endpoints, not the Anthropic API.
The Ollama API is OpenAI-compatible; configure your client accordingly.

| Role       | Model alias     | Endpoint                      |
|------------|-----------------|-------------------------------|
| Architect  | r1-architect    | http://localhost:11434        |
| Editor     | qwen-editor     | http://localhost:11434        |
| RAG        | rag-bot         | http://localhost:11434        |

## Core Rules
@ai-specs/specs/base-standards.mdc

## Standards by Layer
- Backend: @ai-specs/specs/backend-standards.mdc
- Frontend: @ai-specs/specs/frontend-standards.mdc
- Documentation: @ai-specs/specs/documentation-standards.mdc

## Session Start Checklist
Before starting any task:
1. Read ARCHITECTURE.md (project-specific decisions)
2. Read CONSTRAINTS.md (project-specific hard limits)
3. Run pre-LLM pipeline for the project language
4. Add relevant files with /add before requesting changes

## Architect Mode (complex tasks)
```
/architect
Think briefly (max 6 steps). Focus on the final answer.
[your goal + constraints]
```

## Critic Pass (after significant changes)
```
/ask
Critically review the last code modification.
Bug: / File: / Line: / Explanation: / Fix: format.
Focus on real issues only. If none: "No issues found."
```

## Reasoning Budget Control
- Design tasks: "Think briefly (max 6 steps). Focus on the final answer."
- Rust lifetimes: "Reason briefly about: (1) ownership (2) lifetimes (3) trait bounds. Max 6 steps."
- Rescue from loop: "Give the answer with minimal reasoning."
