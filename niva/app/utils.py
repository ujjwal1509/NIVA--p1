# app/utils.py
from typing import Dict, Any

RED_FLAGS = [
    "chest pain",
    "difficulty breathing",
    "unconscious",
    "severe bleeding",
    "sudden weakness",
]


def detect_red_flags(report: Dict[str, Any]) -> bool:
    symptoms = report.get("symptoms", [])
    for s in symptoms:
        name = s.get("name", "").lower()
        for rf in RED_FLAGS:
            if rf in name:
                return True
    for ev in report.get("evidence_snippets", []):
        ans = ev.get("answer", "").lower() if isinstance(ev, dict) else ""
        for rf in RED_FLAGS:
            if rf in ans:
                return True
    return False
