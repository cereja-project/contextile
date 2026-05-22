"""Contextile: compact project context for LLM workflows."""

from .models import Lesson
from .store import LessonStore
from .retrieval import search_lessons
from .renderer import build_context
from .rules import select_rules_for_task, detect_project_profiles

from cereja.utils import get_version_pep440_compliant

__all__ = [
    "Lesson",
    "LessonStore",
    "search_lessons",
    "build_context",
    "select_rules_for_task",
    "detect_project_profiles",
]

VERSION = "0.1.0.final.0"
__version__ = get_version_pep440_compliant(VERSION)
