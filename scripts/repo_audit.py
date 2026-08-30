from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TEXT_SUFFIXES = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".toml", ".csv"}
EXCLUDED = {".git", ".venv", "venv", "dist", "build", "__pycache__", ".pytest_cache"}
_WINDOWS_HOME = r"[A-Za-z]:\\" + "Users" + r"\\[^\\\\\s]+"
_MAC_HOME = "/" + "Users" + r"/[^/\s]+/"

PATTERNS = {
    "private-key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "github-token": re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    "aws-key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "personal-email": re.compile(r"\b[A-Za-z0-9._%+-]+@(?:gmail\.com|163\.com|qq\.com|outlook\.com)\b", re.I),
    "mainland-phone": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "personal-path": re.compile(f"(?:{_WINDOWS_HOME}|{_MAC_HOME})"),
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str


def scan(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED for part in relative.parts):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(lines, 1):
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(Finding(str(relative), number, name))
    return findings


def unpinned_actions(root: Path) -> list[str]:
    issues: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    for path in sorted(workflow_dir.glob("*.y*ml")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not stripped.startswith("uses:") and " uses:" not in line:
                continue
            value = stripped.split("uses:", 1)[1].strip().strip('"').strip("'")
            if value.startswith("./") or value.startswith("docker://"):
                continue
            if "@" not in value or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}", value):
                issues.append(f"{path.relative_to(root)}:{number}: {value}")
    return issues


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    findings = scan(root)
    pins = unpinned_actions(root)
    if findings or pins:
        for item in findings:
            print(f"{item.path}:{item.line}: {item.rule}")
        for item in pins:
            print(f"unpinned-action: {item}")
        return 1
    print("PASS: public-safety scan and action pinning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
