from __future__ import annotations

import random
from typing import Callable, Iterator, Optional


class TreapNode:
    """A node in a treap.

    Carries the key/value, a random priority, and left/right subtrees. We
    expose this class publicly because callers (and split/merge helpers)
    sometimes need to inspect or reuse roots; it is not an implementation
    detail.
    """

    __slots__ = ("key", "value", "priority", "left", "right", "size")

    def __init__(self, key, value, priority: float) -> None:
        self.key = key
        self.value = value
        self.priority = priority
        self.left: Optional[TreapNode] = None
        self.right: Optional[TreapNode] = None
        self.size: int = 1

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"TreapNode(key={self.key!r}, priority={self.priority:.4f})"


def _update_size(node: Optional[TreapNode]) -> None:
    if node is None:
        return
    s = 1
    if node.left is not None:
        s += node.left.size
    if node.right is not None:
        s += node.right.size
    node.size = s


def _split(node: Optional[TreapNode], key) -> tuple[Optional[TreapNode], Optional[TreapNode]]:
    """Split a treap rooted at ``node`` into ``(left, right)``.

    ``left`` receives all keys < ``key``; ``right`` receives all keys >= ``key``.
    The comparison is strict-less-than on the left side so that a split key
    that is present in the tree lands in ``right``. This convention keeps
    "insert then split by the inserted key" composable with ``merge``.
    """
    if node is None:
        return None, None
    if key <= node.key:
        # node and its right subtree belong to right.
        left, right = _split(node.left, key)
        node.left = right
        _update_size(node)
        return left, node
    else:
        # node and its left subtree belong to left.
        left, right = _split(node.right, key)
        node.right = left
        _update_size(node)
        return node, right


def _merge(left: Optional[TreapNode], right: Optional[TreapNode]) -> Optional[TreapNode]:
    """Merge two treaps.

    Requires every key in ``left`` to be < every key in ``right``. The caller
    is responsible for this; we do not scan to verify because doing so would
    cost O(n) and defeat the purpose of the structure.
    """
    if left is None:
        return right
    if right is None:
        return left
    if left.priority > right.priority:
        left.right = _merge(left.right, right)
        _update_size(left)
        return left
    else:
        right.left = _merge(left, right.left)
        _update_size(right)
        return right


class TreapMap:
    """An ordered map backed by a randomized binary search tree.

    Keys must be mutually comparable. Values may be any object. Expected time
    for ``insert``, ``get``, ``delete``, ``split``, ``merge``, and order
    statistics (``kth``) is O(log n); worst case is O(n), same as any BST.

    The tree is keyed by the caller's comparison semantics. A split by key
    ``k`` places every key strictly less than ``k`` in the left result and
    every key greater than or equal to ``k`` in the right result. If you need
    a different convention (e.g. left-inclusive), split by the key you want
    as the boundary and account for it at the call site.
    """

    __slots__ = ("_root", "_rand")

    def __init__(self, rng: Optional[Callable[[], float]] = None) -> None:
        """Create an empty treap.

        ``rng`` produces the float priorities drawn for each node. The default
        is ``random.random``; tests pass a deterministic function so the tree
        shape is reproducible.
        """
        self._root: Optional[TreapNode] = None
        self._rand: Callable[[], float] = rng if rng is not None else random.random

    # ------------------------------------------------------------------
    # Basic map operations
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return 0 if self._root is None else self._root.size

    def __contains__(self, key) -> bool:
        node = self._root
        while node is not None:
            if key < node.key:
                node = node.left
            elif node.key < key:
                node = node.right
            else:
                return True
        return False

    def __getitem__(self, key):
        node = self._root
        while node is not None:
            if key < node.key:
                node = node.left
            elif node.key < key:
                node = node.right
            else:
                return node.value
        raise KeyError(key)

    def __setitem__(self, key, value) -> None:
        self.insert(key, value)

    def __delitem__(self, key) -> None:
        self.delete(key)

    def insert(self, key, value) -> None:
        """Insert or update ``key`` with ``value``.

        Existing keys are overwritten in place; their priority is not changed,
        which keeps update amortized O(log n) instead of O(log n) with a
        resample that could churn structure unnecessarily.
        """
        # Fast path: if the key exists, just replace the value. This avoids a
        # split/merge pair and the priority churn mentioned above.
        node = self._root
        while node is not None:
            if key < node.key:
                node = node.left
            elif node.key < key:
                node = node.right
            else:
                node.value = value
                return
        self._root = self._insert_new(self._root, key, value)

    def _insert_new(self, node: Optional[TreapNode], key, value) -> TreapNode:
        if node is None:
            return TreapNode(key, value, self._rand())
        if key < node.key:
            node.left = self._insert_new(node.left, key, value)
            if node.left.priority > node.priority:
                node = self._rotate_right(node)
        else:
            node.right = self._insert_new(node.right, key, value)
            if node.right.priority > node.priority:
                node = self._rotate_left(node)
        _update_size(node)
        return node

    @staticmethod
    def _rotate_right(node: TreapNode) -> TreapNode:
        left = node.left
        assert left is not None
        node.left = left.right
        left.right = node
        _update_size(node)
        _update_size(left)
        return left

    @staticmethod
    def _rotate_left(node: TreapNode) -> TreapNode:
        right = node.right
        assert right is not None
        node.right = right.left
        right.left = node
        _update_size(node)
        _update_size(right)
        return right

    def delete(self, key) -> None:
        """Remove ``key``. Raises ``KeyError`` if absent."""
        found, self._root = self._delete(self._root, key)
        if not found:
            raise KeyError(key)

    def _delete(self, node: Optional[TreapNode], key) -> tuple[bool, Optional[TreapNode]]:
        if node is None:
            return False, None
        if key < node.key:
            found, node.left = self._delete(node.left, key)
            _update_size(node)
            return found, node
        if node.key < key:
            found, node.right = self._delete(node.right, key)
            _update_size(node)
            return found, node
        # Match. Pull the larger-priority child up so the heap property is
        # preserved, then recurse down until the node is a leaf and drops off.
        left = node.left
        right = node.right
        if left is None and right is None:
            return True, None
        if left is None:
            assert right is not None
            new_root = self._rotate_left(node)
            _, new_root.left = self._delete(new_root.left, key)
            _update_size(new_root)
            return True, new_root
        if right is None:
            new_root = self._rotate_right(node)
            _, new_root.right = self._delete(new_root.right, key)
            _update_size(new_root)
            return True, new_root
        if left.priority > right.priority:
            new_root = self._rotate_right(node)
            _, new_root.right = self._delete(new_root.right, key)
            _update_size(new_root)
            return True, new_root
        new_root = self._rotate_left(node)
        _, new_root.left = self._delete(new_root.left, key)
        _update_size(new_root)
        return True, new_root

    # ------------------------------------------------------------------
    # Ordered operations
    # ------------------------------------------------------------------

    def kth(self, k: int):
        """Return the ``(key, value)`` pair at 0-based rank ``k``.

        Raises ``IndexError`` if ``k`` is out of range. Order is ascending by
        key. This is the ``size`` field's payoff: O(log n) without a scan.
        """
        if k < 0 or k >= len(self):
            raise IndexError(k)
        node = self._root
        assert node is not None
        while node is not None:
            left_size = node.left.size if node.left is not None else 0
            if k < left_size:
                node = node.left
            elif k == left_size:
                return node.key, node.value
            else:
                k -= left_size + 1
                node = node.right
        raise IndexError(k)  # unreachable if size bookkeeping is correct

    def __iter__(self) -> Iterator:
        return self.keys()

    def keys(self) -> Iterator:
        for k, _ in self.items():
            yield k

    def values(self) -> Iterator:
        for _, v in self.items():
            yield v

    def items(self) -> Iterator[tuple, object]:
        # Morris-style in-order traversal. Allocates no recursion stack, so
        # a degenerate linear chain cannot overflow the interpreter.
        node = self._root
        while node is not None:
            if node.left is None:
                yield node.key, node.value
                node = node.right
            else:
                pred = node.left
                while pred.right is not None and pred.right is not node:
                    pred = pred.right
                if pred.right is None:
                    pred.right = node
                    node = node.left
                else:
                    pred.right = None
                    yield node.key, node.value
                    node = node.right

    # ------------------------------------------------------------------
    # Split and merge
    # ------------------------------------------------------------------

    def split(self, key) -> tuple["TreapMap", "TreapMap"]:
        """Split into two treaps at ``key``.

        Returns ``(left, right)`` where ``left`` holds all keys < ``key`` and
        ``right`` holds all keys >= ``key``. ``self`` is left empty after the
        call; the two returned maps share no nodes with each other or with
        the caller's prior reference.
        """
        left_root, right_root = _split(self._root, key)
        self._root = None
        left = TreapMap(self._rand)
        left._root = left_root
        right = TreapMap(self._rand)
        right._root = right_root
        return left, right

    @classmethod
    def merge(cls, left: "TreapMap", right: "TreapMap") -> "TreapMap":
        """Merge two treaps into a new one.

        Requires every key in ``left`` to be < every key in ``right``. Both
        inputs are emptied by the call; the result shares their nodes. We use
        ``left``'s rng for the result so priorities remain internally
        consistent in distribution.
        """
        result = cls(left._rand)
        result._root = _merge(left._root, right._root)
        left._root = None
        right._root = None
        return result

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def min(self):
        """Return the smallest ``(key, value)``. Raises ``KeyError`` if empty."""
        if self._root is None:
            raise KeyError("empty treap")
        node = self._root
        while node.left is not None:
            node = node.left
        return node.key, node.value

    def max(self):
        """Return the largest ``(key, value)``. Raises ``KeyError`` if empty."""
        if self._root is None:
            raise KeyError("empty treap")
        node = self._root
        while node.right is not None:
            node = node.right
        return node.key, node.value

    def __repr__(self) -> str:
        pairs = ", ".join(f"{k!r}: {v!r}" for k, v in self.items())
        return f"TreapMap({{{pairs}}})"
