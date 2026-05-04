# livefold

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

Anywhere you have a numeric stream that grows and you want fast aggregates over arbitrary historical windows (e.g., request latencies, sensor readings, trade prices, telemetry events),`livefold` fits.

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

![Query latency vs collection size](./benchmarks/plots/query_latency.png)

At n = 10⁷, `livefold`'s median range query is **69 µs vs naive Python's 29 ms** (~400× faster), and append cost stays **flat at 2 µs across all n** while every other backend with a competitive query path (numpy, pandas) degrades linearly on appends. `livefold` is the only line that doesn't bend the wrong way on either axis.

Full methodology, append benchmarks, comparison against four backends, and the reproduction script: [`benchmarks/`](./benchmarks).

## Examples

Two runnable Streamlit demos in [`examples/`](./examples):

- **[`system_metrics/`](./examples/system_metrics)** — live `psutil`-driven CPU/memory dashboard with arbitrary-range aggregate queries. Runs entirely offline.
- **[`crypto_ticks/`](./examples/crypto_ticks)** — synthetic BTC/USD tick stream with high/low/avg-price queries. Includes a drop-in recipe for real Binance ticks.


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

## How it works

`LiveFold` splits its underlying list into ⌊√n⌋ blocks of size √n, precomputes the configured folds for each block, and updates them incrementally on mutation. A `query(left, right)` walks at most two partial blocks plus the precomputed folds for whole-block spans in between — touching roughly 2√n elements per fold regardless of n. Mo's algorithm with mutability and a dict-shaped output.

For the full derivation, complexity analysis, and worked examples, see the [original blog post](https://open.substack.com/pub/dannycahall/p/pysquagg-square-root-decomposition?r=1swlpp&utm_campaign=post&utm_medium=web&showWelcomeOnShare=true).

> *Note: the blog post predates the rebrand from `pysquagg` and uses the old singular `aggregator_function=` API. The math and structural choices are unchanged; only the package name and the `folds={"name": fn, ...}` dict shape have evolved.*

## Constraints

- Folds must be **associative** (i.e., form a [monoid](https://en.wikipedia.org/wiki/Monoid)). `sum`, `max`, `min`, `product`, `gcd`, bitwise `or`/`and`/`xor`, and any mergeable sketch (t-digest, HyperLogLog, Count-Min, Welford) all qualify. Commutativity is *not* required — string concatenation, matrix multiplication, and other ordered monoids work too. 
- **Not thread-safe.** Single-process, single-thread workloads only.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).
