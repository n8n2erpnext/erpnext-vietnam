import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestReleaseVersion(unittest.TestCase):
    def test_package_and_project_versions_match_rc(self):
        init_text = (ROOT / "erpnext_vietnam/__init__.py").read_text()
        pyproject = (ROOT / "pyproject.toml").read_text()
        init_version = re.search(r'__version__ = "([^"]+)"', init_text).group(1)
        project_version = re.search(r'^version = "([^"]+)"', pyproject, re.M).group(1)
        self.assertEqual(init_version, project_version)
        self.assertEqual(init_version, "0.1.0-rc1")
        self.assertNotIn("dev", init_version)


if __name__ == "__main__":
    unittest.main()
