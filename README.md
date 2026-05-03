# Overview

[![Build Status](https://github.com/danielenricocahall/livefold/actions/workflows/ci.yaml/badge.svg)](https://github.com/danielenricocahall/pysquagg/actions/workflows/ci.yaml/badge.svg)
[![Supported Versions](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
[![license](https://img.shields.io/github/license/mashape/apistatus.svg?maxAge=2592000)](https://github.com/danielenricocahall/pysquagg/blob/main/LICENSE)

 This is `pysquagg`, a library containing a data structure intended for expediant computation of aggregations on a collection using Square Root Decomposition. The data structure is an extension of [Mo's Algorithm](https://www.geeksforgeeks.org/mos-algorithm-query-square-root-decomposition-set-1-introduction/). Please see more details in the associated [blog post](https://open.substack.com/pub/dannycahall/p/pysquagg-square-root-decomposition?r=1swlpp&utm_campaign=post&utm_medium=web&showWelcomeOnShare=true).
 
# Motivation
The principles behind Mo's Algorithm is interesting and useful, but the implementation is a bit cumbersome. This library is intended to make it easier to use the algorithm in Python, plus introduce dynamic behavior, such that a collection can be modified after the data structure is created, and the corresponding blocks + aggregates are updated accordingly.

# Details
The list supplied is split into $\left\lfloor \frac{n}{\left\lfloor \sqrt{n} \right\rfloor} \right\rfloor$ blocks of size $\sqrt{n}$, and the aggregate (based on the supplied aggregation function) is computed for each block. When the`PySquagg` object is queried with a valid start and end index:
- Pre-computed aggregations for all blocks that are entirely within the range are collected
- Elements not fully contained within a block are iterated over and the aggregation function is applied to them
- The pre-computed aggregations and newly computed aggregations are combined and returned

The end result is a `query` method that is O($\sqrt{n}$), compared to O(n) for a naive implementation.

Additionally, the `PySquagg` object can be modified after creation (e.g; `append`, `extend`, `pop`), and the blocks are updated accordingly to always be of size $\sqrt{n}$. The aggregates are also computed on the updated blocks.


# API & Usage
The API for using `pysquagg` is simple, as we're only providing a single class `PySquagg`:

```python
from livefold.livefold import PySquagg

pysquagg_instance = PySquagg([1, 2, 3, 4, 5, 6], aggregator_function=sum)
pysquagg_instance.blocks  # will print [[1, 2], [3, 4], [5, 6]]
pysquagg_instance.aggregated_values  # will print [3, 7, 11]
pysquagg_instance.query(0, 5)  # will print 21
pysquagg_instance += [7, 8]
pysquagg_instance.blocks  # will print [[1, 2], [3, 4], [5, 6], [7, 8]]
pysquagg_instance.append(9)
pysquagg_instance.blocks  # will print [[1, 2, 3], [4, 5, 6], [7, 8, 9]] - the block size has been recomputed from 2 -> 3
pysquagg_instance.aggregated_values  # will print [6, 15, 24]
pysquagg_instance.query(0, 8)  # will print 45
pysquagg_instance.pop()
pysquagg_instance[2] = -1
pysquagg_instance.blocks  # will print [[1, 2], [-1, 4], [5, 6], [7, 8]] - block_size has dropped down from 3 -> 2
```

# Performance Characteristics

## Complexity

| Operation | Average Case Time Complexity | Worst Case Time Complexity |
|-----------|------------------------------|----------------|
| `query`   | O($\sqrt{n}$)                | O($\sqrt{n}$)  |
| `append`  | O(1)                         | O(n)           |
| `insert`  | O(n)                         | O(n)           |
| `pop`     | O(n)                         | O(n)           |
| `extend` | O(m)                         | O(n + m)       |

The main reason for other operations being linear in the worst case is the fact that when the collection is modified, the blocks and aggregates need to be recomputed when the square root of the size of the collection changes. Furthermore, as `PySquagg` is a subclass of list, some of these performance characteristics are inherent.
## Benchmarks

Some preliminary benchmarking can be conducted from scripts in the `benchmarks` directory. One highlight from comparing `query` to performing computations on the arbitrary slices (using `sum` as the aggregator function) is:

| Operation | PySquagg (s) |  Naive (s) |
|-----------|--------------|------------|
| `query`   | 0.032        | 1.48      |

As derived from a 2023 Macbook Pro M2, 16GB RAM.

# Constraints
The aggregator functions need to be associative and commutative, and the data structure is not thread-safe.


# TODO
- [ ] Identify if we can reduce the runtime of some operations to be sublinear
- [ ] Perform more extensive benchmarking
- [ ] Incorporate a mechanism for combining aggregator functions, if someone adds two `PySquagg` objects
- [ ] Add a `LoosePySquagg` class that does not strictly enforce the sqrt(n), which may have some performance benefits for certain operations such as `insert` and `pop` which currently require recomputation of blocks and aggregates

> 💡 Interested in contributing? Check out the [Local Development & Contributions Guide](https://github.com/danielenricocahall/pysquagg/blob/main/CONTRIBUTING.md).