from __future__ import annotations

import pytest

from src.utils.helpers import parse_github_input


def test_parse_github_input_from_owner_repo() -> None:
    owner, repo, branch = parse_github_input("langchain-ai/langchain")
    assert owner == "langchain-ai"
    assert repo == "langchain"
    assert branch is None


def test_parse_github_input_from_url() -> None:
    owner, repo, branch = parse_github_input("https://github.com/streamlit/streamlit")
    assert owner == "streamlit"
    assert repo == "streamlit"
    assert branch is None


def test_parse_github_input_from_owner_repo_with_branch() -> None:
    owner, repo, branch = parse_github_input("langchain-ai/langchain@feature/demo")
    assert owner == "langchain-ai"
    assert repo == "langchain"
    assert branch == "feature/demo"


def test_parse_github_input_from_tree_url_with_branch() -> None:
    owner, repo, branch = parse_github_input("https://github.com/streamlit/streamlit/tree/feature/demo")
    assert owner == "streamlit"
    assert repo == "streamlit"
    assert branch == "feature/demo"


def test_parse_github_input_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        parse_github_input("not-a-valid-repo")
