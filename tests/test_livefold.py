import copy
import pickle

import pytest
from livefold import LiveFold, InvalidRangeException
from livefold.livefold import InvalidFoldException


def test_basic():
    lf = LiveFold([1, 2, 3, 4], folds={"max": max})
    assert lf.block_size == 2
    assert lf.blocks == [[1, 2], [3, 4]]


def test_append():
    lf = LiveFold([1, 2, 3, 4], folds={"max": max})
    lf.append(5)
    assert lf.block_size == 2
    assert lf.blocks == [[1, 2], [3, 4], [5]]


def test_extend():
    lf = LiveFold([1, 2, 3, 4, 5], folds={"sum": sum})
    lf.extend([6, 7, 8, 9])
    assert lf.block_size == 3
    assert lf.folded_values == {"sum": [6, 15, 24]}


def test_insert_no_change_to_block_size():
    lf = LiveFold([1, 2, 3, 5, 6, 7], folds={"sum": sum})
    assert lf.folded_values == {"sum": [3, 8, 13]}
    lf.insert(3, 4)
    assert lf.block_size == 2
    assert lf.blocks == [[1, 2], [3, 4], [5, 6], [7]]
    assert lf.folded_values == {"sum": [3, 7, 11, 7]}


def test_insert_block_size_changes():
    lf = LiveFold([1, 2, 3, 5, 6, 7, 8, 9], folds={"sum": sum})
    orig_blocks = lf.blocks
    lf.insert(3, 4)
    assert lf.block_size == 3
    assert orig_blocks != lf.blocks
    assert lf.blocks == [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    assert lf.folded_values == {"sum": [6, 15, 24]}


def test_reverse():
    lf = LiveFold([1, 2, 3, 4, 5, 6], folds={"sum": sum})
    assert lf.folded_values == {"sum": [3, 7, 11]}
    lf.reverse()
    assert lf.blocks == [[6, 5], [4, 3], [2, 1]]
    assert lf.folded_values == {"sum": [11, 7, 3]}


def test_concat_finish_last_block():
    lf = LiveFold([1, 2, 3, 4, 5], folds={"sum": sum})
    assert lf.folded_values == {"sum": [3, 7, 5]}
    lf += [6]
    assert lf.folded_values == {"sum": [3, 7, 11]}


def test_concat_add_new_blocks():
    lf = LiveFold([1, 2, 3, 4], folds={"sum": sum})
    assert lf.folded_values == {"sum": [3, 7]}
    lf += [5, 6, 7, 8]
    assert lf.folded_values == {"sum": [3, 7, 11, 15]}


def test_blocks_and_agg_concat_finish_last_block_and_add_new_blocks():
    lf = LiveFold(list(range(10)), folds={"sum": sum})
    lf += [10, 11, 12, 13, 14]
    assert lf.folded_values == {"sum": [3, 12, 21, 30, 39]}


def test_pop_last_value():
    lf = LiveFold([1, 2, 3, 4, 5], folds={"sum": sum})
    assert lf.folded_values == {"sum": [3, 7, 5]}
    val = lf.pop()
    assert val == 5
    assert lf.folded_values == {"sum": [3, 7]}


def test_pop_value():
    lf = LiveFold([1, 2, 3, 4, 5], folds={"sum": sum})
    assert lf.folded_values == {"sum": [3, 7, 5]}
    val = lf.pop(2)
    assert val == 3
    assert lf.blocks == [[1, 2], [4, 5]]
    assert lf.folded_values == {"sum": [3, 9]}


def test_pop_change_block_size():
    lf = LiveFold([1, 2, 3, 4, 5, 6, 7, 8, 9], folds={"sum": sum})
    assert lf.folded_values == {"sum": [6, 15, 24]}
    val = lf.pop(2)
    assert val == 3
    assert lf.blocks == [[1, 2], [4, 5], [6, 7], [8, 9]]
    assert lf.folded_values == {"sum": [3, 9, 13, 17]}


def test_remove():
    lf = LiveFold([1, 2, 3, 4, 5], folds={"sum": sum})
    assert lf.folded_values == {"sum": [3, 7, 5]}
    lf.remove(3)
    assert lf.blocks == [[1, 2], [4, 5]]
    assert lf.folded_values == {"sum": [3, 9]}


def test_remove_element_not_present():
    lf = LiveFold([1, 2, 3, 4, 5], folds={"sum": sum})
    with pytest.raises(ValueError):
        lf.remove(6)


def test_compute_aggregate_whole_blocks():
    lf = LiveFold([1, 2, 3, 4, 5, 6], folds={"sum": sum})
    assert lf.query(0, 5) == {"sum": 21}


def test_compute_aggregate_partial_blocks_left():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    assert lf.query(1, 5) == {"sum": 15}


def test_compute_aggregate_partial_blocks_right():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    assert lf.query(3, 7) == {"sum": 25}


def test_compute_aggregate_partial_blocks_both_sides():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    assert lf.query(1, 6) == {"sum": 21}


@pytest.mark.parametrize("left,right", [(0, 0), (1, 0), (0, 10), (-1, 5)])
def test_compute_blocks_invalid_range(left, right):
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    with pytest.raises(InvalidRangeException):
        lf.query(left, right)


def test_empty_folds():
    with pytest.raises(InvalidFoldException):
        LiveFold([0, 1, 2, 3, 4, 5], folds={})


def test_sort():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    assert lf.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert lf.folded_values == {"sum": [3, 12, 21]}
    lf.sort(reverse=True)
    assert lf.blocks == [[8, 7, 6], [5, 4, 3], [2, 1, 0]]
    assert lf.folded_values == {"sum": [21, 12, 3]}


def test_set_item():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    assert lf.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert lf.folded_values == {"sum": [3, 12, 21]}
    lf[3] = -1
    assert lf.blocks == [[0, 1, 2], [-1, 4, 5], [6, 7, 8]]
    assert lf.folded_values == {"sum": [3, 8, 21]}


def test_set_range_same_block():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    assert lf.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert lf.folded_values == {"sum": [3, 12, 21]}
    lf[3:6] = [-1, -2, -3]
    assert lf.blocks == [[0, 1, 2], [-1, -2, -3], [6, 7, 8]]
    assert lf.folded_values == {"sum": [3, -6, 21]}


def test_set_range_across_blocks():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    assert lf.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert lf.folded_values == {"sum": [3, 12, 21]}
    lf[2:7] = [-1, -2, -3, -4, -5]
    assert lf.blocks == [[0, 1, -1], [-2, -3, -4], [-5, 7, 8]]
    assert lf.folded_values == {"sum": [0, -9, 10]}


def test_set_range_extra_values():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    assert lf.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert lf.folded_values == {"sum": [3, 12, 21]}
    lf[3:6] = [-1, -2, -3, -4]
    assert lf.blocks == [[0, 1, 2], [-1, -2, -3], [-4, 6, 7], [8]]
    assert lf.folded_values == {"sum": [3, -6, 9, 8]}


def test_set_range_fewer_values():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    assert lf.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert lf.folded_values == {"sum": [3, 12, 21]}
    lf[3:6] = [-1]
    assert lf.blocks == [[0, 1], [2, -1], [6, 7], [8]]
    assert lf.folded_values == {"sum": [1, 1, 13, 8]}


def test_clear():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    lf.clear()
    assert lf.blocks == []
    assert lf.folded_values == {"sum": []}


def test_empty_list():
    lf = LiveFold([], folds={"sum": sum})
    assert lf.blocks == []
    assert lf.folded_values == {"sum": []}


def test_iter_yields_elements():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    assert list(iter(lf)) == [0, 1, 2, 3, 4, 5, 6, 7, 8]
    assert list(lf) == [0, 1, 2, 3, 4, 5, 6, 7, 8]
    assert 4 in lf


def test_query_same_block_partial():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    assert lf.query(1, 2) == {"sum": 3}
    assert lf.query(0, 1) == {"sum": 1}
    assert lf.query(3, 5) == {"sum": 12}
    assert lf.query(4, 5) == {"sum": 9}


def test_delitem():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    del lf[3]
    assert list(lf) == [0, 1, 2, 4, 5, 6, 7, 8]
    assert lf.blocks == [[0, 1], [2, 4], [5, 6], [7, 8]]
    assert lf.folded_values == {"sum": [1, 6, 11, 15]}


def test_delitem_slice():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    del lf[2:5]
    assert list(lf) == [0, 1, 5, 6, 7, 8]
    assert lf.blocks == [[0, 1], [5, 6], [7, 8]]
    assert lf.folded_values == {"sum": [1, 11, 15]}


def test_copy():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    clone = lf.copy()
    assert isinstance(clone, LiveFold)
    assert list(clone) == list(lf)
    assert clone.blocks == lf.blocks
    assert clone.folded_values == lf.folded_values
    clone.append(9)
    assert list(lf) == [0, 1, 2, 3, 4, 5, 6, 7, 8]


def test_copy_module():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    shallow = copy.copy(lf)
    assert isinstance(shallow, LiveFold)
    assert list(shallow) == list(lf)
    deep = copy.deepcopy(lf)
    assert isinstance(deep, LiveFold)
    assert list(deep) == list(lf)
    assert deep.folded_values == lf.folded_values


def test_pickle_roundtrip():
    lf = LiveFold([0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum})
    restored = pickle.loads(pickle.dumps(lf))
    assert isinstance(restored, LiveFold)
    assert list(restored) == list(lf)
    assert restored.blocks == lf.blocks
    assert restored.folded_values == lf.folded_values
    restored.append(9)
    assert restored.folded_values["sum"][-1] == 9


def test_multiple_folds_simple():
    lf = LiveFold(
        [0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum, "max": max, "min": min}
    )
    assert lf.block_size == 3
    assert lf.blocks == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert lf.folded_values == {"sum": [3, 12, 21], "max": [2, 5, 8], "min": [0, 3, 6]}


def test_multiple_folds_query():
    lf = LiveFold(
        [0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum, "max": max, "min": min}
    )
    assert lf.query(1, 5) == {"sum": 15, "max": 5, "min": 1}
    assert lf.query(2, 5) == {"sum": 14, "max": 5, "min": 2}
    assert lf.query(0, 8) == {"sum": 36, "max": 8, "min": 0}


def test_multiple_folds_insert():
    lf = LiveFold([1, 2, 3, 5, 6, 7], folds={"sum": sum, "max": max, "min": min})
    assert lf.folded_values == {"sum": [3, 8, 13], "max": [2, 5, 7], "min": [1, 3, 6]}
    lf.insert(3, 4)
    assert lf.blocks == [[1, 2], [3, 4], [5, 6], [7]]
    assert lf.folded_values == {
        "sum": [3, 7, 11, 7],
        "max": [2, 4, 6, 7],
        "min": [1, 3, 5, 7],
    }


def test_multiple_folds_pop():
    lf = LiveFold([1, 2, 3, 4, 5], folds={"sum": sum, "max": max, "min": min})
    assert lf.folded_values == {"sum": [3, 7, 5], "max": [2, 4, 5], "min": [1, 3, 5]}
    val = lf.pop(2)
    assert val == 3
    assert lf.blocks == [[1, 2], [4, 5]]
    assert lf.folded_values == {"sum": [3, 9], "max": [2, 5], "min": [1, 4]}


def test_multiple_folds_extend_with_merge():
    lf = LiveFold([1, 2, 3, 4, 5], folds={"sum": sum, "max": max, "min": min})
    assert lf.blocks == [[1, 2], [3, 4], [5]]
    assert lf.folded_values == {"sum": [3, 7, 5], "max": [2, 4, 5], "min": [1, 3, 5]}
    lf.extend([6, 7, 8])
    assert lf.blocks == [[1, 2], [3, 4], [5, 6], [7, 8]]
    assert lf.folded_values == {
        "sum": [3, 7, 11, 15],
        "max": [2, 4, 6, 8],
        "min": [1, 3, 5, 7],
    }


def test_multiple_folds_set_item():
    lf = LiveFold(
        [0, 1, 2, 3, 4, 5, 6, 7, 8], folds={"sum": sum, "max": max, "min": min}
    )
    assert lf.folded_values == {"sum": [3, 12, 21], "max": [2, 5, 8], "min": [0, 3, 6]}
    lf[3] = -1
    assert lf.blocks == [[0, 1, 2], [-1, 4, 5], [6, 7, 8]]
    assert lf.folded_values == {
        "sum": [3, 8, 21],
        "max": [2, 5, 8],
        "min": [0, -1, 6],
    }


def test_non_commutative_fold_simple():
    chars = list("abcdefghi")
    lf = LiveFold(chars, folds={"concat": "".join})
    assert lf.blocks == [
        ["a", "b", "c"],
        ["d", "e", "f"],
        ["g", "h", "i"],
    ]
    assert lf.folded_values == {"concat": ["abc", "def", "ghi"]}


def test_non_commutative_fold_full_range():
    chars = list("abcdefghi")
    lf = LiveFold(chars, folds={"concat": "".join})
    assert lf.query(0, 8) == {"concat": "abcdefghi"}


def test_non_commutative_fold_partial_left():
    chars = list("abcdefghi")
    lf = LiveFold(chars, folds={"concat": "".join})
    assert lf.query(1, 8) == {"concat": "bcdefghi"}


def test_non_commutative_fold_partial_right():
    chars = list("abcdefghi")
    lf = LiveFold(chars, folds={"concat": "".join})
    assert lf.query(0, 7) == {"concat": "abcdefgh"}


def test_non_commutative_fold_partial_both_sides():
    chars = list("abcdefghi")
    lf = LiveFold(chars, folds={"concat": "".join})
    assert lf.query(1, 7) == {"concat": "bcdefgh"}
    assert lf.query(2, 6) == {"concat": "cdefg"}


def test_non_commutative_fold_within_single_block():
    chars = list("abcdefghi")
    lf = LiveFold(chars, folds={"concat": "".join})
    assert lf.query(0, 2) == {"concat": "abc"}
    assert lf.query(3, 5) == {"concat": "def"}
    assert lf.query(4, 5) == {"concat": "ef"}


def test_non_commutative_fold_after_mutation():
    chars = list("abcdefghi")
    lf = LiveFold(chars, folds={"concat": "".join})
    lf.append("j")
    assert lf.query(0, 9) == {"concat": "abcdefghij"}
    lf[0] = "Z"
    assert lf.query(0, 9) == {"concat": "Zbcdefghij"}
