import json
import tempfile
import unittest
from pathlib import Path

from contextile.rules import (
    detect_project_profiles,
    list_rule_scenarios,
    load_project_rule_settings,
    project_rules_path_for_root,
    select_rules_for_task,
    update_enabled_scenarios,
    validate_rules,
)


class RulesTests(unittest.TestCase):
    def test_detects_profiles_from_project_layout_and_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir(parents=True, exist_ok=True)
            (root / "pyproject.toml").write_text(
                """
[project]
dependencies = ["sqlalchemy", "pytest"]
""".strip()
                + "\n",
                encoding="utf-8",
            )

            profiles = detect_project_profiles(root)

            self.assertIn("python", profiles)
            self.assertIn("tests", profiles)
            self.assertIn("pytest", profiles)
            self.assertIn("sqlalchemy", profiles)

    def test_select_rules_for_task_uses_profiles_and_file_hints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".aiassistant" / "rules").mkdir(parents=True, exist_ok=True)
            (root / ".contextile").mkdir(parents=True, exist_ok=True)

            (root / "pyproject.toml").write_text(
                """
[project]
dependencies = ["sqlalchemy", "pytest"]
""".strip()
                + "\n",
                encoding="utf-8",
            )

            (root / ".contextile" / "project-rules.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "rules_dir": ".aiassistant/rules",
                        "base_profiles": ["python"],
                        "enable_profiles": [],
                        "disable_profiles": [],
                        "force_rules": [],
                        "disable_rules": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            (root / ".aiassistant" / "rules" / "sqlalchemy-rule.md").write_text(
                """---
id: sqlalchemy-mapping
profiles: [sqlalchemy]
match_deps: [sqlalchemy]
match_files: ["**/models/*.py"]
mode: required
priority: 90
instructions: Use SQLAlchemy 2.0 mapped types.
---
# SQLAlchemy Mapping

Use DeclarativeBase and mapped_column.
""",
                encoding="utf-8",
            )
            (root / ".aiassistant" / "rules" / "docs-rule.md").write_text(
                """---
id: docs-architecture
profiles: [docs]
instructions: Keep ADR records updated.
---
# Docs
Update architecture docs.
""",
                encoding="utf-8",
            )

            selections = select_rules_for_task(
                root=root,
                task="Add mapping for customer model",
                files=["src/models/customer.py"],
                tags=["orm"],
                limit=5,
            )

            self.assertGreaterEqual(len(selections), 1)
            self.assertEqual(selections[0].rule.id, "sqlalchemy-mapping")
            self.assertEqual(selections[0].rule.mode, "required")

    def test_validate_rules_reports_invalid_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".aiassistant" / "rules").mkdir(parents=True, exist_ok=True)
            (root / ".contextile").mkdir(parents=True, exist_ok=True)
            project_rules_path_for_root(root).write_text(
                json.dumps(
                    {
                        "version": 1,
                        "rules_dir": ".aiassistant/rules",
                        "base_profiles": ["python"],
                        "enable_profiles": [],
                        "disable_profiles": [],
                        "force_rules": [],
                        "disable_rules": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".aiassistant" / "rules" / "bad.md").write_text(
                """---
id: bad-mode
mode: strict
---
# Bad
""",
                encoding="utf-8",
            )

            error_count, errors = validate_rules(root)
            self.assertEqual(error_count, 1)
            self.assertIn("Invalid mode", errors[0])

    def test_project_rules_default_when_file_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = load_project_rule_settings(tmp)
            self.assertEqual(settings.rules_dir, ".aiassistant/rules")
            self.assertIn("python", settings.base_profiles)

    def test_list_scenarios_and_apply_scenario(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".aiassistant" / "rules").mkdir(parents=True, exist_ok=True)
            (root / ".aiassistant" / "rules" / "10-python-principios.md").write_text(
                "# Python Rules\n",
                encoding="utf-8",
            )
            (root / ".aiassistant" / "rules" / "06-pytest-fixtures.md").write_text(
                "# Pytest Rules\n",
                encoding="utf-8",
            )
            (root / ".aiassistant" / "rules" / "20-fastapi-estrutura.md").write_text(
                "# FastAPI Rules\n",
                encoding="utf-8",
            )

            scenarios = list_rule_scenarios(root)
            scenario_ids = {scenario.id for scenario in scenarios}
            self.assertIn("python-core", scenario_ids)
            self.assertIn("pytest-tests", scenario_ids)
            self.assertIn("fastapi-api", scenario_ids)

            path, enabled = update_enabled_scenarios(root, ["python-core"])
            self.assertTrue(path.exists())
            self.assertEqual(enabled, ["python-core"])

            settings = load_project_rule_settings(root)
            self.assertEqual(settings.enabled_scenarios, ["python-core"])

    def test_list_scenarios_uses_builtin_catalog_when_project_has_no_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenarios = list_rule_scenarios(root)
            scenario_ids = {scenario.id for scenario in scenarios}
            self.assertIn("python-core", scenario_ids)
            self.assertIn("pytest-tests", scenario_ids)

    def test_select_rules_uses_builtin_catalog_when_project_has_no_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir(parents=True, exist_ok=True)
            (root / "pyproject.toml").write_text(
                """
[project]
dependencies = ["pytest"]
""".strip()
                + "\n",
                encoding="utf-8",
            )

            selections = select_rules_for_task(
                root=root,
                task="improve pytest fixtures for tests",
                files=["tests/test_example.py"],
                limit=5,
            )

            self.assertGreaterEqual(len(selections), 1)
            selected_ids = [item.rule.id for item in selections]
            self.assertTrue(any(("pytest" in rule_id) or ("test" in rule_id) for rule_id in selected_ids))

    def test_select_rules_matches_agents_md_rule_from_builtin_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "pyproject.toml").write_text(
                """
[project]
name = "sample"
version = "0.1.0"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            selections = select_rules_for_task(
                root=root,
                task="create AGENTS.md for coding agents",
                files=["AGENTS.md"],
                tags=["documentation"],
                limit=10,
            )

            selected_ids = [item.rule.id for item in selections]
            self.assertIn("42-doc-agents-md", selected_ids)

    def test_select_rules_respects_enabled_scenarios(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".aiassistant" / "rules").mkdir(parents=True, exist_ok=True)
            (root / ".contextile").mkdir(parents=True, exist_ok=True)
            (root / ".aiassistant" / "rules" / "10-python-principios.md").write_text(
                "# Python Rules\n",
                encoding="utf-8",
            )
            (root / ".aiassistant" / "rules" / "41-doc-arquitetura.md").write_text(
                "# Docs Rules\n",
                encoding="utf-8",
            )
            project_rules_path_for_root(root).write_text(
                json.dumps(
                    {
                        "version": 1,
                        "rules_dir": ".aiassistant/rules",
                        "base_profiles": ["python"],
                        "enable_profiles": [],
                        "disable_profiles": [],
                        "enabled_scenarios": ["docs-architecture"],
                        "force_rules": [],
                        "disable_rules": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            selections = select_rules_for_task(
                root=root,
                task="update architecture docs",
                files=["docs/architecture.md"],
                limit=5,
            )
            self.assertGreaterEqual(len(selections), 1)
            selected_ids = [item.rule.id for item in selections]
            self.assertIn("41-doc-arquitetura", selected_ids)


if __name__ == "__main__":
    unittest.main()
