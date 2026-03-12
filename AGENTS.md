# Agent Configuration — DeepLocal Forge

This file is the entry point for AI agents that do not have a dedicated config file.
It references the single source of truth for all development standards.

## Stack
- Infrastructure: Docker + Ollama (local LLM) + Qdrant (vector DB) + MCP servers
- Languages: Rust · Python · JavaScript/TypeScript · React · PHP · HTML/CSS
- Orchestrators: Aider · Roo Code · Continue · OpenCode

## Core Rules
See: ai-specs/specs/base-standards.mdc

## Backend Standards
See: ai-specs/specs/backend-standards.mdc

## Frontend Standards
See: ai-specs/specs/frontend-standards.mdc

## Documentation Standards
See: ai-specs/specs/documentation-standards.mdc

## Available Prompt Templates
See: ai-specs/specs/prompts.md

## Workflow
1. Read ARCHITECTURE.md and CONSTRAINTS.md at the start of every session
2. Run the pre-LLM pipeline before any code change (see base-standards.mdc)
3. Follow the spec-driven workflow (enrich → plan → implement)
4. Run Critic Pass after significant changes

## Project Context
- ARCHITECTURE.md — adopted technical decisions (project-specific, create at project root)
- CONSTRAINTS.md — hard constraints (project-specific, create at project root)
- ai-specs/changes/ — feature implementation plans
