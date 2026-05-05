"""Render an animated GIF illustrating LiveFold's √n-decomposed query.

Walks through `query(2, 7)` on a 9-element list with 3 blocks of size 3:
   1. Idle state with precomputed per-block sums
   2. Query is announced
   3. Left partial block is scanned (1 element)
   4. Middle whole block uses its precomputed fold (no scan)
   5. Right partial block is scanned (2 elements)
   6. Combined answer revealed

Run with:  uv run --group bench python -m assets.render_query_animation
Output: assets/query_animation.gif
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

DATA = [3, 1, 4, 1, 5, 9, 2, 6, 5]
BLOCK_SIZE = 3
BLOCKS = [DATA[i : i + BLOCK_SIZE] for i in range(0, len(DATA), BLOCK_SIZE)]
BLOCK_SUMS = [sum(b) for b in BLOCKS]

QUERY_LEFT, QUERY_RIGHT = 2, 7  # inclusive

IDLE_CELL = "#e5e7eb"
PARTIAL = "#fbbf24"
PRECOMPUTED = "#a78bfa"
ANSWER = "#34d399"
TEXT_DARK = "#111827"
TEXT_MUTED = "#6b7280"

NUM_PHASES = 6
# Hold each phase by emitting one frame per phase + extra holds on the answer.
# Total frames at fps=1 → seconds in the GIF.
PHASE_DURATIONS = [1, 1, 1, 1, 1, 3]  # final answer holds for 3 seconds


def phase_for_frame(frame: int) -> int:
    cumulative = 0
    for phase, duration in enumerate(PHASE_DURATIONS):
        cumulative += duration
        if frame < cumulative:
            return phase
    return NUM_PHASES - 1


def draw(frame: int, ax) -> None:
    phase = phase_for_frame(frame)
    ax.clear()
    ax.set_xlim(-0.6, 9.6)
    ax.set_ylim(-2.6, 3.0)
    ax.set_aspect("equal")
    ax.axis("off")

    title = "LiveFold(data, folds={'sum': sum})"
    if phase >= 1:
        title = "query(left=2, right=7) → ?"
    if phase >= 5:
        title = "query(left=2, right=7) → 27"
    ax.text(
        4.5,
        2.55,
        title,
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=TEXT_DARK,
    )

    for i, val in enumerate(DATA):
        color = IDLE_CELL
        if phase >= 2 and i == QUERY_LEFT:
            color = PARTIAL
        if phase >= 4 and QUERY_RIGHT - 1 <= i <= QUERY_RIGHT:
            color = PARTIAL
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (i + 0.05, 1.05),
                0.9,
                0.9,
                boxstyle="round,pad=0.02,rounding_size=0.08",
                facecolor=color,
                edgecolor="black",
                linewidth=1.2,
            )
        )
        ax.text(
            i + 0.5,
            1.5,
            str(val),
            ha="center",
            va="center",
            fontweight="bold",
            fontsize=14,
            color=TEXT_DARK,
        )
        ax.text(
            i + 0.5,
            2.15,
            str(i),
            ha="center",
            va="center",
            fontsize=9,
            color=TEXT_MUTED,
        )

    for b_idx in range(len(BLOCKS)):
        start_x = b_idx * BLOCK_SIZE + 0.05
        end_x = start_x + BLOCK_SIZE - 0.1
        ax.plot(
            [start_x, start_x, end_x, end_x],
            [0.95, 0.65, 0.65, 0.95],
            color="#374151",
            lw=1.5,
        )

        block_color = IDLE_CELL
        if phase == 3 and b_idx == 1:
            block_color = PRECOMPUTED
        elif phase >= 4 and b_idx == 1:
            block_color = PRECOMPUTED

        label = f"sum = {BLOCK_SUMS[b_idx]}"
        ax.text(
            (start_x + end_x) / 2,
            0.15,
            label,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color=TEXT_DARK,
            bbox=dict(
                boxstyle="round,pad=0.4",
                facecolor=block_color,
                edgecolor="#374151",
                linewidth=1.0,
            ),
        )

    annotations: list[tuple[str, str]] = []
    if phase >= 2:
        annotations.append(("left partial → scan data[2] = 4", PARTIAL))
    if phase >= 3:
        annotations.append(("middle block → reuse precomputed sum = 15", PRECOMPUTED))
    if phase >= 4:
        annotations.append(("right partial → scan data[6:8] = 2 + 6 = 8", PARTIAL))
    if phase >= 5:
        annotations.append(("answer = 4 + 15 + 8 = 27", ANSWER))

    for i, (text, color) in enumerate(annotations):
        ax.text(
            4.5,
            -0.7 - i * 0.45,
            text,
            ha="center",
            va="center",
            fontsize=11,
            color=TEXT_DARK,
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor=color,
                edgecolor="none",
                alpha=0.7,
            ),
        )


def main() -> None:
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=100)
    fig.patch.set_facecolor("white")

    total_frames = sum(PHASE_DURATIONS)
    anim = FuncAnimation(
        fig,
        lambda f: draw(f, ax),
        frames=total_frames,
        interval=1000,
        blit=False,
    )

    out = Path(__file__).parent / "query_animation.gif"
    anim.save(out, writer=PillowWriter(fps=1))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
