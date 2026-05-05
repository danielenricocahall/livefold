"""Render an animated GIF illustrating LiveFold's re-blocking on a
perfect-square boundary append.

Walks through `lf.append(5)` taking n from 8 → 9, which crosses the
isqrt threshold (isqrt(8) = 2, isqrt(9) = 3) and forces the whole
structure to re-block from 4×2 to 3×3. The final state matches the
query animation's starting state, so the two animations tell a
continuous story.

Run with:  uv run --group bench python assets/render_resize_animation.py
Output: assets/resize_animation.gif
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

DATA_BEFORE = [3, 1, 4, 1, 5, 9, 2, 6]
NEW_ELEMENT = 5
DATA_AFTER = DATA_BEFORE + [NEW_ELEMENT]

BLOCK_SIZE_BEFORE = 2
BLOCK_SIZE_AFTER = 3

BLOCKS_BEFORE = [
    DATA_BEFORE[i : i + BLOCK_SIZE_BEFORE]
    for i in range(0, len(DATA_BEFORE), BLOCK_SIZE_BEFORE)
]
BLOCKS_AFTER = [
    DATA_AFTER[i : i + BLOCK_SIZE_AFTER]
    for i in range(0, len(DATA_AFTER), BLOCK_SIZE_AFTER)
]
SUMS_BEFORE = [sum(b) for b in BLOCKS_BEFORE]
SUMS_AFTER = [sum(b) for b in BLOCKS_AFTER]

IDLE_CELL = "#e5e7eb"
NEW_CELL = "#fbbf24"
REBLOCK = "#a78bfa"
REFOLD = "#34d399"
TEXT_DARK = "#111827"
TEXT_MUTED = "#6b7280"

NUM_PHASES = 6
PHASE_DURATIONS = [1, 1, 1, 1, 1, 3]  # final settled state holds for 3s


def phase_for_frame(frame: int) -> int:
    cumulative = 0
    for phase, duration in enumerate(PHASE_DURATIONS):
        cumulative += duration
        if frame < cumulative:
            return phase
    return NUM_PHASES - 1


def _draw_cell(ax, i: int, val: int, color: str) -> None:
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
        i + 0.5, 2.15, str(i), ha="center", va="center", fontsize=9, color=TEXT_MUTED
    )


def _draw_block_bracket(
    ax, start_idx: int, block_size: int, sum_value: int, color: str
) -> None:
    start_x = start_idx + 0.05
    end_x = start_x + block_size - 0.1
    ax.plot(
        [start_x, start_x, end_x, end_x],
        [0.95, 0.65, 0.65, 0.95],
        color="#374151",
        lw=1.5,
    )
    ax.text(
        (start_x + end_x) / 2,
        0.15,
        f"sum = {sum_value}",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color=TEXT_DARK,
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor=color,
            edgecolor="#374151",
            linewidth=1.0,
        ),
    )


def draw(frame: int, ax) -> None:
    phase = phase_for_frame(frame)
    ax.clear()
    ax.set_xlim(-0.6, 9.6)
    ax.set_ylim(-2.6, 3.0)
    ax.set_aspect("equal")
    ax.axis("off")

    if phase == 0:
        title = "n = 8, block_size = isqrt(8) = 2"
    elif phase == 1:
        title = "lf.append(5)"
    elif phase == 2:
        title = "n = 9 — old layout no longer fits"
    elif phase == 3:
        title = "isqrt(9) = 3 → re-block from 4×2 to 3×3"
    elif phase == 4:
        title = "recompute folds for the new blocks"
    else:
        title = "amortized O(1) — re-blocks only at perfect squares"

    ax.text(
        4.5,
        2.55,
        title,
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=TEXT_DARK,
    )

    if phase == 0:
        cells = DATA_BEFORE
    else:
        cells = DATA_AFTER

    for i, val in enumerate(cells):
        color = IDLE_CELL
        if phase in (1, 2) and i == len(DATA_BEFORE):
            color = NEW_CELL
        _draw_cell(ax, i, val, color)

    if phase <= 2:
        for b_idx, block in enumerate(BLOCKS_BEFORE):
            _draw_block_bracket(
                ax,
                b_idx * BLOCK_SIZE_BEFORE,
                BLOCK_SIZE_BEFORE,
                SUMS_BEFORE[b_idx],
                IDLE_CELL,
            )
    else:
        for b_idx, block in enumerate(BLOCKS_AFTER):
            color = REBLOCK if phase == 3 else REFOLD if phase == 4 else IDLE_CELL
            _draw_block_bracket(
                ax,
                b_idx * BLOCK_SIZE_AFTER,
                BLOCK_SIZE_AFTER,
                SUMS_AFTER[b_idx],
                color,
            )

    annotations: list[tuple[str, str]] = []
    if phase == 1:
        annotations.append(("appending value 5 at index 8", NEW_CELL))
    elif phase == 2:
        annotations.append(("4 blocks of size 2 cover only 8 cells", NEW_CELL))
        annotations.append(("isqrt(9) = 3 ≠ 2 → trigger re-block", REBLOCK))
    elif phase == 3:
        annotations.append(("blocks recomputed: [3,1,4] [1,5,9] [2,6,5]", REBLOCK))
    elif phase == 4:
        annotations.append(("sums recomputed: 8, 15, 13", REFOLD))
    elif phase == 5:
        annotations.append(("re-block cost is O(n), but happens only at", TEXT_MUTED))
        annotations.append(("n = 4, 9, 16, 25, … (perfect squares)", TEXT_MUTED))
        annotations.append(("→ amortized O(1) per append over the long run", REFOLD))

    for i, (text, color) in enumerate(annotations):
        if color == TEXT_MUTED:
            ax.text(
                4.5,
                -0.7 - i * 0.4,
                text,
                ha="center",
                va="center",
                fontsize=10,
                color=TEXT_MUTED,
                style="italic",
            )
        else:
            ax.text(
                4.5,
                -0.7 - i * 0.4,
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

    out = Path(__file__).parent / "resize_animation.gif"
    anim.save(out, writer=PillowWriter(fps=1))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
