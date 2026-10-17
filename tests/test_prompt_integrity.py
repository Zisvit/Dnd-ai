#!/usr/bin/env python3
"""Манифест целостности промптов: соответствие и детекция расхождений."""

import json

import dndai.core.config.prompt_integrity as integrity


def test_manifest_matches_package_prompts():
    """Манифест в репозитории должен совпадать с фактическими *.txt."""
    problems = integrity.verify_prompts()
    assert problems == [], problems


def test_verify_ok_on_generated_manifest(tmp_path):
    (tmp_path / "a.txt").write_text("оригинал", encoding="utf-8")
    integrity.write_manifest(tmp_path)
    assert integrity.verify_prompts(tmp_path) == []


def test_verify_detects_tampered_file(tmp_path):
    (tmp_path / "a.txt").write_text("оригинал", encoding="utf-8")
    integrity.write_manifest(tmp_path)
    (tmp_path / "a.txt").write_text("подмена", encoding="utf-8")
    problems = integrity.verify_prompts(tmp_path)
    assert any("sha256" in p and "a.txt" in p for p in problems)


def test_verify_reports_missing_and_extra(tmp_path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "checksums.json").write_text(
        json.dumps({"algorithm": "sha256", "files": {"ghost.txt": "0" * 64}}),
        encoding="utf-8",
    )
    problems = integrity.verify_prompts(tmp_path)
    assert any("ghost.txt" in p for p in problems)  # манифест знает, файла нет
    assert any("нет в манифесте" in p for p in problems)  # a.txt


def test_verify_manifest_missing(tmp_path):
    problems = integrity.verify_prompts(tmp_path)
    assert len(problems) == 1
    assert "манифест" in problems[0]
