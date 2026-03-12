# Gemini Agent Configuration — DeepLocal Forge

## Stack Context
Local AI development stack. All inference runs on local hardware via Ollama.
No external API calls. No cloud dependencies.

## Core Rules
See file: ai-specs/specs/base-standards.mdc

## Standards
- Backend: ai-specs/specs/backend-standards.mdc
- Frontend: ai-specs/specs/frontend-standards.mdc
- Documentation: ai-specs/specs/documentation-standards.mdc

## Session Protocol
1. Load ARCHITECTURE.md and CONSTRAINTS.md at session start
2. Run pre-LLM pipeline before modifying code
3. Use spec-driven workflow: enrich → plan → implement
4. Critic Pass after significant changes

## Prompt Templates
See: ai-specs/specs/prompts.md
