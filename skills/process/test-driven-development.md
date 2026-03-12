# Test-Driven Development
Source: obra/superpowers · https://skills.sh/obra/superpowers/test-driven-development
License: MIT · https://github.com/obra/superpowers

## Overview

Write the test first. The test defines the contract. The implementation satisfies it.

**Core principle:** A failing test is the only valid starting point for new code.

## The TDD Cycle

```
Red → Green → Refactor
```

1. **Red**: Write a test that fails because the feature does not exist yet
2. **Green**: Write the minimum code to make the test pass
3. **Refactor**: Clean up without breaking the test

## Rules

- Never write implementation code without a failing test first
- The failing test must fail for the RIGHT reason (not a syntax error or import failure)
- Write one test at a time — do not write a test suite before any implementation
- After green: refactor freely, the test is your safety net
- A test that never fails gives you no information

## Test Anatomy

Every test must have:
1. **Arrange**: set up the preconditions
2. **Act**: call the thing being tested
3. **Assert**: verify one specific outcome

```python
# Python example
def test_calculate_discount_applies_rate():
    # Arrange
    price = 100.0
    rate = 0.2

    # Act
    result = calculate_discount(price, rate)

    # Assert
    assert result == 80.0
```

```rust
// Rust example
#[test]
fn test_calculate_discount_applies_rate() {
    // Arrange
    let price = 100.0_f64;
    let rate = 0.2_f64;

    // Act
    let result = calculate_discount(price, rate).unwrap();

    // Assert
    assert!((result - 80.0).abs() < f64::EPSILON);
}
```

## What to Test

| Test type       | Tests what                              | Mocks allowed?        |
|-----------------|-----------------------------------------|-----------------------|
| Unit            | One function/method in isolation        | At system boundaries  |
| Integration     | Multiple modules working together       | External systems only |
| E2E             | Full user flow (HTTP in → HTTP out)     | Nothing               |

## What NOT to Test

- Implementation details (test behavior, not internals)
- Private methods (test through the public API)
- Framework code (trust the framework)
- Configuration values (test that config is loaded, not the values themselves)

## Integration with DeepLocal Forge

```
/ask
I need to implement: [feature description]

Follow TDD:
1. Show me the failing tests first (do not write implementation yet)
2. Tests must follow Arrange/Act/Assert
3. Cover: happy path, edge cases, error cases
4. Language: [Rust/Python/TypeScript]
5. Framework: [cargo test/pytest/vitest]
```
