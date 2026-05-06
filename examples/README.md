# LiveFold Examples

Two runnable Streamlit demos showing what `livefold` is for in practice. Both use the same five-line core — `TimeIndexedLiveFold(folds={...})` + `.append(value, timestamp=t)` + `.query_time_range(t1, t2)` — applied to different data sources.

## [`system_metrics/`](./system_metrics/) — Live system monitoring

Polls `psutil` once per second (CPU %, memory %), appends to a TimeIndexedLiveFold, and queries `{sum, max, min}` over user-selected time windows. **Runs entirely offline**, no external services. This is the canonical demo — bulletproof, universal, and matches the observability/SRE use case where the library shines.

```bash
uv run --group demo streamlit run examples/system_metrics/app.py
```

## [`crypto_ticks/`](./crypto_ticks/) — Live crypto tick replay

Synthetic BTC/USD ticks (seeded GBM + occasional jumps) replayed at configurable speed into a TimeIndexedLiveFold, with high/low/avg-price queries over any window. Includes a [`live_websocket.py`](./crypto_ticks/live_websocket.py) recipe for swapping in real Binance ticks if you want them.

```bash
uv run --group demo streamlit run examples/crypto_ticks/app.py
```

## Setup

From the repo root:

```bash
uv sync --group demo
```

That installs Streamlit, Plotly, and `psutil` alongside livefold. The base library has zero runtime dependencies — these are only pulled in when you actually want to run the demos.

## Why two?

The library isn't tied to one domain. The system-metrics demo speaks to observability/SRE folks; the crypto demo speaks to quant/finance folks; the same `TimeIndexedLiveFold` instance works for both. Together they make the implicit point that this is a **primitive** — applicable wherever you have a mutable sequence and want fast aggregates over arbitrary ranges.
