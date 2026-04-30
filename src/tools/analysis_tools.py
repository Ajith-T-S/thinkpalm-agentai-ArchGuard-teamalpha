"""Heuristic analysis tools for architecture review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from src.models.schemas import DependencyInfo, ProjectStructureFinding
from src.utils.helpers import list_top_level_modules


def detect_tech_stack(file_paths: Sequence[str], metadata_language: str | None = None) -> List[str]:
    stack = set()
    lower_paths = [p.lower() for p in file_paths]
    file_names = [Path(p).name.lower() for p in file_paths]
    path_suffixes = [Path(p).suffix.lower() for p in file_paths]

    if metadata_language:
        stack.add(metadata_language)

    if any(suffix == ".py" for suffix in path_suffixes) or any(
        name in {"requirements.txt", "pyproject.toml", "pipfile"} for name in file_names
    ):
        stack.add("python")

    if any(suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"} for suffix in path_suffixes) or any(
        name in {"yarn.lock", "pnpm-lock.yaml"} for name in file_names
    ):
        stack.add("node.js")
    if "package.json" in file_names:
        stack.add("node.js")

    if any(suffix == ".java" for suffix in path_suffixes) or any(
        name in {"pom.xml", "build.gradle"} for name in file_names
    ):
        stack.add("java")

    if any(suffix == ".go" for suffix in path_suffixes) or "go.mod" in file_names:
        stack.add("go")

    if any(suffix in {".csproj", ".sln", ".cs"} for suffix in path_suffixes):
        stack.add("dotnet")

    if any(name in {"dockerfile", "docker-compose.yml", "docker-compose.yaml"} for name in file_names):
        stack.add("docker")

    if any(".github/workflows/" in path for path in lower_paths):
        stack.add("github-actions")

    if any(suffix == ".tf" for suffix in path_suffixes) or any("terraform" in path for path in lower_paths):
        stack.add("terraform")

    if any("k8s" in path or "helm" in path for path in lower_paths) or "chart.yaml" in file_names:
        stack.add("kubernetes")

    if any("streamlit" in p for p in lower_paths):
        stack.add("streamlit")
    if any("django" in p for p in lower_paths):
        stack.add("django")
    if any("flask" in p for p in lower_paths):
        stack.add("flask")
    if any("fastapi" in p for p in lower_paths):
        stack.add("fastapi")

    return sorted(stack)


def parse_dependencies(file_contents: Dict[str, str]) -> List[DependencyInfo]:
    dependencies: List[DependencyInfo] = []

    if "requirements.txt" in file_contents:
        deps = [
            line.strip()
            for line in file_contents["requirements.txt"].splitlines()
            if line.strip() and not line.startswith("#")
        ]
        dependencies.append(DependencyInfo(ecosystem="python", dependencies=deps[:80], evidence_file="requirements.txt"))

    if "pyproject.toml" in file_contents:
        content = file_contents["pyproject.toml"]
        candidates = [line.strip() for line in content.splitlines() if "=" in line and "dependencies" in line.lower()]
        dependencies.append(
            DependencyInfo(
                ecosystem="python",
                dependencies=candidates[:80],
                evidence_file="pyproject.toml",
            )
        )

    if "package.json" in file_contents:
        try:
            data = json.loads(file_contents["package.json"])
            merged = dict(data.get("dependencies", {}))
            merged.update(data.get("devDependencies", {}))
            dependencies.append(
                DependencyInfo(
                    ecosystem="node",
                    dependencies=[f"{k}@{v}" for k, v in merged.items()][:100],
                    evidence_file="package.json",
                )
            )
        except json.JSONDecodeError:
            dependencies.append(
                DependencyInfo(
                    ecosystem="node",
                    dependencies=["Could not parse package.json"],
                    evidence_file="package.json",
                )
            )

    if "pom.xml" in file_contents:
        xml_lines = [line.strip() for line in file_contents["pom.xml"].splitlines() if "<artifactId>" in line]
        dependencies.append(DependencyInfo(ecosystem="java", dependencies=xml_lines[:80], evidence_file="pom.xml"))

    return dependencies


def analyze_project_structure(file_paths: Iterable[str]) -> ProjectStructureFinding:
    paths = list(file_paths)
    lower_paths = [p.lower() for p in paths]

    entry_points = [
        p
        for p in paths
        if Path(p).name in {"main.py", "app.py", "index.js", "index.ts", "server.js", "manage.py"}
    ][:30]

    config_files = [
        p
        for p in paths
        if Path(p).name.lower()
        in {
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "pom.xml",
            "build.gradle",
            "dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            ".env.example",
            "tsconfig.json",
            "angular.json",
        }
    ][:60]

    ci_files = [p for p in paths if ".github/workflows" in p or "azure-pipelines" in p.lower()][:40]
    container_files = [p for p in paths if "docker" in p.lower() or "k8s" in p.lower()][:40]

    key_directories = []
    for candidate in ["src/", "app/", "services/", "controllers/", "domain/", "infrastructure/", "tests/", "docs/"]:
        if any(path.startswith(candidate) for path in lower_paths):
            key_directories.append(candidate.rstrip("/"))

    modules = list_top_level_modules(paths)

    return ProjectStructureFinding(
        modules=modules,
        entry_points=entry_points,
        config_files=config_files,
        ci_files=ci_files,
        container_files=container_files,
        key_directories=key_directories,
    )


def detect_architecture_patterns(paths: Sequence[str], file_contents: Dict[str, str]) -> List[str]:
    patterns = set()
    lower_paths = [p.lower() for p in paths]

    if any("/controllers/" in p or "/routes/" in p for p in lower_paths):
        patterns.add("Layered web app with controller/routing boundaries")
    if any("/services/" in p for p in lower_paths):
        patterns.add("Service layer abstraction present")
    if any("/domain/" in p and "/infrastructure/" in p for p in lower_paths):
        patterns.add("Domain/infrastructure separation hints")
    if any("/tests/" in p or p.startswith("tests/") for p in lower_paths):
        patterns.add("Automated testing layout detected")
    if "docker-compose.yml" in lower_paths or "docker-compose.yaml" in lower_paths:
        patterns.add("Container orchestration for local/dev environments")
    if any(".github/workflows" in p for p in lower_paths):
        patterns.add("CI automation through GitHub Actions")
    if any("microservice" in content.lower() for content in file_contents.values()):
        patterns.add("Microservice intent referenced in repository content")

    if not patterns:
        patterns.add("No explicit architecture markers found; likely pragmatic modular structure")

    return sorted(patterns)


def detect_risks(
    paths: Sequence[str],
    dependencies: Sequence[DependencyInfo],
    focus: str = "general",
) -> List[str]:
    risks = []
    lower_paths = [p.lower() for p in paths]
    has_tests = any(p.startswith("tests/") or "/tests/" in p for p in lower_paths)
    python_deps = [dep for dep in dependencies if dep.ecosystem == "python"]
    has_env_files = any(Path(p).name.lower() in {".env", ".env.example"} for p in paths)
    has_python_sources = any(Path(p).suffix.lower() == ".py" for p in paths)
    has_api_integration = any("github" in p or "openai" in p for p in lower_paths) or any(
        dep.ecosystem in {"python", "node"}
        and any("openai" in item.lower() or "github" in item.lower() for item in dep.dependencies)
        for dep in dependencies
    )

    if not has_tests:
        risks.append("Test directory is missing or sparse; regression risk may be high.")
    if not any(".github/workflows" in p for p in lower_paths):
        risks.append("No CI workflow detected; code quality checks may be inconsistent.")
    if not any("dockerfile" in p for p in lower_paths):
        risks.append("No Dockerfile found; environment parity across machines may be weaker.")
    if has_python_sources and python_deps:
        has_unpinned_python_ranges = any(
            ">=" in item or "~=" in item or ">" in item
            for dep in python_deps
            for item in dep.dependencies
        )
        if has_unpinned_python_ranges:
            risks.append(
                "No strict Python dependency lock detected; requirements ranges can cause cross-environment version drift."
            )
    if has_env_files and not any(
        marker in p
        for p in lower_paths
        for marker in ("secrets", "vault", "sops", "doppler", "keyvault", "secret_manager")
    ):
        risks.append(
            "Secrets handling appears to rely on .env files; local/dev/prod secret management boundaries may be unclear."
        )
    if not any(
        marker in p
        for p in lower_paths
        for marker in ("dependabot", "pip-audit", "safety", "bandit", "semgrep", "trivy", "snyk")
    ):
        risks.append(
            "No explicit dependency/security scanning configuration detected; vulnerable packages may go unnoticed."
        )
    if any("memory_store.json" in p for p in lower_paths):
        risks.append(
            "JSON file-based memory store is suitable for prototyping but can become a scalability/concurrency bottleneck."
        )
    if has_api_integration and not any("retry" in p or "backoff" in p for p in lower_paths):
        risks.append(
            "API integration is present, but explicit retry/backoff patterns are not evident; rate-limit failures may impact large analyses."
        )
    if len(paths) > 2500:
        risks.append("Large repository size may hide architectural drift and ownership complexity.")
    if len(paths) >= 80:
        risks.append(
            "Analysis evidence is sample-based and may miss file-level nuances; per-file scoring/coverage depth is limited."
        )
    if not dependencies:
        risks.append("Dependency manifests were not parsed; stack governance visibility is limited.")

    if focus == "security":
        risks.append("No explicit security policy/config evidence found (e.g., SAST, secret scanning configs).")
    if focus == "scalability":
        risks.append("Limited direct evidence of performance/load strategy from static repository scan.")
    if focus == "maintainability":
        risks.append("Potential maintainability concern if module boundaries are not strongly enforced.")

    return risks[:12]
