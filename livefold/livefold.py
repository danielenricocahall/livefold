import copy as _copy

from math import sqrt, floor
from typing import Any, Iterable, Callable


class InvalidRangeException(Exception): ...


class LiveFold(list):
    def __init__(self, data: Iterable[Any], folds: dict[str, Callable]):
        super().__init__(data)
        self.folds = folds
        self._blocks = self.compute_blocks()

    @property
    def block_size(self):
        return floor(sqrt(len(self)))

    @property
    def block_count(self):
        return floor(len(self) / self.block_size)

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
        if not self.block_size:
            return []
        return [
            self[i : i + self.block_size]
            for i in range(start_index, len(self), self.block_size)
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
            self.blocks[block_index].insert(__index % block_size, __object)
            self.blocks[block_index:] = self.compute_blocks(block_index * block_size)
            self._refold_from(block_index)

    def sort(self, *, key=None, reverse=False):
        super().sort(key=key, reverse=reverse)
        self.blocks = self.compute_blocks()

    def extend(self, __iterable):
        block_size = self.block_size
        super().extend(__iterable)
        new_block_size = self.block_size
        if new_block_size != block_size:
            self.blocks = self.compute_blocks()
        else:
            if (index := self.block_size - len(self.blocks[-1])) > 0:
                self._merge_into_last_block_folds(__iterable[:index])
                self.blocks[-1] += __iterable[:index]
                __iterable = __iterable[index:]
            self.__extend_blocks(__iterable)

    def __extend_blocks(self, iterable):
        new_blocks = [
            iterable[i : i + self.block_size]
            for i in range(0, len(iterable), self.block_size)
        ]
        self.blocks.extend(new_blocks)
        self._extend_block_folds(new_blocks)

    def pop(self, __index=-1):
        block_size = self.block_size
        value = super().pop(__index)
        new_block_size = self.block_size
        if new_block_size != block_size:
            self.blocks = self.compute_blocks()
        else:
            block_index = __index // block_size
            self.blocks[block_index].pop(__index % block_size if __index >= 0 else -1)
            if len(self.blocks[block_index]) == 0:
                del self.blocks[block_index]
                for name in self.folds:
                    del self.folded_values[name][block_index]
            else:
                self.blocks[block_index:] = self.compute_blocks(
                    block_index * block_size
                )
                self._refold_from(block_index)
        return value

    def remove(self, __value):
        index = self.index(__value)
        if index == -1:
            raise ValueError(f"{__value} not in list")
        self.pop(index)

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
            block_index = key // self.block_size
            self.blocks[block_index][key % self.block_size] = value
            self._refold_at(block_index)

    def __delitem__(self, key):
        super().__delitem__(key)
        self.blocks = self.compute_blocks()

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
        if right - left <= 0 or right > len(self) or left < 0:
            raise InvalidRangeException(
                f"Invalid range of {left} - {right}. Please supply a valid range!"
            )
        left_block = left // self.block_size
        right_block = right // self.block_size
        left_block_start_index = left_block * self.block_size
        left_block_end_index = left_block_start_index + len(self.blocks[left_block]) - 1
        right_block_start_index = right_block * self.block_size
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
                self.folded_values[name][left_block + 1 : right_block]
                + [initial_value[name], final_value[name]]
            )
            for name, fn in self.folds.items()
        }

    def clear(self):
        super().clear()
        self.blocks = []
        self.folded_values = {name: [] for name in self.folds}
