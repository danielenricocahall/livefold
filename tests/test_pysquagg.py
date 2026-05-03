import copy
import pickle

import pytest
from livefold import LiveFold, InvalidRangeException


def test_basic():
    lf = LiveFold([1, 2, 3, 4], aggregator_function=lambda x: x)
    assert lf.block_size == 2
    assert lf.blocks == [[1, 2], [3, 4]]


def test_append():
    lf = LiveFold([1, 2, 3, 4], aggregator_function=lambda x: x)
    lf.append(5)
    assert lf.block_size == 2
    assert lf.blocks == [[1, 2], [3, 4], [5]]


def test_extend():
    lf = LiveFold([1, 2, 3, 4, 5], aggregator_function=sum)
    lf.extend([6, 7, 8, 9])
    assert lf.block_size == 3
    assert lf.aggregated_values == [6, 15, 24]


def test_insert_no_change_to_block_size():
    lf = LiveFold([1, 2, 3, 5, 6, 7], aggregator_function=sum)
    assert lf.aggregated_values == [3, 8, 13]
    lf.insert(3, 4)
    assert lf.block_size == 2
    assert lf.blocks == [[1, 2], [3, 4], [5, 6], [7]]
    assert lf.aggregated_values == [3, 7, 11, 7]


def test_insert_block_size_changes():
    lf = LiveFold([1, 2, 3, 5, 6, 7, 8, 9], aggregator_function=sum)
    orig_blocks = lf.blocks
    lf.insert(3, 4)
    assert lf.block_size == 3
    assert orig_blocks != LiveFold.blocks
    assert lf.blocks == [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    assert lf.aggregated_values == [6, 15, 24]


def test_reverse():
    lf = LiveFold([1, 2, 3, 4, 5, 6], aggregator_function=sum)
    assert lf.aggregated_values == [3, 7, 11]
    lf.reverse()
    assert lf.blocks == [[6, 5], [4, 3], [2, 1]]
    assert lf.aggregated_values == [11, 7, 3]


def test_concat_finish_last_block():
    lf = LiveFold([1, 2, 3, 4, 5], aggregator_function=sum)
    assert lf.aggregated_values == [3, 7, 5]
    lf += [6]
    assert lf.aggregated_values == [3, 7, 11]


def test_concat_add_new_blocks():
    lf = LiveFold([1, 2, 3, 4], aggregator_function=sum)
    assert lf.aggregated_values == [3, 7]
    lf += [5, 6, 7, 8]
    assert lf.aggregated_values == [3, 7, 11, 15]


def test_blocks_and_agg_concat_finish_last_block_and_add_new_blocks():
    lf = LiveFold(list(range(10)), aggregator_function=sum)
    lf += [10, 11, 12, 13, 14]
    assert lf.aggregated_values == [3, 12, 21, 30, 39]


def test_pop_last_value():
    lf = LiveFold([1, 2, 3, 4, 5], aggregator_function=sum)
    assert lf.aggregated_values == [3, 7, 5]
    val = lf.pop()
    assert val == 5
    assert lf.aggregated_values == [3, 7]


def test_pop_value():
    lf = LiveFold([1, 2, 3, 4, 5], aggregator_function=sum)
    assert lf.aggregated_values == [3, 7, 5]
    val = lf.pop(2)
    assert val == 3
    assert lf.blocks == [[1, 2], [4, 5]]
    assert lf.aggregated_values == [3, 9]


def test_pop_change_block_size():
    lf = LiveFold([1, 2, 3, 4, 5, 6, 7, 8, 9], aggregator_function=sum)
    assert lf.aggregated_values == [6, 15, 24]
    val = lf.pop(2)
    assert val == 3
    assert lf.blocks == [[1, 2], [4, 5], [6, 7], [8, 9]]
    assert lf.aggregated_values == [3, 9, 13, 17]


def test_remove():
    lf = LiveFold([1, 2, 3, 4, 5], aggregator_function=sum)
    assert lf.aggregated_values == [3, 7, 5]
    lf.remove(3)
    assert lf.blocks == [[1, 2], [4, 5]]
    assert lf.aggregated_values == [3, 9]


def test_remove_element_not_present():
    lf = LiveFold([1, 2, 3, 4, 5], aggregator_function=sum)
    with pytest.raises(ValueError):
        lf.remove(6)


def test_compute_aggregate_whole_blocks():
    lf = LiveFold([1, 2, 3, 4, 5, 6], aggregator_function=sum)
    assert lf.query(0, 5) == 21


def test_compute_aggregate_partial_blocks_left():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert lf.query(1, 5) == 15


def test_compute_aggregate_partial_blocks_right():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert lf.query(3, 7) == 25


def test_compute_aggregate_partial_blocks_both_sides():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert lf.query(1, 6) == 21


@pytest.mark.parametrize("left,right", [(0, 0), (1, 0), (0, 10), (-1, 5)])
def test_compute_blocks_invalid_range(left, right):
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    with pytest.raises(InvalidRangeException):
        lf.query(left, right)


def test_sort():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert lf.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert lf.aggregated_values == [3, 12, 21]
    lf.sort(reverse=True)
    assert lf.blocks == [[8, 7, 6], [5, 4, 3], [2, 1, 0]]
    assert lf.aggregated_values == [21, 12, 3]


def test_set_item():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert lf.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert lf.aggregated_values == [3, 12, 21]
    lf[3] = -1
    assert lf.blocks == [[0, 1, 2], [-1, 4, 5], [6, 7, 8]]
    assert lf.aggregated_values == [3, 8, 21]


def test_set_range_same_block():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert lf.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert lf.aggregated_values == [3, 12, 21]
    lf[3:6] = [-1, -2, -3]
    assert lf.blocks == [[0, 1, 2], [-1, -2, -3], [6, 7, 8]]
    assert lf.aggregated_values == [3, -6, 21]


def test_set_range_across_blocks():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert lf.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert lf.aggregated_values == [3, 12, 21]
    lf[2:7] = [-1, -2, -3, -4, -5]
    assert lf.blocks == [[0, 1, -1], [-2, -3, -4], [-5, 7, 8]]
    assert lf.aggregated_values == [0, -9, 10]


def test_set_range_extra_values():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert lf.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert lf.aggregated_values == [3, 12, 21]
    lf[3:6] = [-1, -2, -3, -4]
    assert lf.blocks == [[0, 1, 2], [-1, -2, -3], [-4, 6, 7], [8]]
    assert lf.aggregated_values == [3, -6, 9, 8]


def test_set_range_fewer_values():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert lf.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert lf.aggregated_values == [3, 12, 21]
    lf[3:6] = [-1]
    assert lf.blocks == [[0, 1], [2, -1], [6, 7], [8]]
    assert lf.aggregated_values == [1, 1, 13, 8]


def test_clear():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    lf.clear()
    assert lf.blocks == []
    assert lf.aggregated_values == []


def test_empty_list():
    lf = LiveFold([], aggregator_function=sum)
    assert lf.blocks == []
    assert lf.aggregated_values == []


def test_iter_yields_elements():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert list(iter(lf)) == [0, 1, 2, 3, 4, 5, 6, 7, 8]
    assert list(lf) == [0, 1, 2, 3, 4, 5, 6, 7, 8]
    assert 4 in lf


def test_iter_blocks():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert list(lf.iter_blocks()) == [
        ([0, 1, 2], 3),
        ([3, 4, 5], 12),
        ([6, 7, 8], 21),
    ]


def test_query_same_block_partial():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    assert lf.query(1, 2) == 3
    assert lf.query(0, 1) == 1
    assert lf.query(3, 5) == 12
    assert lf.query(4, 5) == 9


def test_delitem():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    del lf[3]
    assert list(lf) == [0, 1, 2, 4, 5, 6, 7, 8]
    assert lf.blocks == [[0, 1], [2, 4], [5, 6], [7, 8]]
    assert lf.aggregated_values == [1, 6, 11, 15]


def test_delitem_slice():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    del lf[2:5]
    assert list(lf) == [0, 1, 5, 6, 7, 8]
    assert lf.blocks == [[0, 1], [5, 6], [7, 8]]
    assert lf.aggregated_values == [1, 11, 15]


def test_copy():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    clone = lf.copy()
    assert isinstance(clone, LiveFold)
    assert list(clone) == list(lf)
    assert clone.blocks == lf.blocks
    assert clone.aggregated_values == lf.aggregated_values
    clone.append(9)
    assert list(lf) == [0, 1, 2, 3, 4, 5, 6, 7, 8]


def test_copy_module():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    shallow = copy.copy(lf)
    assert isinstance(shallow, LiveFold)
    assert list(shallow) == list(lf)
    deep = copy.deepcopy(lf)
    assert isinstance(deep, LiveFold)
    assert list(deep) == list(lf)
    assert deep.aggregated_values == lf.aggregated_values


def test_pickle_roundtrip():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], aggregator_function=sum)
    restored = pickle.loads(pickle.dumps(lf))
    assert isinstance(restored, LiveFold)
    assert list(restored) == list(lf)
    assert restored.blocks == lf.blocks
    assert restored.aggregated_values == lf.aggregated_values
    restored.append(9)
    assert restored.aggregated_values[-1] == 9
