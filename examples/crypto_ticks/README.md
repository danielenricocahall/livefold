# Live Crypto Ticks Demo

A Streamlit dashboard that replays a synthetic BTC/USD tick stream into a `LiveFold`, with a range slider for querying the high/low/average over any user-selected time window.

The synthetic stream is reproducible (seeded geometric Brownian motion + occasional jumps) and runs entirely offline. For real Binance data, see [`live_websocket.py`](./live_websocket.py) next to this file — it's a drop-in replacement.

## Run it

From the repo root:

```bash
uv run --group demo streamlit run examples/crypto_ticks/app.py
```

The dashboard opens in your browser. Pick a replay speed (1× through 100×), let ticks accumulate, and drag the range slider to see range aggregates update.

## What's happening

```python
from livefold import LiveFold

lf = LiveFold([], folds={"sum": sum, "max": max, "min": min})

# As each tick arrives:
lf.append(price)

# When the user picks a time window [t1, t2]:
stats = lf.query(left_idx, right_idx)
# → {"sum": ..., "max": ..., "min": ...}  in O(√n)
```

At a 25× replay rate, this generates ~125 ticks/second. After a few minutes the underlying series is in the tens of thousands; each query still completes in under 100µs. After an hour, the series is in the millions and queries still complete in well under a millisecond — see [`benchmarks/`](../../benchmarks/) for the curves.

## Why synthetic?

A live WebSocket demo is more impressive on the first viewing but rots fast: Binance changes endpoint paths, adds rate limits, or simply has an outage. Anyone reading this README a year from now should still be able to run the demo and see something. The synthetic generator gives you that — same shape (roughly BTC-ish prices, realistic volatility, occasional jumps) without the fragility.

If you want real ticks, [`live_websocket.py`](./live_websocket.py) shows the ~30 lines needed to swap them in. The rest of the demo (LiveFold, chart, range slider, query logic) is identical.

## Adapting this to your data

The "tick stream" pattern fits more than crypto:

- Ad bid streams — bid prices over time, range aggregates per campaign window
- Telemetry events — error counts, latency percentiles per deploy window
- Sensor networks — readings from multiple devices, range stats per sensor
- Game telemetry — player events, range stats per match

Anywhere you have a numeric stream that grows and you want fast aggregates over arbitrary historical windows, the same five lines of LiveFold apply.
