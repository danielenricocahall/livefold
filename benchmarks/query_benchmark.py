import random
import timeit

from livefold.livefold import PySquagg

aggregator_function = sum
n = 100_000
data = list(range(n))
num_ops = 10_000

# Shared: Generate consistent queries/updates
queries = [
    (min(a, b), max(a, b))
    for a, b in (
        (random.randint(0, n - 1), random.randint(0, n - 1)) for _ in range(num_ops)
    )
]
inserts = [(random.randint(0, n - 1), random.randint(1, 10**6)) for _ in range(num_ops)]
pops = [random.randint(0, n - 1) for _ in range(num_ops)]
appends = [random.randint(1, 10**6) for _ in range(num_ops)]


# === Range Query ===
def benchmark_pysquagg_query():
    ps = PySquagg(data, aggregator_function)
    total = 0
    for left, right in queries:
        total += ps.query(left, right)
    return total


def benchmark_naive_query():
    total = 0
    for left, right in queries:
        total += sum(data[left : right + 1])
    return total


# === Insert ===
def benchmark_pysquagg_insert():
    ps = PySquagg(data.copy(), aggregator_function)
    for index, value in inserts:
        ps.insert(index, value)
    return ps


def benchmark_naive_insert():
    arr = data.copy()
    for index, value in inserts:
        arr.insert(index, value)
    return arr


# === Pop ===
def benchmark_pysquagg_pop():
    ps = PySquagg(data.copy(), aggregator_function)
    for index in pops:
        ps.pop(index % len(ps))
    return ps


def benchmark_naive_pop():
    arr = data.copy()
    for index in pops:
        arr.pop(index % len(arr))
    return arr


# === Append ===
def benchmark_pysquagg_append():
    ps = PySquagg(data.copy(), aggregator_function)
    for value in appends:
        ps.append(value)
    return ps


def benchmark_naive_append():
    arr = data.copy()
    for value in appends:
        arr.append(value)
    return arr


# === Run All Benchmarks ===
def run_benchmark(label, pysquagg_fn, naive_fn):
    py_time = timeit.timeit(pysquagg_fn, number=10)
    naive_time = timeit.timeit(naive_fn, number=10)
    print(f"[{label}]")
    print(f"  PySquagg:     {py_time:.6f} seconds")
    print(f"  Naive List:   {naive_time:.6f} seconds\n")


if __name__ == "__main__":
    print("=== Benchmarking PySquagg vs. Naive List Approaches ===\n")
    run_benchmark("Range Query", benchmark_pysquagg_query, benchmark_naive_query)
    run_benchmark("Insert", benchmark_pysquagg_insert, benchmark_naive_insert)
    run_benchmark("Pop", benchmark_pysquagg_pop, benchmark_naive_pop)
    run_benchmark("Append", benchmark_pysquagg_append, benchmark_naive_append)
