import unittest

from erpnext_vietnam.integration.idempotency import make_idempotency_key


class TestIdempotency(unittest.TestCase):
    def test_same_input_same_key(self):
        a = make_idempotency_key("company-a", "01/GTGT", "2026-Q3", "submit")
        b = make_idempotency_key("company-a", "01/GTGT", "2026-Q3", "submit")
        self.assertEqual(a, b)

    def test_changed_operation_changes_key(self):
        self.assertNotEqual(make_idempotency_key("a", "b", "submit"), make_idempotency_key("a", "b", "replace"))


if __name__ == "__main__":
    unittest.main()
