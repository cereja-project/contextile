import tempfile
import unittest
from pathlib import Path

from contextile.models import LessonValidationError
from contextile.store import LessonStore
from contextile.models import Lesson


class LessonStoreTests(unittest.TestCase):
    def test_append_and_list_lessons(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lessons.jsonl"
            store = LessonStore(path)
            lesson = Lesson.from_dict(
                {
                    "id": "minimal-changes",
                    "when": "Implementing a requested change in an existing codebase.",
                    "do": "Make the smallest safe change that satisfies the request.",
                    "avoid": "Do not refactor unrelated code or architecture.",
                    "tags": ["scope", "refactor"],
                }
            )
            store.append(lesson)
            self.assertEqual(store.list()[0].id, "minimal-changes")

    def test_duplicate_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lessons.jsonl"
            store = LessonStore(path)
            lesson = Lesson.from_dict(
                {
                    "id": "validate-before-final",
                    "when": "After editing code, tests, configuration, or documentation.",
                    "do": "Run or recommend the most relevant validation step.",
                    "avoid": "Do not claim validation was run unless it was run.",
                }
            )
            store.append(lesson)
            with self.assertRaises(LessonValidationError):
                store.append(lesson)


if __name__ == "__main__":
    unittest.main()
