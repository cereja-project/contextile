import unittest

from contextile.models import Lesson
from contextile.retrieval import search_lessons


class RetrievalTests(unittest.TestCase):
    def test_search_prioritizes_tag_and_query_matches(self):
        lessons = [
            Lesson.from_dict(
                {
                    "id": "preserve-api-contracts",
                    "when": "Editing public API responses or request schemas.",
                    "do": "Preserve existing API contracts unless explicitly requested.",
                    "avoid": "Do not rename response fields unexpectedly.",
                    "tags": ["api", "contracts"],
                }
            ),
            Lesson.from_dict(
                {
                    "id": "docs-style",
                    "when": "Writing README or documentation pages.",
                    "do": "Use concise examples and clear headings.",
                    "avoid": "Do not add outdated implementation details.",
                    "tags": ["docs"],
                }
            ),
        ]
        results = search_lessons(lessons, "change api validation", tags=["api"], limit=2)
        self.assertEqual(results[0].lesson.id, "preserve-api-contracts")


if __name__ == "__main__":
    unittest.main()
