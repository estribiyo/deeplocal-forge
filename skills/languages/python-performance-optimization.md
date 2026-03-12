# Python Performance Optimization
Source: wshobson/agents · https://skills.sh/wshobson/agents/python-performance-optimization
License: MIT · https://github.com/wshobson/agents

## Overview

Optimize only what you have measured. Premature optimization creates complexity
without solving real problems. Profile first, then optimize the bottleneck.

## Step 1: Measure Before Changing Anything

```python
import cProfile
import pstats

# Profile a function
profiler = cProfile.Profile()
profiler.enable()
your_function()
profiler.disable()

stats = pstats.Stats(profiler)
stats.sort_stats("cumulative")
stats.print_stats(20)  # Top 20 hotspots
```

For async code (FastAPI):
```python
import time
import logging

logger = logging.getLogger(__name__)

async def timed_endpoint():
    start = time.perf_counter()
    result = await do_work()
    elapsed = time.perf_counter() - start
    logger.info(f"endpoint took {elapsed:.3f}s")
    return result
```

## Common Bottlenecks and Fixes

### Database queries (most common)

```python
# Bad: N+1 query — 1 query for list + N queries for details
items = db.query(Item).all()
for item in items:
    print(item.owner.name)  # triggers a query per item

# Good: eager load in one query
from sqlalchemy.orm import joinedload
items = db.query(Item).options(joinedload(Item.owner)).all()
```

### Unnecessary computation in loops

```python
# Bad: recomputes len(data) every iteration
for i in range(len(data)):
    process(data[i])

# Good: compute once, use iterators
for item in data:
    process(item)
```

### Blocking I/O in async code

```python
# Bad: blocks the event loop
import requests
def get_data():
    return requests.get(url).json()  # synchronous in async context

# Good: use async HTTP
import httpx
async def get_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return response.json()
```

### String concatenation in loops

```python
# Bad: O(n²) — creates a new string every iteration
result = ""
for item in items:
    result += str(item) + ","

# Good: O(n)
result = ",".join(str(item) for item in items)
```

## FastAPI-specific

- Use `async def` for endpoints that do I/O (DB, HTTP, filesystem)
- Use `def` (sync) for CPU-bound endpoints — FastAPI runs them in a thread pool
- Use `BackgroundTasks` for work that does not affect the response
- Connection pooling: configure SQLAlchemy pool size based on expected concurrency

## When to Use Caching

Cache when:
- The same computation is repeated with the same inputs
- The result does not change frequently
- The computation is expensive (> 50ms)

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_pure_function(arg: str) -> str:
    ...
```

For FastAPI with Redis: use `fastapi-cache2`.

## Integration with DeepLocal Forge

```
/read skills/languages/python-performance-optimization.md
/ask
Profile this code and identify the performance bottleneck:
[paste code or describe the slow path]

Steps:
1. Identify what to measure
2. Show the profiling approach
3. Identify the root cause of slowness
4. Propose one targeted optimization
5. Explain how to verify the improvement
```
