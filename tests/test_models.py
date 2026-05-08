import unittest

from contextile.models import Lesson, LessonValidationError


class LessonModelTests(unittest.TestCase):
    def test_normalizes_tags_from_string(self):
        lesson = Lesson.from_dict(
            {
                "id": "preserve-domain-terms",
                "when": "Editing existing domain terms in API contracts.",
                "do": "Preserve domain terms exactly as used.",
                "avoid": "Do not translate established domain terms.",
                "tags": "Domain, API, domain",
            }
        )
        self.assertEqual(lesson.tags, ["domain", "api"])

    def test_rejects_missing_required_fields(self):
        with self.assertRaises(LessonValidationError):
            Lesson.from_dict({"id": "bad", "when": "too short"})


if __name__ == "__main__":
    unittest.main()
