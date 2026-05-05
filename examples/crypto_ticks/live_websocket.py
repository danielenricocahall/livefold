"""Drop-in replacement for the synthetic tick generator in app.py — uses
the real Binance public WebSocket (no API key required).

To use: copy `binance_tick_thread` and the queue plumbing into app.py,
replace `append_ticks` with `drain_queue`, and delete the synthetic
GBM helpers. The rest of the demo (TimeIndexedLiveFold, chart, range
slider) stays exactly the same.

Caveat: Binance occasionally changes endpoint URLs or rate-limits.
The synthetic version is the canonical demo for that reason.
"""

from __future__ import annotations

import json
import queue
import threading

import websockets.sync.client


BINANCE_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"


def binance_tick_thread(out_queue: queue.Queue, stop: threading.Event) -> None:
    """Subscribe to BTC/USDT trades and push (timestamp_ms, price) tuples
    into out_queue until stop is set."""
    with websockets.sync.client.connect(BINANCE_URL) as ws:
        while not stop.is_set():
            msg = ws.recv(timeout=5)
            payload = json.loads(msg)
            ts_ms = payload["T"]
            price = float(payload["p"])
            out_queue.put((ts_ms, price))


def drain_queue(q: queue.Queue, lf, start_ms: int) -> None:
    """Drain whatever the websocket thread has buffered into the LiveFold."""
    while True:
        try:
            ts_ms, price = q.get_nowait()
        except queue.Empty:
            return
        lf.append(price, timestamp=(ts_ms - start_ms) / 1000.0)


# Streamlit wiring sketch — adapt into app.py:
#
#     if "tick_q" not in st.session_state:
#         st.session_state.tick_q = queue.Queue(maxsize=10_000)
#         st.session_state.stop = threading.Event()
#         t = threading.Thread(
#             target=binance_tick_thread,
#             args=(st.session_state.tick_q, st.session_state.stop),
#             daemon=True,
#         )
#         t.start()
#
#     drain_queue(
#         st.session_state.tick_q,
#         st.session_state.lf,
#         st.session_state.start_ms,
#     )
