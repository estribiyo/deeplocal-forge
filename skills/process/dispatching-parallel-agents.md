# Dispatching Parallel Agents
Source: obra/superpowers · https://skills.sh/obra/superpowers/dispatching-parallel-agents
License: MIT · https://github.com/obra/superpowers

## Overview

When a task has multiple independent subtasks, dispatch them to separate agents
running in parallel rather than executing them sequentially.

**Prerequisite**: The subtasks must be truly independent — no shared state,
no ordering dependency, no file conflicts.

## When to Use

Use parallel agents when:
- Building frontend + backend independently (different files, same interface contract)
- Writing tests for multiple modules simultaneously
- Refactoring several unrelated modules
- Running validation in multiple languages simultaneously

Do NOT use when:
- Tasks share files that will be modified
- Task B depends on the output of Task A
- The combined work touches the same database migration

## Preparation: Decompose First

Before dispatching, the architect must:
1. Identify the independent subtasks
2. Define a clear interface/contract between the parts (so they can integrate)
3. Write a self-contained instruction block for each agent
4. Specify the exact files each agent will read and modify

```
/architect
Think briefly (max 4 steps).

Decompose this task into independent subtasks:
[task description]

For each subtask, output:
- Files to read (context)
- Files to modify (scope)
- Success criteria (how to verify done)
- Self-contained instruction (what the agent must do)

Verify: do any subtasks share files? If yes, they are NOT independent.
```

## Execution Pattern (with git worktrees)

```bash
# 1. Create a worktree per subtask
git worktree add ../project-feature-api feature/api
git worktree add ../project-feature-ui feature/ui

# 2. Launch an agent in each worktree
cd ../project-feature-api && aider --read skills/process/executing-plans.md
cd ../project-feature-ui  && aider --read skills/process/executing-plans.md

# 3. Each agent works independently

# 4. Integrate: merge both branches to a feature integration branch
git checkout -b feature/integration
git merge feature/api
git merge feature/ui
```

## Integration with DeepLocal Forge

Each parallel agent should:
1. Read its own copy of `ARCHITECTURE.md` and `CONSTRAINTS.md`
2. Run its own pre-LLM pipeline
3. Write its own tests and verify they pass
4. NOT touch files outside its defined scope

The orchestrator (you) is responsible for:
- Defining the contract between parts before dispatch
- Integrating and resolving any conflicts after parallel work
- Running the Critic Pass on the integrated result
