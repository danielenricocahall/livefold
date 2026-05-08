import bisect
import copy as _copy
import time

from math import isqrt
from typing import Any, Generic, Iterable, Callable, TypeVar

T = TypeVar("T")


class InvalidRangeException(Exception): ...


class InvalidFoldException(Exception): ...


class MonotonicityError(Exception): ...


class LiveFold(list):
    def __init__(self, data: Iterable[Any], folds: dict[str, Callable]):
        super().__init__(data)
        if not folds:
            raise InvalidFoldException(
                "Cannot initialize LiveFold with no `folds` provided"
            )
        self.folds = folds
        self._blocks = self.compute_blocks()

    @property
    def block_size(self):
        return isqrt(len(self))

    @property
    def block_count(self):
        if not len(self):
            return 0
        return len(self) // self.block_size

    @property
    def blocks(self):
        return self._blocks

    @blocks.setter
    def blocks(self, blocks_):
        self._blocks = blocks_
        if hasattr(self, "_folded_values"):
            del self._folded_values

    @property
    def folded_values(self):
        if not hasattr(self, "_folded_values"):
            self.folded_values = {
                name: list(map(fn, self.blocks)) for name, fn in self.folds.items()
            }
        return self._folded_values

    @folded_values.setter
    def folded_values(self, values):
        self._folded_values = values

    def _fold_each(self, items) -> dict[str, Any]:
        return {name: fn(items) for name, fn in self.folds.items()}

    def _block_folds(self, block_index: int) -> dict[str, Any]:
        return {name: self.folded_values[name][block_index] for name in self.folds}

    def _refold_from(self, block_index: int) -> None:
        for name, fn in self.folds.items():
            self.folded_values[name][block_index:] = list(
                map(fn, self.blocks[block_index:])
            )

    def _refold_at(self, block_index: int) -> None:
        for name, fn in self.folds.items():
            self.folded_values[name][block_index] = fn(self.blocks[block_index])

    def _merge_into_last_block_folds(self, prefix) -> None:
        for name, fn in self.folds.items():
            self.folded_values[name][-1] = fn([self.folded_values[name][-1], *prefix])

    def _extend_block_folds(self, new_blocks) -> None:
        for name, fn in self.folds.items():
            self.folded_values[name].extend(map(fn, new_blocks))

    def compute_blocks(self, start_index: int = 0):
        block_size = self.block_size
        if not block_size:
            return []
        return [
            self[i : i + block_size] for i in range(start_index, len(self), block_size)
        ]

    def append(self, __object):
        self.extend([__object])

    def insert(self, __index, __object):
        block_size = self.block_size
        super().insert(__index, __object)
        new_block_size = self.block_size
        if new_block_size != block_size:
            self.blocks = self.compute_blocks()
        else:
            block_index = __index // block_size
            self.blocks[block_index:] = self.compute_blocks(block_index * block_size)
            self._refold_from(block_index)

    def sort(self, *, key=None, reverse=False):
        super().sort(key=key, reverse=reverse)
        self.blocks = self.compute_blocks()

    def extend(self, __iterable):
        __iterable = list(__iterable)
        block_size = self.block_size
        super().extend(__iterable)
        new_block_size = self.block_size
        if new_block_size != block_size:
            self.blocks = self.compute_blocks()
        else:
            if (index := block_size - len(self.blocks[-1])) > 0:
                self._merge_into_last_block_folds(__iterable[:index])
                self.blocks[-1] += __iterable[:index]
                __iterable = __iterable[index:]
            self.__extend_blocks(__iterable)

    def __extend_blocks(self, iterable):
        block_size = self.block_size
        new_blocks = [
            iterable[i : i + block_size] for i in range(0, len(iterable), block_size)
        ]
        self.blocks.extend(new_blocks)
        self._extend_block_folds(new_blocks)

    def pop(self, __index=-1):
        block_size = self.block_size
        n = len(self)
        value = super().pop(__index)
        new_block_size = self.block_size
        if new_block_size != block_size:
            self.blocks = self.compute_blocks()
        else:
            idx = __index if __index >= 0 else n + __index
            block_index = idx // block_size
            self.blocks[block_index:] = self.compute_blocks(block_index * block_size)
            self._refold_from(block_index)
        return value

    def remove(self, __value):
        self.pop(self.index(__value))

    def reverse(self):
        super().reverse()
        self.blocks = self.compute_blocks()

    def __add__(self, other):
        return LiveFold(super().__add__(other), self.folds)

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if isinstance(key, slice):
            # TODO: for slice assignment we recompute all blocks - this can be optimized but
            # requires more thought for all edge cases
            self.blocks = self.compute_blocks()
        else:
            if key < 0:
                key += len(self)
            block_size = self.block_size
            block_index = key // block_size
            self.blocks[block_index][key % block_size] = value
            self._refold_at(block_index)

    def __delitem__(self, key):
        if isinstance(key, slice):
            super().__delitem__(key)
            self.blocks = self.compute_blocks()
        else:
            self.pop(key)

    def copy(self):
        return LiveFold(list(self), self.folds)

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memo):
        return LiveFold(
            _copy.deepcopy(list(self), memo),
            self.folds,
        )

    def __reduce__(self):
        return (
            self.__class__,
            (list(self), self.folds),
        )

    def query(self, left: int, right: int):
        if right - left < 0 or right >= len(self) or left < 0:
            raise InvalidRangeException(
                f"Invalid range of {left} - {right}. Please supply a valid range!"
            )
        block_size = self.block_size
        left_block = left // block_size
        right_block = right // block_size
        left_block_start_index = left_block * block_size
        left_block_end_index = left_block_start_index + len(self.blocks[left_block]) - 1
        right_block_start_index = right_block * block_size
        right_block_end_index = (
            right_block_start_index + len(self.blocks[right_block]) - 1
        )
        if left_block == right_block:
            if left == left_block_start_index and right == right_block_end_index:
                return self._block_folds(left_block)
            return self._fold_each(self[left : right + 1])
        if left != left_block_start_index:
            initial_value = self._fold_each(self[left : left_block_end_index + 1])
        else:
            initial_value = self._block_folds(left_block)
        if right != right_block_end_index:
            final_value = self._fold_each(self[right_block_start_index : right + 1])
        else:
            final_value = self._block_folds(right_block)
        return {
            name: fn(
                [initial_value[name]]
                + self.folded_values[name][left_block + 1 : right_block]
                + [final_value[name]]
            )
            for name, fn in self.folds.items()
        }

    def clear(self):
        super().clear()
        self.blocks = []
        self.folded_values = {name: [] for name in self.folds}


class TimeIndexedLiveFold(LiveFold, Generic[T]):
    """LiveFold with monotonically non-decreasing timestamps per element.

    Generic over `T`, the timestamp type. Any orderable type works
    (`float`, `int`, `datetime`, etc.) — the implementation only uses `<`
    and `bisect`, which require mutual comparability of stored timestamps.

    The `timestamp=None` defaults in `__init__`, `append`, and `extend`
    fall back to `time.time()` (a `float`). This default only makes sense
    for `T = float`; for any other type, pass timestamps explicitly.
    """

    def __init__(
        self,
        data: Iterable[Any],
        folds: dict[str, Callable],
        timestamps: list[T] | None = None,
    ):
        super().__init__(data, folds)
        if timestamps is not None:
            if len(timestamps) != len(self):
                raise ValueError(
                    f"Timestamps and data length must match, got {len(timestamps)} and {len(self)}"
                )
            self._timestamps: list[T] = []
            self._check_monotonic(timestamps)
            self._timestamps = list(timestamps)
        else:
            self._timestamps: list[T] = [time.time() for _ in range(len(self))]

    @property
    def timestamps(self) -> list[T]:
        return self._timestamps

    def append(self, __object, timestamp: T | None = None):
        self.extend([__object], [timestamp] if timestamp is not None else None)

    def extend(self, __iterable, timestamps: list[T] | None = None):
        __iterable = list(__iterable)
        if timestamps is None:
            timestamps = [time.time() for _ in __iterable]
        else:
            if len(timestamps) != len(__iterable):
                raise ValueError(
                    f"Timestamps and iterable lengths must match, got {len(timestamps)} and {len(__iterable)}"
                )
            self._check_monotonic(timestamps)
        super().extend(__iterable)
        self._timestamps.extend(timestamps)

    def _check_monotonic(self, new_timestamps: list[T]) -> None:
        prev = self._timestamps[-1] if self._timestamps else None
        for ts in new_timestamps:
            if prev is not None and ts < prev:
                raise MonotonicityError(
                    f"non-monotonic timestamp: {ts} precedes {prev}"
                )
            prev = ts

    def insert(self, __index, __object):
        raise MonotonicityError(
            "insert is not supported on TimeIndexedLiveFold; use append to preserve time ordering"
        )

    def sort(self, *, key=None, reverse=False):
        raise MonotonicityError(
            "sort is not supported on TimeIndexedLiveFold; sorting would break time ordering"
        )

    def reverse(self):
        raise MonotonicityError(
            "reverse is not supported on TimeIndexedLiveFold; reversing would break time ordering"
        )

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            raise MonotonicityError(
                "slice assignment is not supported on TimeIndexedLiveFold; "
                "it would not preserve alignment with stored timestamps"
            )
        super().__setitem__(key, value)

    def __delitem__(self, key):
        if isinstance(key, slice):
            raise MonotonicityError(
                "slice deletion is not supported on TimeIndexedLiveFold; use pop or remove"
            )
        # super().__delitem__ routes int keys through self.pop, which we override
        # to handle timestamps; no separate timestamp removal needed here.
        super().__delitem__(key)

    def __add__(self, other):
        if not isinstance(other, TimeIndexedLiveFold):
            raise MonotonicityError(
                "+ only supports TimeIndexedLiveFold + TimeIndexedLiveFold; "
                "use extend(values, timestamps=...) for other inputs"
            )
        self._check_monotonic(other.timestamps)
        return TimeIndexedLiveFold(
            list(self) + list(other),
            self.folds,
            timestamps=self.timestamps + other.timestamps,
        )

    def __iadd__(self, other):
        if not isinstance(other, TimeIndexedLiveFold):
            raise MonotonicityError(
                "+= only supports TimeIndexedLiveFold + TimeIndexedLiveFold; "
                "use extend(values, timestamps=...) for other inputs"
            )
        self.extend(list(other), timestamps=list(other.timestamps))
        return self

    def copy(self):
        return TimeIndexedLiveFold(
            list(self), self.folds, timestamps=list(self._timestamps)
        )

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memo):
        return TimeIndexedLiveFold(
            _copy.deepcopy(list(self), memo),
            self.folds,
            timestamps=_copy.deepcopy(self._timestamps, memo),
        )

    def __reduce__(self):
        return (
            self.__class__,
            (list(self), self.folds, list(self._timestamps)),
        )

    def pop(self, __index=-1):
        value = super().pop(__index)
        self.timestamps.pop(__index)
        return value

    def clear(self):
        super().clear()
        self.timestamps.clear()

    def __repr__(self) -> str:
        return f"TimeIndexedLiveFold({list(self)!r}, timestamps={self._timestamps!r})"

    def query_time_range(self, start: T, end: T):
        left = bisect.bisect_left(self.timestamps, start)
        right = bisect.bisect_right(self.timestamps, end) - 1
        try:
            return super().query(left, right)
        except InvalidRangeException as e:
            raise InvalidRangeException(
                f"No elements in time range: [{start}, {end}]"
            ) from e
