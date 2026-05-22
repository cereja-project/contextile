import tempfile
import unittest
from pathlib import Path

from contextile.workspace import init_workspace


class WorkspaceTests(unittest.TestCase):
    def test_init_creates_project_rules_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = init_workspace(root)
            created_set = {path.name for path in created}
            self.assertIn("project-rules.json", created_set)
            self.assertTrue((root / ".contextile" / "project-rules.json").exists())


if __name__ == "__main__":
    unittest.main()
