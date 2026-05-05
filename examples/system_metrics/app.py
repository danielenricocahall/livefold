"""Live system metrics demo.

Polls CPU/memory once per second, appends to a TimeIndexedLiveFold, and
lets you query the sum/max/min over any time window via a range slider.

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

from livefold import InvalidRangeException, TimeIndexedLiveFold

st.set_page_config(
    page_title="livefold — live system metrics", page_icon="📊", layout="wide"
)

st_autorefresh(interval=1000, key="tick")


def init_state() -> None:
    if "lf" not in st.session_state:
        st.session_state.lf = TimeIndexedLiveFold(
            [], folds={"sum": sum, "max": max, "min": min}
        )
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
    elapsed = time.time() - st.session_state.start
    st.session_state.lf.append(value, timestamp=elapsed)


def reset() -> None:
    for key in ("lf", "start", "window_slider"):
        st.session_state.pop(key, None)


init_state()

st.title("livefold — live system metrics")
st.caption(
    "Live `psutil` readings appended to a `TimeIndexedLiveFold` once per second. "
    "Drag the slider to query any time window — "
    "`livefold.query_time_range(t₁, t₂)` returns `{sum, max, min}` in O(√n)."
)

col_l, col_r = st.columns([1, 4])
with col_l:
    metric = st.selectbox("Metric", ["CPU %", "Memory %"], index=0)
    if st.button("Reset"):
        reset()
        st.rerun()

append_reading(metric)

ts = st.session_state.lf.timestamps
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
# Initialize once; on subsequent reruns clamp the persisted value to
# current bounds without passing value= (which would reset the widget).
if "window_slider" not in st.session_state:
    st.session_state["window_slider"] = (t_min, t_max)
else:
    lo, hi = st.session_state["window_slider"]
    st.session_state["window_slider"] = (
        max(t_min, min(t_max, lo)),
        max(t_min, min(t_max, hi)),
    )

window = st.slider(
    "Range to aggregate (seconds since start)",
    min_value=t_min,
    max_value=t_max,
    step=1.0,
    key="window_slider",
)

try:
    stats = st.session_state.lf.query_time_range(window[0], window[1])
    span = bisect.bisect_right(ts, window[1]) - bisect.bisect_left(ts, window[0])
    mean = stats["sum"] / span

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric(
        "Samples in window",
        f"{span:,}",
        delta=f"over {window[1] - window[0]:.1f}s",
        delta_color="off",
    )
    m2.metric("Sum", f"{stats['sum']:.1f}")
    m3.metric("Max", f"{stats['max']:.2f}")
    m4.metric("Min", f"{stats['min']:.2f}")
    m5.metric("Mean (sum/n)", f"{mean:.2f}")
except InvalidRangeException:
    st.warning("Pick a wider range — need at least two samples.")

with st.expander("How this works"):
    st.markdown(
        """
        Every second, the script appends the latest `psutil` reading to a
        single `TimeIndexedLiveFold` instance held in `st.session_state`,
        with the elapsed-since-start timestamp:

        ```python
        lf = TimeIndexedLiveFold(
            [], folds={"sum": sum, "max": max, "min": min}
        )
        # ...each rerun:
        lf.append(psutil.cpu_percent(interval=None), timestamp=elapsed)
        ```

        When you drag the slider, we call
        `lf.query_time_range(t1, t2)` — bisect maps the time bounds to
        indices in O(log n), and the underlying √n-decomposed query
        returns `{sum, max, min}` in **O(√n)** regardless of how long
        this session has been running.

        Replace this with any numeric stream — request latencies, sensor
        readings, trade prices — and the same primitive applies.
        """
    )
