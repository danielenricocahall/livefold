"""Backend adapters for benchmarking. All implement build/append/query
returning a {sum, max, min} dict so the comparison is apples-to-apples."""

from __future__ import annotations

import numpy as np
import pandas as pd

from livefold import LiveFold


class NaiveBackend:
    name = "naive"

    def __init__(self, data: list[float]) -> None:
        self.data = list(data)

    def append(self, value: float) -> None:
        self.data.append(value)

    def query(self, left: int, right: int) -> dict[str, float]:
        sub = self.data[left : right + 1]
        return {"sum": sum(sub), "max": max(sub), "min": min(sub)}


class PrefixSumBackend:
    """Prefix sums for sum; naive scan for max/min.

    Honest representation of how a user would extend prefix sums to multi-fold:
    sum is O(1), max/min stay O(n) per query because no prefix structure exists
    that survives mutations cheaply."""

    name = "prefix_sums"

    def __init__(self, data: list[float]) -> None:
        self.data = list(data)
        self.prefix = [0.0]
        for v in self.data:
            self.prefix.append(self.prefix[-1] + v)

    def append(self, value: float) -> None:
        self.data.append(value)
        self.prefix.append(self.prefix[-1] + value)

    def query(self, left: int, right: int) -> dict[str, float]:
        sub = self.data[left : right + 1]
        return {
            "sum": self.prefix[right + 1] - self.prefix[left],
            "max": max(sub),
            "min": min(sub),
        }


class NumpyBackend:
    """np.ndarray; appends via np.append (O(n) rebuild — the canonical
    one-element-at-a-time pattern for users who haven't reached for a
    geometrically-growing buffer)."""

    name = "numpy"

    def __init__(self, data: list[float]) -> None:
        self.arr = np.array(data, dtype=float)

    def append(self, value: float) -> None:
        self.arr = np.append(self.arr, value)

    def query(self, left: int, right: int) -> dict[str, float]:
        sub = self.arr[left : right + 1]
        return {
            "sum": float(sub.sum()),
            "max": float(sub.max()),
            "min": float(sub.min()),
        }


class PandasBackend:
    """pd.Series; rebuilt on append, which is the canonical pattern for
    users who want a Series for query ergonomics."""

    name = "pandas"

    def __init__(self, data: list[float]) -> None:
        self.data = list(data)
        self._series = pd.Series(self.data, dtype=float)

    def append(self, value: float) -> None:
        self.data.append(value)
        self._series = pd.Series(self.data, dtype=float)

    def query(self, left: int, right: int) -> dict[str, float]:
        sub = self._series.iloc[left : right + 1]
        return {
            "sum": float(sub.sum()),
            "max": float(sub.max()),
            "min": float(sub.min()),
        }


class LiveFoldBackend:
    name = "livefold"

    def __init__(self, data: list[float]) -> None:
        self.lf = LiveFold(list(data), folds={"sum": sum, "max": max, "min": min})

    def append(self, value: float) -> None:
        self.lf.append(value)

    def query(self, left: int, right: int) -> dict[str, float]:
        return self.lf.query(left, right)


BACKENDS = [
    NaiveBackend,
    PrefixSumBackend,
    NumpyBackend,
    PandasBackend,
    LiveFoldBackend,
]
