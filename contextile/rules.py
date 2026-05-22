from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any


class RuleValidationError(ValueError):
    """Raised when a rule file or rules config is invalid."""


@dataclass(frozen=True)
class RuleScenario:
    id: str
    description: str
    profiles: list[str]
    rule_ids: list[str]


@dataclass(frozen=True)
class Rule:
    id: str
    path: Path
    title: str
    body: str
    apply: str = ""
    instructions: str = ""
    profiles: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    match_deps: list[str] = field(default_factory=list)
    match_files: list[str] = field(default_factory=list)
    always: bool = False
    priority: int = 50
    mode: str = "advisory"

    def validate(self) -> None:
        if not self.id:
            raise RuleValidationError(f"Rule id is required: {self.path}")
        if not _is_stable_id(self.id):
            raise RuleValidationError(
                f"Invalid rule id '{self.id}' in {self.path}. "
                "Use lowercase letters, numbers, hyphens, underscores, or dots."
            )
        if self.mode not in {"advisory", "required"}:
            raise RuleValidationError(
                f"Invalid mode '{self.mode}' in {self.path}. Use 'advisory' or 'required'."
            )


@dataclass(frozen=True)
class RuleSelection:
    rule: Rule
    score: float
    reasons: list[str]


@dataclass(frozen=True)
class ProjectRuleSettings:
    rules_dir: str = ".aiassistant/rules"
    base_profiles: list[str] = field(default_factory=lambda: ["python", "tests"])
    enable_profiles: list[str] = field(default_factory=list)
    disable_profiles: list[str] = field(default_factory=list)
    enabled_scenarios: list[str] = field(default_factory=list)
    force_rules: list[str] = field(default_factory=list)
    disable_rules: list[str] = field(default_factory=list)


DEFAULT_PROJECT_RULES_CONFIG = {
    "version": 1,
    "rules_dir": ".aiassistant/rules",
    "base_profiles": ["python", "tests"],
    "enable_profiles": [],
    "disable_profiles": [],
    "enabled_scenarios": [],
    "force_rules": [],
    "disable_rules": [],
}


_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_./-]+")
_STOP_TOKENS = {"py", "md", "txt", "json", "yaml", "yml", "toml", "ini"}
_KNOWN_DEPENDENCIES = (
    "pytest",
    "sqlalchemy",
    "alembic",
    "fastapi",
    "django",
    "flask",
    "pydantic",
)

_SCENARIO_DEFINITIONS: tuple[tuple[str, str, list[str]], ...] = (
    ("python-core", "Base Python rules for coding standards and architecture.", ["python"]),
    ("pytest-tests", "Pytest and test-quality rules.", ["tests", "pytest"]),
    ("fastapi-api", "FastAPI API architecture, schemas, dependencies, and error handling rules.", ["fastapi"]),
    ("sqlalchemy-orm", "SQLAlchemy ORM and persistence rules.", ["sqlalchemy"]),
    ("docs-architecture", "Documentation and architecture decision rules.", ["docs"]),
    (
        "python-backend-full",
        "Combined profile for Python backend projects (python, tests, FastAPI, SQLAlchemy, docs).",
        ["python", "tests", "pytest", "fastapi", "sqlalchemy", "docs"],
    ),
)
_DEFAULT_RULES_DIR = Path(__file__).resolve().parent / "default_rules"


def project_rules_path_for_root(root: str | Path = ".") -> Path:
    return Path(root) / ".contextile" / "project-rules.json"


def load_project_rule_settings(root: str | Path = ".") -> ProjectRuleSettings:
    path = project_rules_path_for_root(root)
    if not path.exists():
        return ProjectRuleSettings()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuleValidationError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise RuleValidationError(f"Invalid rules config in {path}: expected a JSON object.")

    return ProjectRuleSettings(
        rules_dir=_normalize_string(data.get("rules_dir")) or ".aiassistant/rules",
        base_profiles=_normalize_list(data.get("base_profiles"), lower=True),
        enable_profiles=_normalize_list(data.get("enable_profiles"), lower=True),
        disable_profiles=_normalize_list(data.get("disable_profiles"), lower=True),
        enabled_scenarios=_normalize_list(data.get("enabled_scenarios"), lower=True),
        force_rules=_normalize_list(data.get("force_rules"), lower=True),
        disable_rules=_normalize_list(data.get("disable_rules"), lower=True),
    )


def detect_project_dependencies(root: str | Path = ".") -> set[str]:
    root_path = Path(root)
    found: set[str] = set()
    candidates: list[Path] = [root_path / "pyproject.toml"]
    candidates.extend(sorted(root_path.glob("requirements*.txt")))

    for path in candidates:
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for dependency in _KNOWN_DEPENDENCIES:
            if re.search(rf"\b{re.escape(dependency)}\b", text):
                found.add(dependency)

    return found


def detect_project_profiles(root: str | Path = ".") -> dict[str, str]:
    root_path = Path(root)
    profiles: dict[str, str] = {}
    dependencies = detect_project_dependencies(root_path)

    if (root_path / "pyproject.toml").exists() or any(root_path.glob("**/*.py")):
        profiles["python"] = "Python project detected by pyproject.toml or .py files."

    if "pytest" in dependencies or (root_path / "tests").exists():
        profiles["tests"] = "tests/ directory or pytest dependency detected."
        profiles["pytest"] = "Pytest usage detected by dependency or project layout."

    if {"sqlalchemy", "alembic"} & dependencies or (root_path / "alembic.ini").exists():
        profiles["sqlalchemy"] = "SQLAlchemy/Alembic dependency or alembic.ini detected."

    if "fastapi" in dependencies:
        profiles["fastapi"] = "FastAPI dependency detected."

    if "django" in dependencies:
        profiles["django"] = "Django dependency detected."

    if "flask" in dependencies:
        profiles["flask"] = "Flask dependency detected."

    if (root_path / "docs").exists():
        profiles["docs"] = "docs/ directory detected."

    return profiles


def resolve_active_profiles(
    root: str | Path = ".",
    settings: ProjectRuleSettings | None = None,
) -> tuple[list[str], dict[str, str]]:
    settings = settings or load_project_rule_settings(root)
    detected = detect_project_profiles(root)

    active = set(settings.base_profiles)
    active.update(detected.keys())
    active.update(settings.enable_profiles)
    active.difference_update(settings.disable_profiles)

    return sorted(active), detected


def load_rules(
    root: str | Path = ".",
    *,
    rules_dir: str | None = None,
) -> list[Rule]:
    root_path = Path(root)
    if rules_dir is None:
        rules_dir = load_project_rule_settings(root_path).rules_dir

    base_dir = root_path / rules_dir
    local_rules = _load_rules_from_dir(base_dir)
    default_rules = _load_rules_from_dir(_DEFAULT_RULES_DIR)

    # Defaults are always available; project rules override same id.
    return _merge_rules(default_rules, local_rules)


def validate_rules(root: str | Path = ".", *, rules_dir: str | None = None) -> tuple[int, list[str]]:
    errors: list[str] = []
    root_path = Path(root)
    selected_rules_dir = rules_dir or load_project_rule_settings(root_path).rules_dir
    directories = [root_path / selected_rules_dir, _DEFAULT_RULES_DIR]
    seen_paths: set[Path] = set()

    for directory in directories:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            try:
                _read_rule(path)
            except RuleValidationError as exc:
                errors.append(str(exc))

    return len(errors), errors


def list_rule_scenarios(
    root: str | Path = ".",
    *,
    rules: list[Rule] | None = None,
    rules_dir: str | None = None,
) -> list[RuleScenario]:
    root_path = Path(root)
    loaded_rules = rules if rules is not None else load_rules(root_path, rules_dir=rules_dir)
    scenarios: list[RuleScenario] = []

    for scenario_id, description, profiles in _SCENARIO_DEFINITIONS:
        profile_set = set(profiles)
        rule_ids = sorted(
            {
                rule.id
                for rule in loaded_rules
                if profile_set & set(rule.profiles)
            }
        )
        if rule_ids:
            scenarios.append(
                RuleScenario(
                    id=scenario_id,
                    description=description,
                    profiles=profiles,
                    rule_ids=rule_ids,
                )
            )
    return scenarios


def update_enabled_scenarios(
    root: str | Path,
    scenario_ids: list[str],
    *,
    replace: bool = False,
) -> tuple[Path, list[str]]:
    root_path = Path(root)
    path = project_rules_path_for_root(root_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    known_scenarios = {scenario.id for scenario in list_rule_scenarios(root_path)}
    requested = _normalize_list(scenario_ids, lower=True)
    unknown = sorted(set(requested) - known_scenarios)
    if unknown:
        raise RuleValidationError(
            f"Unknown scenario(s): {', '.join(unknown)}. "
            "Use 'contextile list-rule-scenarios' to inspect available names."
        )

    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuleValidationError(f"Invalid JSON in {path}: {exc}") from exc
    else:
        data = dict(DEFAULT_PROJECT_RULES_CONFIG)

    current = _normalize_list(data.get("enabled_scenarios", []), lower=True)
    if replace:
        merged = requested
    else:
        merged = _normalize_unique(current + requested)

    data["enabled_scenarios"] = merged
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path, merged


def select_rules_for_task(
    *,
    root: str | Path = ".",
    task: str,
    files: list[str] | None = None,
    tags: list[str] | None = None,
    limit: int = 6,
) -> list[RuleSelection]:
    root_path = Path(root)
    files = files or []
    tags = tags or []
    settings = load_project_rule_settings(root_path)
    active_profiles, _ = resolve_active_profiles(root_path, settings)
    dependencies = detect_project_dependencies(root_path)
    rules = load_rules(root_path, rules_dir=settings.rules_dir)
    enabled_scenario_rule_ids = _resolve_enabled_scenario_rule_ids(
        enabled_scenarios=settings.enabled_scenarios,
        root=root_path,
        rules=rules,
    )

    query_text = " ".join([task, " ".join(files), " ".join(tags)])
    query_tokens = _tokenize(query_text)

    selections: list[RuleSelection] = []
    for rule in rules:
        if rule.id in settings.disable_rules:
            continue
        if enabled_scenario_rule_ids and rule.id not in enabled_scenario_rule_ids and rule.id not in settings.force_rules:
            continue

        score, reasons = _score_rule(
            rule,
            query_tokens=query_tokens,
            file_hints=files,
            requested_tags=tags,
            active_profiles=active_profiles,
            detected_dependencies=dependencies,
        )
        if enabled_scenario_rule_ids and rule.id in enabled_scenario_rule_ids:
            score += 20
            reasons.append("enabled scenario")

        if rule.id in settings.force_rules:
            score += 120
            reasons.append("forced by project-rules.json")

        if score > 0:
            selections.append(RuleSelection(rule=rule, score=score, reasons=reasons))

    selections.sort(key=lambda item: (-item.score, -item.rule.priority, item.rule.id))
    return selections[: max(0, limit)]


def _read_rule(path: Path) -> Rule:
    text = path.read_text(encoding="utf-8", errors="ignore")
    metadata, body = _split_frontmatter(text)
    title = _extract_title(body) or path.stem
    inferred_profiles = _infer_profiles_from_filename(path.stem)
    inferred_tags = _tokenize(path.stem.replace("-", " ")) | set(inferred_profiles)
    explicit_tags = _normalize_list(metadata.get("tags", []), lower=True)

    rule = Rule(
        id=_normalize_string(metadata.get("id")) or path.stem.lower(),
        path=path,
        title=title,
        body=body.strip(),
        apply=_normalize_string(metadata.get("apply")),
        instructions=_normalize_string(metadata.get("instructions")),
        profiles=_normalize_unique(inferred_profiles + _normalize_list(metadata.get("profiles", []), lower=True)),
        tags=_normalize_unique(explicit_tags + sorted(inferred_tags)),
        match_deps=_normalize_list(metadata.get("match_deps", []), lower=True),
        match_files=_normalize_list(metadata.get("match_files", []), lower=False),
        always=_to_bool(metadata.get("always")),
        priority=_to_int(metadata.get("priority"), default=50),
        mode=(_normalize_string(metadata.get("mode")) or "advisory").lower(),
    )
    rule.validate()
    return rule


def _load_rules_from_dir(path: Path) -> list[Rule]:
    if not path.exists():
        return []
    return [_read_rule(rule_path) for rule_path in sorted(path.glob("*.md"))]


def _merge_rules(*rule_groups: list[Rule]) -> list[Rule]:
    by_id: dict[str, Rule] = {}
    for rules in rule_groups:
        for rule in rules:
            by_id[rule.id] = rule
    return sorted(by_id.values(), key=lambda rule: rule.id)


def _score_rule(
    rule: Rule,
    *,
    query_tokens: set[str],
    file_hints: list[str],
    requested_tags: list[str],
    active_profiles: list[str],
    detected_dependencies: set[str],
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    if rule.always:
        score += 90
        reasons.append("always=true")

    if rule.mode == "required":
        score += 15
        reasons.append("mode=required")

    dep_matches = set(rule.match_deps) & detected_dependencies
    if dep_matches:
        score += 28 * len(dep_matches)
        reasons.append("dependency: " + ", ".join(sorted(dep_matches)))

    if requested_tags:
        tag_matches = set(map(str.lower, requested_tags)) & set(rule.tags)
        if tag_matches:
            score += 10 * len(tag_matches)
            reasons.append("tag: " + ", ".join(sorted(tag_matches)))

    file_matches = _match_file_hints(file_hints, rule.match_files)
    if file_matches:
        score += 16 * len(file_matches)
        reasons.append("file: " + ", ".join(sorted(file_matches)))

    token_matches = query_tokens & _rule_tokens(rule)
    if token_matches:
        score += min(24, 2 * len(token_matches))
        reasons.append("task tokens: " + ", ".join(sorted(token_matches)[:6]))

    rule_profiles = set(rule.profiles)
    profile_matches = rule_profiles & set(active_profiles)
    if profile_matches:
        if (profile_matches & query_tokens) or dep_matches or file_matches:
            score += 22 + (6 * len(profile_matches))
            reasons.append("profile: " + ", ".join(sorted(profile_matches)))
        elif rule.always or rule.mode == "required":
            score += 8
            reasons.append("profile baseline: " + ", ".join(sorted(profile_matches)))

    return score, reasons


def _rule_tokens(rule: Rule) -> set[str]:
    return _tokenize(
        " ".join(
            [
                rule.id,
                rule.title,
                rule.instructions,
                " ".join(rule.tags),
                " ".join(rule.profiles),
                rule.body[:2000],
            ]
        )
    )


def _match_file_hints(file_hints: list[str], patterns: list[str]) -> set[str]:
    if not file_hints or not patterns:
        return set()

    matched: set[str] = set()
    for hint in file_hints:
        normalized_hint = hint.replace("\\", "/").strip()
        for pattern in patterns:
            normalized_pattern = pattern.replace("\\", "/").strip()
            if normalized_pattern and fnmatch(normalized_hint, normalized_pattern):
                matched.add(normalized_pattern)
    return matched


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_index = None
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = idx
            break

    if end_index is None:
        raise RuleValidationError("Unclosed frontmatter block. Expected closing '---'.")

    frontmatter = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :]).lstrip("\n")
    return _parse_frontmatter(frontmatter), body


def _parse_frontmatter(frontmatter: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list_key: str | None = None

    for raw_line in frontmatter.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("- ") and current_list_key:
            current = data.get(current_list_key)
            if not isinstance(current, list):
                current = []
                data[current_list_key] = current
            current.append(_parse_scalar(line[2:].strip()))
            continue

        current_list_key = None
        if ":" not in raw_line:
            continue

        key, value = raw_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if not value:
            data[key] = []
            current_list_key = key
            continue

        data[key] = _parse_scalar(value)

    return data


def _parse_scalar(value: str) -> Any:
    stripped = value.strip()
    lower = stripped.lower()

    if (stripped.startswith('"') and stripped.endswith('"')) or (
        stripped.startswith("'") and stripped.endswith("'")
    ):
        return stripped[1:-1].strip()

    if stripped.startswith("[") and stripped.endswith("]"):
        inside = stripped[1:-1].strip()
        if not inside:
            return []
        return [_parse_scalar(part.strip()) for part in inside.split(",")]

    if lower in {"true", "yes", "on"}:
        return True
    if lower in {"false", "no", "off"}:
        return False

    if re.fullmatch(r"-?\d+", stripped):
        return int(stripped)

    return stripped


def _infer_profiles_from_filename(stem: str) -> list[str]:
    normalized = stem.lower()
    profiles: list[str] = []
    if "python" in normalized:
        profiles.append("python")
    if "fastapi" in normalized:
        profiles.append("fastapi")
    if "test" in normalized or "pytest" in normalized:
        profiles.append("tests")
        if "pytest" in normalized:
            profiles.append("pytest")
    if "sqlalchemy" in normalized or "alembic" in normalized:
        profiles.append("sqlalchemy")
    if "doc" in normalized:
        profiles.append("docs")
    return _normalize_unique(profiles)


def _extract_title(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def _tokenize(text: str) -> set[str]:
    tokens = set()
    for token in _TOKEN_PATTERN.findall(text.lower()):
        token = token.strip("._-/")
        if len(token) >= 2:
            if token not in _STOP_TOKENS:
                tokens.add(token)
            for part in re.split(r"[._/-]+", token):
                if len(part) >= 2 and part not in _STOP_TOKENS:
                    tokens.add(part)
    return tokens


def _normalize_list(value: Any, *, lower: bool) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        raw_items = [str(item).strip() for item in value]
    else:
        return []

    items: list[str] = []
    for item in raw_items:
        if not item:
            continue
        normalized = item.lower() if lower else item
        items.append(normalized)
    return _normalize_unique(items)


def _normalize_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def _normalize_string(value: Any) -> str:
    return str(value or "").strip()


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _to_int(value: Any, *, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"-?\d+", value.strip()):
        return int(value.strip())
    return default


def _is_stable_id(value: str) -> bool:
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-_.")
    return bool(value) and all(char in allowed for char in value)


def _resolve_enabled_scenario_rule_ids(
    *,
    enabled_scenarios: list[str],
    root: Path,
    rules: list[Rule],
) -> set[str]:
    if not enabled_scenarios:
        return set()
    scenario_map = {scenario.id: scenario for scenario in list_rule_scenarios(root, rules=rules)}
    unknown = sorted(set(enabled_scenarios) - set(scenario_map.keys()))
    if unknown:
        raise RuleValidationError(
            f"Unknown scenario(s) in project-rules.json: {', '.join(unknown)}. "
            "Use 'contextile list-rule-scenarios' to inspect available names."
        )

    selected_ids: set[str] = set()
    for scenario_id in enabled_scenarios:
        selected_ids.update(scenario_map[scenario_id].rule_ids)
    return selected_ids
