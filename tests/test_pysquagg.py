import copy
import pickle

import pytest
from pysquagg import LiveFold, InvalidRangeException


def test_basic():
    live_fold = LiveFold([1, 2, 3, 4], aggregator_function=lambda x: x)
    assert live_fold.block_size == 2
    assert live_fold.blocks == [[1, 2], [3, 4]]


def test_append():
    live_fold = LiveFold([1, 2, 3, 4], aggregator_function=lambda x: x)
    live_fold.append(5)
    assert live_fold.block_size == 2
    assert live_fold.blocks == [[1, 2], [3, 4], [5]]


def test_extend():
    live_fold = LiveFold([1, 2, 3, 4, 5], aggregator_function=sum)
    live_fold.extend([6, 7, 8, 9])
    assert live_fold.block_size == 3
    assert live_fold.aggregated_values == [6, 15, 24]


def test_insert_no_change_to_block_size():
    live_fold = LiveFold([1, 2, 3, 5, 6, 7], aggregator_function=sum)
    assert live_fold.aggregated_values == [3, 8, 13]
    live_fold.insert(3, 4)
    assert live_fold.block_size == 2
    assert live_fold.blocks == [[1, 2], [3, 4], [5, 6], [7]]
    assert live_fold.aggregated_values == [3, 7, 11, 7]


def test_insert_block_size_changes():
    live_fold = LiveFold([1, 2, 3, 5, 6, 7, 8, 9], aggregator_function=sum)
    orig_blocks = live_fold.blocks
    live_fold.insert(3, 4)
    assert live_fold.block_size == 3
    assert orig_blocks != LiveFold.blocks
    assert live_fold.blocks == [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    assert live_fold.aggregated_values == [6, 15, 24]


def test_reverse():
    live_fold = LiveFold([1, 2, 3, 4, 5, 6], aggregator_function=sum)
    assert live_fold.aggregated_values == [3, 7, 11]
    live_fold.reverse()
    assert live_fold.blocks == [[6, 5], [4, 3], [2, 1]]
    assert live_fold.aggregated_values == [11, 7, 3]


def test_concat_finish_last_block():
    live_fold = LiveFold([1, 2, 3, 4, 5], aggregator_function=sum)
    assert live_fold.aggregated_values == [3, 7, 5]
    live_fold += [6]
    assert live_fold.aggregated_values == [3, 7, 11]


def test_concat_add_new_blocks():
    live_fold = LiveFold([1, 2, 3, 4], aggregator_function=sum)
    assert live_fold.aggregated_values == [3, 7]
    live_fold += [5, 6, 7, 8]
    assert live_fold.aggregated_values == [3, 7, 11, 15]


def test_blocks_and_agg_concat_finish_last_block_and_add_new_blocks():
    live_fold = LiveFold(list(range(10)), aggregator_function=sum)
    live_fold += [10, 11, 12, 13, 14]
    assert live_fold.aggregated_values == [3, 12, 21, 30, 39]


def test_pop_last_value():
    live_fold = LiveFold([1, 2, 3, 4, 5], aggregator_function=sum)
    assert live_fold.aggregated_values == [3, 7, 5]
    val = live_fold.pop()
    assert val == 5
    assert live_fold.aggregated_values == [3, 7]


def test_pop_value():
    live_fold = LiveFold([1, 2, 3, 4, 5], aggregator_function=sum)
    assert live_fold.aggregated_values == [3, 7, 5]
    val = live_fold.pop(2)
    assert val == 3
    assert live_fold.blocks == [[1, 2], [4, 5]]
    assert live_fold.aggregated_values == [3, 9]


def test_pop_change_block_size():
    live_fold = LiveFold([1, 2, 3, 4, 5, 6, 7, 8, 9], aggregator_function=sum)
    assert live_fold.aggregated_values == [6, 15, 24]
    val = live_fold.pop(2)
    assert val == 3
    assert live_fold.blocks == [[1, 2], [4, 5], [6, 7], [8, 9]]
    assert live_fold.aggregated_values == [3, 9, 13, 17]


def test_remove():
    live_fold = LiveFold([1, 2, 3, 4, 5], aggregator_function=sum)
    assert live_fold.aggregated_values == [3, 7, 5]
    live_fold.remove(3)
    assert live_fold.blocks == [[1, 2], [4, 5]]
    assert live_fold.aggregated_values == [3, 9]


def test_remove_element_not_present():
    live_fold = LiveFold([1, 2, 3, 4, 5], aggregator_function=sum)
    with pytest.raises(ValueError):
        live_fold.remove(6)


def test_compute_aggregate_whole_blocks():
    live_fold = LiveFold([1, 2, 3, 4, 5, 6], aggregator_function=sum)
    assert live_fold.query(0, 5) == 21


def test_compute_aggregate_partial_blocks_left():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert live_fold.query(1, 5) == 15


def test_compute_aggregate_partial_blocks_right():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert live_fold.query(3, 7) == 25


def test_compute_aggregate_partial_blocks_both_sides():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert live_fold.query(1, 6) == 21


@pytest.mark.parametrize("left,right", [(0, 0), (1, 0), (0, 10), (-1, 5)])
def test_compute_blocks_invalid_range(left, right):
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    with pytest.raises(InvalidRangeException):
        live_fold.query(left, right)


def test_sort():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert live_fold.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert live_fold.aggregated_values == [3, 12, 21]
    live_fold.sort(reverse=True)
    assert live_fold.blocks == [[8, 7, 6], [5, 4, 3], [2, 1, 0]]
    assert live_fold.aggregated_values == [21, 12, 3]


def test_set_item():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert live_fold.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert live_fold.aggregated_values == [3, 12, 21]
    live_fold[3] = -1
    assert live_fold.blocks == [[0, 1, 2], [-1, 4, 5], [6, 7, 8]]
    assert live_fold.aggregated_values == [3, 8, 21]


def test_set_range_same_block():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert live_fold.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert live_fold.aggregated_values == [3, 12, 21]
    live_fold[3:6] = [-1, -2, -3]
    assert live_fold.blocks == [[0, 1, 2], [-1, -2, -3], [6, 7, 8]]
    assert live_fold.aggregated_values == [3, -6, 21]


def test_set_range_across_blocks():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert live_fold.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert live_fold.aggregated_values == [3, 12, 21]
    live_fold[2:7] = [-1, -2, -3, -4, -5]
    assert live_fold.blocks == [[0, 1, -1], [-2, -3, -4], [-5, 7, 8]]
    assert live_fold.aggregated_values == [0, -9, 10]


def test_set_range_extra_values():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert live_fold.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert live_fold.aggregated_values == [3, 12, 21]
    live_fold[3:6] = [-1, -2, -3, -4]
    assert live_fold.blocks == [[0, 1, 2], [-1, -2, -3], [-4, 6, 7], [8]]
    assert live_fold.aggregated_values == [3, -6, 9, 8]


def test_set_range_fewer_values():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert live_fold.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert live_fold.aggregated_values == [3, 12, 21]
    live_fold[3:6] = [-1]
    assert live_fold.blocks == [[0, 1], [2, -1], [6, 7], [8]]
    assert live_fold.aggregated_values == [1, 1, 13, 8]


def test_clear():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    live_fold.clear()
    assert live_fold.blocks == []
    assert live_fold.aggregated_values == []


def test_empty_list():
    live_fold = LiveFold([], aggregator_function=sum)
    assert live_fold.blocks == []
    assert live_fold.aggregated_values == []


def test_iter_yields_elements():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert list(iter(live_fold)) == [0, 1, 2, 3, 4, 5, 6, 7, 8]
    assert list(live_fold) == [0, 1, 2, 3, 4, 5, 6, 7, 8]
    assert 4 in live_fold


def test_iter_blocks():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert list(live_fold.iter_blocks()) == [
        ([0, 1, 2], 3),
        ([3, 4, 5], 12),
        ([6, 7, 8], 21),
    ]


def test_query_same_block_partial():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert live_fold.query(1, 2) == 3
    assert live_fold.query(0, 1) == 1
    assert live_fold.query(3, 5) == 12
    assert live_fold.query(4, 5) == 9


def test_delitem():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    del live_fold[3]
    assert list(live_fold) == [0, 1, 2, 4, 5, 6, 7, 8]
    assert live_fold.blocks == [[0, 1], [2, 4], [5, 6], [7, 8]]
    assert live_fold.aggregated_values == [1, 6, 11, 15]


def test_delitem_slice():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    del live_fold[2:5]
    assert list(live_fold) == [0, 1, 5, 6, 7, 8]
    assert live_fold.blocks == [[0, 1], [5, 6], [7, 8]]
    assert live_fold.aggregated_values == [1, 11, 15]


def test_copy():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    clone = live_fold.copy()
    assert isinstance(clone, LiveFold)
    assert list(clone) == list(live_fold)
    assert clone.blocks == live_fold.blocks
    assert clone.aggregated_values == live_fold.aggregated_values
    clone.append(9)
    assert list(live_fold) == [0, 1, 2, 3, 4, 5, 6, 7, 8]


def test_copy_module():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    shallow = copy.copy(live_fold)
    assert isinstance(shallow, LiveFold)
    assert list(shallow) == list(live_fold)
    deep = copy.deepcopy(live_fold)
    assert isinstance(deep, LiveFold)
    assert list(deep) == list(live_fold)
    assert deep.aggregated_values == live_fold.aggregated_values


def test_pickle_roundtrip():
    live_fold = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    restored = pickle.loads(pickle.dumps(live_fold))
    assert isinstance(restored, LiveFold)
    assert list(restored) == list(live_fold)
    assert restored.blocks == live_fold.blocks
    assert restored.aggregated_values == live_fold.aggregated_values
    restored.append(9)
    assert restored.aggregated_values[-1] == 9
