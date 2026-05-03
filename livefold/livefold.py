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
            _folded_values = {}
            for fold_name, fold_func in self.folds.items():
                _folded_values[fold_name] = list(map(fold_func, self.blocks))
            self.folded_values = _folded_values
        return self._folded_values

    @folded_values.setter
    def folded_values(self, values):
        self._folded_values = values

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
            for fold_name, fold_func in self.folds.items():
                self.folded_values[fold_name][block_index:] = list(
                    map(fold_func, self.blocks[block_index:])
                )

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
                for fold_name, fold_func in self.folds.items():
                    fold_value = fold_func(
                        [self.folded_values[fold_name][-1], *__iterable[:index]]
                    )
                    self.folded_values[fold_name][-1] = fold_value
                self.blocks[-1] += __iterable[:index]
                __iterable = __iterable[index:]
            self.__extend_blocks(__iterable)

    def __extend_blocks(self, iterable):
        new_blocks = [
            iterable[i : i + self.block_size]
            for i in range(0, len(iterable), self.block_size)
        ]
        self.blocks.extend(new_blocks)
        for fold_name, fold_func in self.folds.items():
            fold_values = list(map(fold_func, new_blocks))
            self.folded_values[fold_name].extend(fold_values)

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
                for fold_name, fold_func in self.folds.items():
                    del self.folded_values[fold_name][block_index]
            else:
                self.blocks[block_index:] = self.compute_blocks(
                    block_index * block_size
                )
                for fold_name, fold_func in self.folds.items():
                    fold_value = list(map(fold_func, self.blocks[block_index:]))
                    self.folded_values[fold_name][block_index:] = fold_value
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
            for fold_name, fold_func in self.folds.items():
                self.folded_values[fold_name][block_index] = fold_func(
                    self.blocks[block_index]
                )

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
                return {
                    fold_name: self.folded_values[fold_name][left_block]
                    for fold_name in self.folds.keys()
                }
            return {
                fold_name: fold_func(self[left : right + 1])
                for fold_name, fold_func in self.folds.items()
            }
        if left != left_block_start_index:
            initial_value = {
                fold_name: fold_func(self[left : left_block_end_index + 1])
                for fold_name, fold_func in self.folds.items()
            }
        else:
            initial_value = {
                fold_name: self.folded_values[fold_name][left_block]
                for fold_name in self.folds.keys()
            }
        if right != right_block_end_index:
            final_value = {
                fold_name: fold_func(self[right_block_start_index : right + 1])
                for fold_name, fold_func in self.folds.items()
            }
        else:
            final_value = {
                fold_name: self.folded_values[fold_name][right_block]
                for fold_name in self.folds.keys()
            }
        return {
            fold_name: fold_func(
                self.folded_values[fold_name][left_block + 1 : right_block]
                + [initial_value[fold_name], final_value[fold_name]]
            )
            for fold_name, fold_func in self.folds.items()
        }

    def clear(self):
        super().clear()
        self.blocks = []
        self.folded_values = []
