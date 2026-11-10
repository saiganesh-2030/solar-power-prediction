"""Tests to enforce the strict vocabulary policy across the codebase.

References:
- docs/PROJECT_HANDBOOK.md section 8
- AGENTS.md section 4 (Non-negotiable 3)
- docs/roles/ROLE_4_PLATFORM_INTEGRATION.md section 5
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Strictly banned terms in user-facing text, API fields, and domain logic
BANNED_REGEX = re.compile(
    r"\b(fault|faults|faulty|defective|malfunction|malfunctioning)\b",
    re.IGNORECASE,
)

TARGET_DIRS = [
    REPO_ROOT / "backend" / "app",
    REPO_ROOT / "frontend" / "src",
    REPO_ROOT / "frontend" / "public" / "mock",
    REPO_ROOT / "ml",
]

def test_no_banned_vocabulary():
    violations = []
    
    for base_dir in TARGET_DIRS:
        if not base_dir.exists():
            continue
        for file_path in base_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in [".py", ".js", ".json", ".html", ".css"]:
                continue
                
            try:
                content = file_path.read_text(encoding="utf-8")
                for line_no, line in enumerate(content.splitlines(), start=1):
                    # Check for banned words
                    match = BANNED_REGEX.search(line)
                    if match:
                        violations.append(
                            f"{file_path.relative_to(REPO_ROOT)}:{line_no} "
                            f"Contains banned word: '{match.group()}' -> line: {line.strip()}"
                        )
            except Exception:
                pass

    if violations:
        msg = "Banned vocabulary violations found:\n" + "\n".join(violations)
        raise AssertionError(msg)
    print("✓ Banned vocabulary test passed: zero violations found.")

if __name__ == "__main__":
    test_no_banned_vocabulary()

