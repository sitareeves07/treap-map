# treap_map

A small, dependency-free Python ordered map built on a treap: a binary search
 tree keyed by your values and heap-ordered by random priorities. Expected
 O(log n) for insert, lookup, delete, split, merge, and order statistics.

```python
from treap_map import TreapMap

t = TreapMap()
t[3] = "c"
t[1] = "a"
t[2] = "b"

print(list(t))            # [1, 2, 3]
print(t.kth(0))           # (1, 'a')

left, right = t.split(2)  # left: {1}, right: {2, 3}
merged = TreapMap.merge(left, right)
```

## Why this exists

When you need an ordered map that also supports `split`/`merge` and rank
queries, balanced BSTs are the natural fit. Python's stdlib offers `dict`
(unordered, no rank) and `bisect` over a sorted list (O(n) insert/delete). A
treap gives you all of ordered iteration, kth-by-rank, and destructive
split/merge in expected logarithmic time, with about 200 lines of code and
no C extension.

The trade-off: priorities are random, so individual operations are
*expected* O(log n), not guaranteed. In practice with a decent RNG the tree
stays balanced; for adversarial inputs you would want a deterministic
self-balancing tree (AVL/red-black) instead.

## Edge cases worth knowing

- **`split(k)` is strict on the left.** Left gets keys `< k`, right gets keys
  `>= k`. If `k` is itself a key in the map, it lands in the right result.
  This convention keeps `split` composable with `merge`, which requires every
  key in its left input to be strictly less than every key in its right input.
- **`merge` does not verify the ordering precondition.** Checking would cost
  O(n) and defeat the purpose. If you merge two maps whose key ranges overlap,
  the resulting tree will be a malformed BST and lookups will return wrong
  values silently.
- **Updating an existing key keeps its priority.** This avoids churn and keeps
  updates O(log n); it means a key's structural position can differ depending
  on whether it was inserted fresh or updated.

## Exported names

`treap_map.TreapMap` — the map class. Constructor accepts an optional `rng`
callable returning a float in `[0, 1)`; defaults to `random.random`.

`treap_map.TreapMap` methods: `insert`, `delete`, `get` via `__getitem__`,
`__setitem__`, `__delitem__`, `__contains__`, `__len__`, `__iter__`,
`keys`, `values`, `items`, `kth`, `min`, `max`, `split`, classmethod `merge`.

`treap_map.TreapNode` — the node type, exposed for callers that need to
inspect roots returned by split/merge or build their own traversal logic.
Fields: `key`, `value`, `priority`, `left`, `right`, `size`.

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```
