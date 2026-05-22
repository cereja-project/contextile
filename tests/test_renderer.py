import json
import tempfile
import unittest
from pathlib import Path

from contextile.renderer import build_context


class RendererTests(unittest.TestCase):
    def test_build_context_includes_relevant_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".aiassistant" / "rules").mkdir(parents=True, exist_ok=True)
            (root / ".contextile").mkdir(parents=True, exist_ok=True)
            (root / ".contextile" / "instructions").mkdir(parents=True, exist_ok=True)
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
            (root / "pyproject.toml").write_text(
                """
[project]
dependencies = ["sqlalchemy"]
""".strip()
                + "\n",
                encoding="utf-8",
            )
            (root / ".aiassistant" / "rules" / "sqlalchemy.md").write_text(
                """---
id: sqlalchemy-mapping
profiles: [sqlalchemy]
instructions: Prefer SQLAlchemy 2.0 mapped annotations.
---
# SQLAlchemy Mapping

Use mapped_column and keep relationships explicit.
""",
                encoding="utf-8",
            )

            context = build_context(
                task="Refactor models for SQLAlchemy mapping",
                lessons=[],
                root=root,
                files=["src/models/order.py"],
                max_tokens=1200,
            )

            self.assertIn("## Relevant Rules", context)
            self.assertIn("sqlalchemy-mapping", context)

    def test_build_context_keeps_full_rule_body_without_token_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".aiassistant" / "rules").mkdir(parents=True, exist_ok=True)
            (root / ".contextile").mkdir(parents=True, exist_ok=True)
            (root / ".contextile" / "instructions").mkdir(parents=True, exist_ok=True)
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

            long_rule_body = "\n".join(
                [
                    "# Critical Rule",
                    "",
                    "Rule line 1: keep behavior consistent.",
                    "Rule line 2: enforce invariants.",
                    "Rule line 3: no silent regressions.",
                    "Rule line 4: this line must remain visible.",
                    "Rule line 5: final sentinel text 9f2f62f7.",
                ]
            )
            (root / ".aiassistant" / "rules" / "10-python-principios.md").write_text(
                f"""---
id: critical-python-rule
profiles: [python]
always: true
instructions: Always include this full rule.
---
{long_rule_body}
""",
                encoding="utf-8",
            )

            context = build_context(
                task="review python changes",
                lessons=[],
                root=root,
                files=["src/module.py"],
                max_tokens=20,
            )

            self.assertIn("## Relevant Rules", context)
            self.assertIn("critical-python-rule", context)
            self.assertIn("final sentinel text 9f2f62f7.", context)


if __name__ == "__main__":
    unittest.main()
