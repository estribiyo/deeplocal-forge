# Copilot/Codex Configuration — DeepLocal Forge

## Stack
Local AI infrastructure. Ollama serves models via OpenAI-compatible API on localhost:11434.

## Development Standards
Core rules: ai-specs/specs/base-standards.mdc
Backend: ai-specs/specs/backend-standards.mdc
Frontend: ai-specs/specs/frontend-standards.mdc
Documentation: ai-specs/specs/documentation-standards.mdc

## Workflow
1. Read ARCHITECTURE.md + CONSTRAINTS.md before starting
2. Run pre-LLM pipeline (fmt + lint + type check) before changes
3. Spec-driven: enrich user story → plan → implement
4. Critic Pass after significant changes

## Prompt Templates
ai-specs/specs/prompts.md
