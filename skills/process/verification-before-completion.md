# Verification Before Completion
Source: obra/superpowers · https://skills.sh/obra/superpowers/verification-before-completion
License: MIT · https://github.com/obra/superpowers

## Overview

Do not declare a task done until you have verified it actually works.
"It should work" and "I tested it and it works" are not equivalent.

## Verification Checklist

Before saying a task is complete, verify each of these:

### 1. The code compiles / parses without errors
```bash
cargo check          # Rust
mypy .               # Python
tsc --noEmit         # TypeScript
php -l <file>        # PHP
```

### 2. The pre-LLM pipeline passes
```bash
# Run the full pipeline for your language (see base-standards.mdc)
cargo fmt && cargo clippy --fix --allow-dirty && cargo check
```

### 3. The tests pass
```bash
cargo test           # Rust
pytest               # Python
vitest run           # TypeScript
phpunit              # PHP
```

### 4. The specific behavior requested works
- Run the actual command, endpoint, or function
- Verify with the exact input described in the task
- Do not assume — observe

### 5. No regressions
- Run the full test suite, not just the new tests
- Check that existing tests still pass

### 6. The Critic Pass (for significant changes)
```
/ask Critically review the last code modification.
Bug: / File: / Line: / Explanation: / Fix: format.
```

## What "Done" Means

A task is done when:
- [ ] Code compiles with zero errors and zero warnings
- [ ] Pre-LLM pipeline passes
- [ ] All tests pass (new + existing)
- [ ] The behavior was manually verified with actual inputs
- [ ] Critic Pass found no issues (for significant changes)
- [ ] ARCHITECTURE.md updated if decisions were made
- [ ] No TODOs left in changed files

## Integration with DeepLocal Forge

After the editor applies changes, run this sequence before declaring done:

```bash
# 1. Pipeline
cargo fmt && cargo clippy && cargo check   # or language equivalent

# 2. Tests
cargo test   # or pytest / vitest run / phpunit

# 3. Critic Pass (in Aider)
/critic

# 4. Only then:
# Mark the task as complete in the implementation plan
```
