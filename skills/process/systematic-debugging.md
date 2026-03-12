# Systematic Debugging
Source: obra/superpowers · https://skills.sh/obra/superpowers/systematic-debugging
License: MIT · https://github.com/obra/superpowers

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you have not completed Phase 1, you cannot propose fixes.

## The Four Phases

### Phase 1: Root Cause Investigation

BEFORE attempting ANY fix:

1. Read error messages carefully — do not skip stack traces
2. Reproduce consistently — if not reproducible, gather more data first
3. Check recent changes — git diff, new dependencies, config changes
4. Gather evidence at each component boundary before proposing anything
5. Trace data flow backward to the origin of the bad value

### Phase 2: Pattern Analysis

1. Find working examples of similar code in the same codebase
2. Read the reference implementation completely — do not skim
3. List every difference between working and broken, however small

### Phase 3: Hypothesis and Testing

1. State clearly: "I think X is the root cause because Y"
2. Make the SMALLEST possible change to test the hypothesis
3. One variable at a time — never stack multiple fixes

### Phase 4: Implementation

1. Write a failing test case first
2. Implement a single fix targeting the root cause
3. Verify the fix — tests pass, no regressions

**If 3+ fixes have failed:** STOP. Question the architecture, not the symptom.

## Red Flags — Stop and Follow the Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "It's probably X, let me fix that" (without tracing)
- "One more fix attempt" (when already tried 2+)

**All of these mean: STOP. Return to Phase 1.**

## Integration with DeepLocal Forge

```bash
# Before debugging with the LLM, run the pre-LLM pipeline first
cargo check          # Rust — see the actual compiler errors
mypy .               # Python — see the actual type errors
tsc --noEmit         # TypeScript — see the actual type errors

# Then add the error output as context
/run cargo check 2>&1 | head -50
/ask [paste this skill] + Follow Phase 1: what is the root cause of this error?
```
