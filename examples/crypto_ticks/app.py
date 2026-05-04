"""Live crypto tick demo.

Replays a synthetic BTC/USD tick stream into a LiveFold, with a range
slider for querying high/low over any user-selected time window. The
synthetic stream is reproducible (seeded) and never depends on a live
network feed — see live_websocket.py for the recipe to swap in real
Binance ticks.

Run with:
    uv run --group demo streamlit run examples/crypto_ticks/app.py
"""

from __future__ import annotations

import bisect
import math
import random
import time

import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from livefold import LiveFold

st.set_page_config(
    page_title="livefold — live crypto ticks", page_icon="💸", layout="wide"
)

st_autorefresh(interval=1000, key="tick")

START_PRICE = 60_000.0
TICK_DT = 0.2  # seconds between synthetic ticks
SIGMA = 0.0008  # per-tick volatility
JUMP_PROB = 0.003  # rare news-event jumps
JUMP_SCALE = 0.015


def gen_tick(prev_price: float, rng: random.Random) -> float:
    """One step of geometric Brownian motion with rare jumps."""
    z = rng.gauss(0, 1)
    price = prev_price * math.exp(-0.5 * SIGMA**2 + SIGMA * z)
    if rng.random() < JUMP_PROB:
        price *= 1 + rng.uniform(-JUMP_SCALE, JUMP_SCALE)
    return price


def init_state() -> None:
    if "lf" not in st.session_state:
        st.session_state.lf = LiveFold([], folds={"sum": sum, "max": max, "min": min})
        st.session_state.timestamps = []
        st.session_state.last_price = START_PRICE
        st.session_state.start = time.time()
        st.session_state.rng = random.Random(42)


def append_ticks(rate_multiplier: int) -> None:
    now = time.time() - st.session_state.start
    target_count = int(now / TICK_DT) * rate_multiplier
    while len(st.session_state.timestamps) < target_count:
        next_price = gen_tick(st.session_state.last_price, st.session_state.rng)
        st.session_state.lf.append(next_price)
        next_t = len(st.session_state.timestamps) * TICK_DT / rate_multiplier
        st.session_state.timestamps.append(next_t)
        st.session_state.last_price = next_price


def reset() -> None:
    for key in (
        "lf",
        "timestamps",
        "last_price",
        "start",
        "rng",
        "window_slider",
    ):
        st.session_state.pop(key, None)


init_state()

st.title("livefold — live crypto ticks")
st.caption(
    "Synthetic BTC/USD ticks (geometric Brownian motion + rare jumps, "
    "deterministic with a fixed seed) appended to a `LiveFold`. "
    "Drag the slider to query the high/low/VWAP-numerator over any window."
)

col_l, col_r = st.columns([1, 4])
with col_l:
    rate = st.select_slider(
        "Replay speed", options=[1, 5, 25, 100], value=25, format_func=lambda x: f"{x}x"
    )
    if st.button("Reset"):
        reset()
        st.rerun()

append_ticks(rate)

ts = st.session_state.timestamps
prices = list(st.session_state.lf)
n = len(ts)

with col_r:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ts,
            y=prices,
            mode="lines",
            line=dict(color="#f59e0b", width=2),
            name="BTC/USD",
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=40, r=20, t=10, b=40),
        xaxis_title="seconds (synthetic time)",
        yaxis_title="price (USD)",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

if n < 2:
    st.info("Generating ticks… give it a moment.")
    st.stop()

t_min, t_max = float(ts[0]), float(ts[-1])
# Initialize once; on subsequent reruns clamp the persisted value to
# current bounds without passing value= (which would reset the widget).
if "window_slider" not in st.session_state:
    st.session_state["window_slider"] = (max(t_min, t_max - 30), t_max)
else:
    lo, hi = st.session_state["window_slider"]
    st.session_state["window_slider"] = (
        max(t_min, min(t_max, lo)),
        max(t_min, min(t_max, hi)),
    )

window = st.slider(
    "Range to aggregate (seconds)",
    min_value=t_min,
    max_value=t_max,
    step=1.0,
    key="window_slider",
)

left_idx = bisect.bisect_left(ts, window[0])
right_idx = bisect.bisect_right(ts, window[1]) - 1
right_idx = min(right_idx, n - 1)

if right_idx > left_idx:
    stats = st.session_state.lf.query(left_idx, right_idx)
    span = right_idx - left_idx + 1
    vwap_proxy = stats["sum"] / span  # equal-weighted; real VWAP needs volume

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ticks in window", f"{span:,}")
    m2.metric("High", f"${stats['max']:,.2f}")
    m3.metric("Low", f"${stats['min']:,.2f}")
    m4.metric("Avg price", f"${vwap_proxy:,.2f}")
else:
    st.warning("Pick a wider range — need at least two ticks.")

with st.expander("How this works"):
    st.markdown(
        """
        A single `LiveFold` instance holds the entire price series:

        ```python
        lf = LiveFold([], folds={"sum": sum, "max": max, "min": min})
        # for each incoming tick:
        lf.append(price)
        ```

        When you drag the range slider, we map your time window to indices
        and call `lf.query(left, right)` — which returns `{sum, max, min}`
        in **O(√n)** regardless of how long the stream has been running.

        At a 25× replay rate this generates ~125 ticks/second; after a few
        minutes the underlying series is in the tens of thousands and
        each query still completes in under 100µs (see `benchmarks/`).

        **For real Binance data:** see `live_websocket.py` next to this
        file — drop-in replacement for the synthetic tick generator.
        """
    )
