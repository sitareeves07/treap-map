import unittest

from treap_map import TreapMap, TreapNode


def deterministic_priorities():
    """Yield a fixed sequence of priorities.

    We walk a small LCG so priorities are reproducible across runs and
    platforms. Values are floats in [0, 1).
    """
    state = 1

    def next_priority() -> float:
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF

    return next_priority


class TestBasicMap(unittest.TestCase):
    def test_empty_len_and_contains(self):
        t = TreapMap()
        self.assertEqual(len(t), 0)
        self.assertNotIn(1, t)

    def test_insert_and_get(self):
        t = TreapMap(deterministic_priorities())
        t.insert("a", 1)
        t.insert("b", 2)
        t["c"] = 3
        self.assertEqual(t["a"], 1)
        self.assertEqual(t["b"], 2)
        self.assertEqual(t["c"], 3)
        self.assertEqual(len(t), 3)

    def test_get_missing_raises_keyerror(self):
        t = TreapMap(deterministic_priorities())
        t["x"] = 1
        with self.assertRaises(KeyError):
            _ = t["y"]

    def test_update_existing_key_preserves_value(self):
        t = TreapMap(deterministic_priorities())
        t[1] = "old"
        t[1] = "new"
        self.assertEqual(t[1], "new")
        self.assertEqual(len(t), 1)

    def test_delete(self):
        t = TreapMap(deterministic_priorities())
        for i in range(20):
            t[i] = i * 10
        del t[10]
        self.assertNotIn(10, t)
        self.assertEqual(len(t), 19)
        # neighbours still present and correct
        self.assertEqual(t[9], 90)
        self.assertEqual(t[11], 110)

    def test_delete_missing_raises_keyerror(self):
        t = TreapMap(deterministic_priorities())
        t[1] = 1
        with self.assertRaises(KeyError):
            del t[2]

    def test_delete_root_when_tree_has_only_root(self):
        t = TreapMap(deterministic_priorities())
        t[5] = 5
        del t[5]
        self.assertEqual(len(t), 0)
        self.assertNotIn(5, t)

    def test_delete_all_in_random_order_leaves_empty(self):
        t = TreapMap(deterministic_priorities())
        keys = list(range(50))
        for k in keys:
            t[k] = k
        # delete in a shuffled but deterministic order
        order = sorted(keys, key=lambda k: (k * 7) % 50)
        for k in order:
            del t[k]
        self.assertEqual(len(t), 0)


class TestIteration(unittest.TestCase):
    def test_items_are_sorted(self):
        t = TreapMap(deterministic_priorities())
        import random
        keys = list(range(100))
        random.Random(42).shuffle(keys)
        for k in keys:
            t[k] = k * 2
        result = list(t.items())
        self.assertEqual([k for k, _ in result], sorted(keys))
        self.assertEqual([v for _, v in result], [k * 2 for k in sorted(keys)])

    def test_iter_yields_keys(self):
        t = TreapMap(deterministic_priorities())
        for k in [3, 1, 2]:
            t[k] = k
        self.assertEqual(list(t), [1, 2, 3])

    def test_values_match_items(self):
        t = TreapMap(deterministic_priorities())
        for k in [5, 2, 8]:
            t[k] = chr(k + 60)
        values = list(t.values())
        self.assertEqual(values, [chr(k + 60) for k in [2, 5, 8]])

    def test_iteration_empty(self):
        t = TreapMap(deterministic_priorities())
        self.assertEqual(list(t.items()), [])


class TestOrderedStatistics(unittest.TestCase):
    def test_kth_basic(self):
        t = TreapMap(deterministic_priorities())
        for k in [10, 20, 30, 40, 50]:
            t[k] = -k
        self.assertEqual(t.kth(0), (10, -10))
        self.assertEqual(t.kth(2), (30, -30))
        self.assertEqual(t.kth(4), (50, -50))

    def test_kth_out_of_range_raises(self):
        t = TreapMap(deterministic_priorities())
        t[1] = 1
        with self.assertRaises(IndexError):
            t.kth(-1)
        with self.assertRaises(IndexError):
            t.kth(1)

    def test_kth_after_deletions(self):
        t = TreapMap(deterministic_priorities())
        for k in range(10):
            t[k] = k
        del t[3]
        del t[7]
        # remaining: 0,1,2,4,5,6,8,9
        self.assertEqual(t.kth(3), (4, 4))
        self.assertEqual(t.kth(6), (8, 8))


class TestSplit(unittest.TestCase):
    def test_split_partitions_keys(self):
        t = TreapMap(deterministic_priorities())
        for k in range(20):
            t[k] = k
        left, right = t.split(10)
        self.assertEqual(list(left), list(range(10)))
        self.assertEqual(list(right), list(range(10, 20)))
        self.assertEqual(len(left), 10)
        self.assertEqual(len(right), 10)
        # source emptied
        self.assertEqual(len(t), 0)

    def test_split_at_min_and_max(self):
        t = TreapMap(deterministic_priorities())
        for k in [5, 10, 15]:
            t[k] = k
        left, right = t.split(5)
        self.assertEqual(list(left), [])
        self.assertEqual(list(right), [5, 10, 15])

        t2 = TreapMap(deterministic_priorities())
        for k in [5, 10, 15]:
            t2[k] = k
        left2, right2 = t2.split(20)
        self.assertEqual(list(left2), [5, 10, 15])
        self.assertEqual(list(right2), [])

    def test_split_empty(self):
        t = TreapMap(deterministic_priorities())
        left, right = t.split(0)
        self.assertEqual(len(left), 0)
        self.assertEqual(len(right), 0)

    def test_split_with_duplicate_boundary_key(self):
        # Split key matches a present key; that key lands on the right side
        # because the convention is left = keys < split key.
        t = TreapMap(deterministic_priorities())
        for k in [1, 2, 2, 3]:  # duplicates collapse to one entry
            t[k] = k
        left, right = t.split(2)
        self.assertEqual(list(left), [1])
        self.assertEqual(list(right), [2, 3])


class TestMerge(unittest.TestCase):
    def test_merge_disjoint_ranges(self):
        a = TreapMap(deterministic_priorities())
        b = TreapMap(deterministic_priorities())
        for k in range(10):
            a[k] = k
        for k in range(10, 20):
            b[k] = k
        m = TreapMap.merge(a, b)
        self.assertEqual(list(m), list(range(20)))
        # sources emptied
        self.assertEqual(len(a), 0)
        self.assertEqual(len(b), 0)

    def test_merge_empty_left(self):
        b = TreapMap(deterministic_priorities())
        for k in range(5):
            b[k] = k
        m = TreapMap.merge(TreapMap(deterministic_priorities()), b)
        self.assertEqual(list(m), [0, 1, 2, 3, 4])

    def test_merge_empty_right(self):
        a = TreapMap(deterministic_priorities())
        for k in range(5):
            a[k] = k
        m = TreapMap.merge(a, TreapMap(deterministic_priorities()))
        self.assertEqual(list(m), [0, 1, 2, 3, 4])

    def test_merge_two_empties(self):
        m = TreapMap.merge(
            TreapMap(deterministic_priorities()),
            TreapMap(deterministic_priorities()),
        )
        self.assertEqual(len(m), 0)


class TestMinAndMax(unittest.TestCase):
    def test_min_max(self):
        t = TreapMap(deterministic_priorities())
        for k in [7, 3, 11, 1, 9]:
            t[k] = k
        self.assertEqual(t.min(), (1, 1))
        self.assertEqual(t.max(), (11, 11))

    def test_min_max_empty_raises(self):
        t = TreapMap(deterministic_priorities())
        with self.assertRaises(KeyError):
            t.min()
        with self.assertRaises(KeyError):
            t.max()


class TestDeterminism(unittest.TestCase):
    def test_same_priorities_same_shape(self):
        # Two treaps built with the same priority sequence should produce the
        # same in-order iteration (trivially true) AND the same kth sequence,
        # which exercises structural equality at the order-statistics layer.
        keys = list(range(30))
        import random
        random.Random(7).shuffle(keys)

        t1 = TreapMap(deterministic_priorities())
        t2 = TreapMap(deterministic_priorities())
        for k in keys:
            t1[k] = k
            t2[k] = k
        for i in range(len(keys)):
            self.assertEqual(t1.kth(i), t2.kth(i))


class TestNodeExport(unittest.TestCase):
    def test_node_is_exported(self):
        # The README and __all__ promise TreapNode is part of the public API.
        self.assertTrue(hasattr(TreapNode, "__init__"))
        n = TreapNode(1, "v", 0.5)
        self.assertEqual(n.key, 1)
        self.assertEqual(n.value, "v")
        self.assertEqual(n.priority, 0.5)
        self.assertEqual(n.size, 1)


if __name__ == "__main__":
    unittest.main()
