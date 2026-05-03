"""Live system metrics demo.

Polls CPU/memory once per second, appends to a LiveFold, and lets you
query the sum/max/min over any time window via a range slider.

Run with:
    uv run --group demo streamlit run examples/system_metrics/app.py
"""

from __future__ import annotations

import bisect
import time

import plotly.graph_objects as go
import psutil
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from livefold import LiveFold

st.set_page_config(
    page_title="livefold — live system metrics", page_icon="📊", layout="wide"
)

st_autorefresh(interval=1000, key="tick")


def init_state() -> None:
    if "lf" not in st.session_state:
        st.session_state.lf = LiveFold([], folds={"sum": sum, "max": max, "min": min})
        st.session_state.timestamps = []
        st.session_state.start = time.time()
        # prime psutil so the first non-blocking call returns a real number
        psutil.cpu_percent(interval=None)


def append_reading(metric: str) -> None:
    if metric == "CPU %":
        value = psutil.cpu_percent(interval=None)
    elif metric == "Memory %":
        value = psutil.virtual_memory().percent
    else:
        raise ValueError(f"unknown metric: {metric}")
    st.session_state.lf.append(value)
    st.session_state.timestamps.append(time.time() - st.session_state.start)


def reset() -> None:
    for key in ("lf", "timestamps", "start"):
        st.session_state.pop(key, None)


init_state()

st.title("livefold — live system metrics")
st.caption(
    "Live `psutil` readings appended to a `LiveFold` once per second. "
    "Drag the slider to query any time window — "
    "`livefold.query(t₁, t₂)` returns `{sum, max, min}` in O(√n)."
)

col_l, col_r = st.columns([1, 4])
with col_l:
    metric = st.selectbox("Metric", ["CPU %", "Memory %"], index=0)
    if st.button("Reset"):
        reset()
        st.rerun()

append_reading(metric)

ts = st.session_state.timestamps
n = len(ts)
values = list(st.session_state.lf)

with col_r:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ts,
            y=values,
            mode="lines",
            line=dict(color="#7c3aed", width=2),
            name=metric,
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=40, r=20, t=10, b=40),
        xaxis_title="seconds since start",
        yaxis_title=metric,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

if n < 2:
    st.info("Collecting readings… give it a couple of seconds.")
    st.stop()

t_min, t_max = float(ts[0]), float(ts[-1])
window = st.slider(
    "Range to aggregate (seconds since start)",
    min_value=t_min,
    max_value=t_max,
    value=(t_min, t_max),
    step=1.0,
)

left_idx = bisect.bisect_left(ts, window[0])
right_idx = bisect.bisect_right(ts, window[1]) - 1
right_idx = min(right_idx, n - 1)

if right_idx > left_idx:
    stats = st.session_state.lf.query(left_idx, right_idx)
    span = right_idx - left_idx + 1
    mean = stats["sum"] / span

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Samples in window", f"{span:,}")
    m2.metric("Sum", f"{stats['sum']:.1f}")
    m3.metric("Max", f"{stats['max']:.2f}")
    m4.metric("Min", f"{stats['min']:.2f}")
    m5.metric("Mean (sum/n)", f"{mean:.2f}")
else:
    st.warning("Pick a wider range — need at least two samples.")

with st.expander("How this works"):
    st.markdown(
        """
        Every second, the script appends the latest `psutil` reading to a
        single `LiveFold` instance held in `st.session_state`:

        ```python
        lf = LiveFold([], folds={"sum": sum, "max": max, "min": min})
        # ...each rerun:
        lf.append(psutil.cpu_percent(interval=None))
        ```

        When you drag the slider, we map your chosen time window to the
        corresponding index range and call `lf.query(left, right)` —
        which returns `{sum, max, min}` in **O(√n)** regardless of how
        long this session has been running.

        Replace this with any numeric stream — request latencies, sensor
        readings, trade prices — and the same primitive applies.
        """
    )
