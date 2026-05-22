import tempfile
import unittest
from pathlib import Path

from contextile.mcp_server import (
    tool_add_lesson,
    tool_apply_rule_scenario,
    tool_build_agents_md,
    tool_build_context,
    tool_detect_rules,
    tool_list_rule_scenarios,
    tool_search_lessons,
    tool_select_rules,
    tool_validate_rules,
)
from contextile.models import LessonValidationError
from contextile.workspace import init_workspace, lessons_path_for_root


class McpServerToolTests(unittest.TestCase):
    def test_tool_build_context_and_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace(root)
            add_result = tool_add_lesson(
                id="preserve-domain-terms",
                when="Editing public API names and contracts in code and docs.",
                do="Preserve established domain terms exactly.",
                avoid="Do not rename terms without explicit request.",
                tags=["api", "domain"],
                root=str(root),
            )
            self.assertEqual(
                add_result["path"],
                str(lessons_path_for_root(root)),
            )
            self.assertEqual(add_result["lesson"]["id"], "preserve-domain-terms")

            context_result = tool_build_context(
                task="Refactor API validation",
                root=str(root),
                files=["src/api/contracts.py"],
                tags=["api"],
                max_tokens=1000,
            )
            self.assertIn("context", context_result)
            self.assertGreater(context_result["estimated_tokens"], 0)

            search_result = tool_search_lessons(
                query="api contract terms",
                root=str(root),
                tags=["api"],
                limit=5,
            )
            self.assertEqual(search_result["count"], 1)
            self.assertEqual(search_result["results"][0]["id"], "preserve-domain-terms")

    def test_rule_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace(root)
            (root / ".aiassistant" / "rules").mkdir(parents=True, exist_ok=True)
            (root / "pyproject.toml").write_text(
                """
[project]
dependencies = ["sqlalchemy", "pytest"]
""".strip()
                + "\n",
                encoding="utf-8",
            )
            (root / ".aiassistant" / "rules" / "sqlalchemy-rule.md").write_text(
                """---
id: sqlalchemy-mapping
profiles: [sqlalchemy]
match_deps: [sqlalchemy]
instructions: Use SQLAlchemy 2.0 mapped types.
---
# SQLAlchemy Mapping

Use DeclarativeBase and mapped_column.
""",
                encoding="utf-8",
            )

            detect_result = tool_detect_rules(root=str(root))
            self.assertIn("sqlalchemy", detect_result["dependencies"])
            self.assertIn("sqlalchemy", detect_result["active_profiles"])

            select_result = tool_select_rules(
                task="Refactor SQLAlchemy models",
                root=str(root),
                files=["src/models/order.py"],
                limit=3,
            )
            self.assertGreaterEqual(select_result["count"], 1)
            self.assertEqual(select_result["results"][0]["id"], "sqlalchemy-mapping")

            validate_result = tool_validate_rules(root=str(root))
            self.assertTrue(validate_result["valid"])

            scenarios_result = tool_list_rule_scenarios(root=str(root))
            self.assertGreaterEqual(scenarios_result["count"], 1)

            apply_result = tool_apply_rule_scenario(
                root=str(root),
                scenarios=["sqlalchemy-orm"],
                replace=True,
            )
            self.assertEqual(apply_result["enabled_scenarios"], ["sqlalchemy-orm"])

    def test_tool_add_lesson_rejects_duplicate_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace(root)
            payload = {
                "id": "preserve-domain-terms",
                "when": "Editing public API names and contracts in code and docs.",
                "do": "Preserve established domain terms exactly.",
                "avoid": "Do not rename terms without explicit request.",
                "tags": ["api", "domain"],
                "root": str(root),
            }
            tool_add_lesson(**payload)
            with self.assertRaises(LessonValidationError):
                tool_add_lesson(**payload)

    def test_tool_build_agents_md_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace(root)
            (root / ".contextile" / "instructions" / "validation.md").write_text(
                """# Validation

```bash
python -m pytest
python -m ruff check .
```
""",
                encoding="utf-8",
            )
            tool_add_lesson(
                id="preserve-api-contracts",
                when="Editing existing API schemas and response fields in Python services.",
                do="Keep backward-compatible fields and types unless explicitly requested.",
                avoid="Do not break API consumers by removing or renaming fields silently.",
                tags=["api", "contracts"],
                root=str(root),
            )

            result = tool_build_agents_md(root=str(root))
            agents_path = root / "AGENTS.md"
            self.assertTrue(agents_path.exists())
            self.assertTrue(result["written"])
            self.assertIn("## Setup Commands", result["content"])
            self.assertIn("python -m pytest", result["content"])
            self.assertIn("## Lessons Learned", result["content"])
            self.assertIn("preserve-api-contracts", result["content"])

    def test_tool_build_agents_md_requires_overwrite_to_replace_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace(root)
            agents_path = root / "AGENTS.md"
            agents_path.write_text("# Existing file\n", encoding="utf-8")

            with self.assertRaises(LessonValidationError):
                tool_build_agents_md(root=str(root), write=True, overwrite=False)


if __name__ == "__main__":
    unittest.main()
