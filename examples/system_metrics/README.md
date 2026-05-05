# Live System Metrics Demo

A Streamlit dashboard that polls `psutil` once per second, appends the reading to a `TimeIndexedLiveFold`, and lets you query `{sum, max, min}` over any user-selected time window via a range slider.

This is the canonical demo: it runs entirely offline, has no external dependencies beyond `psutil`/`streamlit`, and never breaks because of an API change. If you want to see what `livefold` is for in 30 seconds of clicking, this is the example.

## Run it

From the repo root:

```bash
uv run --group demo streamlit run examples/system_metrics/app.py
```

The dashboard opens in your browser. Pick a metric (CPU % or Memory %), let it collect data for a few seconds, then drag the range slider to query aggregates over any window.

## What's happening

```python
from livefold import TimeIndexedLiveFold

lf = TimeIndexedLiveFold([], folds={"sum": sum, "max": max, "min": min})

# Every second:
lf.append(psutil.cpu_percent(interval=None), timestamp=elapsed)

# When the user picks a time range [t1, t2]:
stats = lf.query_time_range(t1, t2)
# → {"sum": ..., "max": ..., "min": ...}  in O(√n)
```

The point of using `TimeIndexedLiveFold` here — instead of just calling `sum/max/min(values[i:j])` — is that the per-query cost stays sublinear as the session grows. After an hour of polling, that's ~3,600 readings and a query touches ~60 of them per fold, not 3,600.

## Try this

- Run a CPU-heavy task in another terminal (e.g., `yes > /dev/null`) and watch the chart spike. Then use the slider to query the max during that window vs. the rest of the session.
- Switch between CPU % and Memory % — the same `TimeIndexedLiveFold` instance resets, but the API shape doesn't change.
- Leave it running for a while. Notice that query latency stays flat regardless of session length — that's `O(√n)` doing its job.

## Adapting this to your data

Swap the `psutil` call for any source of numeric readings:

- HTTP request latencies from a load test
- Temperature readings from an IoT sensor
- Job durations from a queue worker
- Any stream where you'd otherwise reach for `pandas.Series` and regret it
