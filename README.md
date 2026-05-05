# livefold

*live + fold — incremental folds over a mutable sequence.*

[![Build Status](https://github.com/danielenricocahall/livefold/actions/workflows/ci.yaml/badge.svg)](https://github.com/danielenricocahall/livefold/actions/workflows/ci.yaml)
[![Supported Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://github.com/danielenricocahall/livefold/blob/main/pyproject.toml)
[![license](https://img.shields.io/github/license/danielenricocahall/livefold.svg)](https://github.com/danielenricocahall/livefold/blob/main/LICENSE)

> A primitive for online sequential aggregation in Python.
> Maintain a mutable numeric sequence; query exact aggregates over any range
> in **O(√n)**; plug in any associative reducer (any monoid).

## When to reach for it

| Need | Use |
|---|---|
| Immutable series, range aggregates | Prefix sums |
| Frequent point updates, log-time queries | Segment tree / Fenwick tree |
| Fixed-width rolling windows | `pandas.rolling()` / `polars.rolling()` |
| **Mutable series, arbitrary range queries, multi-fold** | **livefold** |

Common shapes: request latencies, sensor readings, trade prices, telemetry events.

## Quickstart

```bash
pip install livefold
```

```python
from livefold import LiveFold

lf = LiveFold([1, 2, 3, 4, 5, 6], folds={"sum": sum, "max": max, "min": min})

lf.append(7)
lf.query(0, 5)
# → {"sum": 21, "max": 6, "min": 1}

# Mutate freely; aggregates stay current
lf[2] = -1
lf.query(2, 5)
# → {"sum": 9, "max": 6, "min": -1}
```

## Performance

![Query latency vs collection size](https://raw.githubusercontent.com/danielenricocahall/livefold/main/benchmarks/plots/query_latency.png)

At n = 10⁷, `livefold`'s median range query is **69 µs vs naive Python's 29 ms** (~400× faster), and append cost stays **flat at 2 µs across all n** while every other backend with a competitive query path (numpy, pandas) degrades linearly on appends. `livefold` is the only line that doesn't bend the wrong way on either axis.

Full methodology, append benchmarks, comparison against four backends, and the reproduction script: [`benchmarks/`](https://github.com/danielenricocahall/livefold/tree/main/benchmarks).

## Examples

Two runnable Streamlit demos in [`examples/`](https://github.com/danielenricocahall/livefold/tree/main/examples):

- **[`system_metrics/`](https://github.com/danielenricocahall/livefold/tree/main/examples/system_metrics)** — live `psutil`-driven CPU/memory dashboard with arbitrary-range aggregate queries. Runs entirely offline.
- **[`crypto_ticks/`](https://github.com/danielenricocahall/livefold/tree/main/examples/crypto_ticks)** — synthetic BTC/USD tick stream with high/low/avg-price queries. Includes a drop-in recipe for real Binance ticks.


## API

```python
LiveFold(data: Iterable, folds: dict[str, Callable])
```

| Member | Returns | Notes |
|---|---|---|
| `lf.append(x)` | `None` | Amortized O(1) |
| `lf.query(left, right)` | `dict[str, Any]` | O(√n); inclusive bounds |
| `lf.blocks` | `list[list]` | Underlying √n-sized blocks |
| `lf.folded_values` | `dict[str, list]` | Per-fold, per-block aggregates |
| `lf.insert / pop / extend / remove / sort / ...` | — | Standard `list` methods; blocks and folds updated in place |

`LiveFold` subclasses `list`, so it's a drop-in for any code that expected a plain list — until you start calling `query`.

## Time-indexed queries: `TimeIndexedLiveFold`

For monotonic streams where you want to query by *time* instead of *index*, `TimeIndexedLiveFold` carries a parallel timestamp per element and exposes `query_time_range` — still O(√n).

```python
from livefold import TimeIndexedLiveFold

lf = TimeIndexedLiveFold(
    [1, 2, 3],
    folds={"sum": sum, "max": max},
    timestamps=[1.0, 2.0, 3.0],
)
lf.append(4, timestamp=4.0)
lf.append(5, timestamp=5.0)

lf.query_time_range(2.0, 4.0)
# → {"sum": 9, "max": 4}
```

If you omit `timestamps` / `timestamp`, `time.time()` is used by default. The class is generic over the timestamp type — anything orderable works (`float`, `int`, `datetime`, ...). Pass explicit timestamps for any non-`float` type:

```python
from datetime import datetime
from livefold import TimeIndexedLiveFold

lf = TimeIndexedLiveFold[datetime](
    [1, 2, 3],
    folds={"sum": sum},
    timestamps=[datetime(2025, 1, 1), datetime(2025, 6, 1), datetime(2026, 1, 1)],
)
lf.query_time_range(datetime(2025, 5, 1), datetime(2026, 6, 1))
# → {"sum": 5}
```

`TimeIndexedLiveFold` is **append-only by design**. Operations that would break time ordering raise `MonotonicityError`:

- `insert`, `sort`, `reverse` — would break the ordering invariant
- slice `__setitem__`, slice `__delitem__` — would desync data and timestamps
- `append` / `extend` with a timestamp earlier than the last stored one
- `+` / `+=` with anything other than another `TimeIndexedLiveFold` (use `extend(values, timestamps=...)` instead)

Integer indexing (`lf[i] = x`, `del lf[i]`), `pop`, `remove`, and `clear` work normally and keep the parallel timestamp list in sync. `+` and `+=` between two `TimeIndexedLiveFold` instances concatenate timestamps and re-check monotonicity.

## How it works

`LiveFold` splits its underlying list into ⌊√n⌋ blocks of size √n, precomputes the configured folds for each block, and updates them incrementally on mutation. A `query(left, right)` walks at most two partial blocks plus the precomputed folds for whole-block spans in between — touching roughly 2√n elements per fold regardless of n. Mo's algorithm with mutability and a dict-shaped output.

`TimeIndexedLiveFold` layers a parallel monotonically non-decreasing timestamp list on top. `query_time_range(start, end)` calls `bisect_left`/`bisect_right` to map timestamps to indices in O(log n), then routes through the same √n-decomposed query path — so overall query cost stays O(√n).

For the full derivation, complexity analysis, and worked examples, see the [original blog post](https://open.substack.com/pub/dannycahall/p/pysquagg-square-root-decomposition?r=1swlpp&utm_campaign=post&utm_medium=web&showWelcomeOnShare=true).

> *Note: the blog post predates the rebrand from `pysquagg` and uses the old singular `aggregator_function=` API. The math and structural choices are unchanged; only the package name and the `folds={"name": fn, ...}` dict shape have evolved.*

## Fold contract

A fold is a single-argument callable `fn(items) -> result` that:

1. Accepts an **iterable** of elements (or, when called internally to combine block results, an iterable of prior fold results) and returns a single value.
2. Is **associative**: `fn([fn([a, b]), fn([c, d])]) == fn([a, b, c, d])`. This lets `query` combine precomputed block-level folds with the partial folds at each end.
3. Returns a value of the same shape it accepts as elements — i.e., feeding the result back through `fn` together with other results must work. `len` is a common-but-broken choice: it returns an `int` regardless of input shape, so `len([len(block_a), len(block_b)])` gives `2`, not the total element count.

Examples that satisfy the contract: `sum`, `max`, `min`, `math.prod`, `math.gcd` (via `functools.reduce`), bitwise `or`/`and`/`xor`, `"".join`, and any mergeable sketch (t-digest, HyperLogLog, Count-Min, Welford) wrapped in a fold-shaped callable. Commutativity is *not* required — string concatenation, matrix multiplication, and other ordered monoids work too.

## Constraints

- **Not thread-safe.** Single-process, single-thread workloads only.

## Contributing

See [CONTRIBUTING.md](https://github.com/danielenricocahall/livefold/blob/main/CONTRIBUTING.md).
