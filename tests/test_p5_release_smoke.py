import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "scripts/p5_release_smoke.py").read_text()


class TestP5ReleaseSmoke(unittest.TestCase):
    def test_runner_requires_preprovisioned_site(self):
        self.assertIn("provision the disposable site separately", SOURCE)
        self.assertNotIn("site creation", SOURCE.lower())
        self.assertNotIn("site removal", SOURCE.lower())

    def test_migrate_is_explicit_opt_in(self):
        self.assertIn('parser.add_argument("--migrate", action="store_true"', SOURCE)
        self.assertIn("if args.migrate:", SOURCE)
        self.assertIn('"migrate_executed"', SOURCE)

    def test_runner_requires_doctor_pass_before_and_after(self):
        self.assertGreaterEqual(SOURCE.count("doctor(bench, args.site)"), 2)
        self.assertIn('data.get("status") != "PASS"', SOURCE)


if __name__ == "__main__":
    unittest.main()
