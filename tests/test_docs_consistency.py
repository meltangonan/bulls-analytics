"""Check file references, prototype indexing, and canonical skill links."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ROOT_DOCS = ["AGENTS.md", "DEVELOPMENT.md", "DESIGN.md", "POSTING_WORKFLOW.md",
             "STRATEGY.md", "README.md"]
SKILLS = sorted((ROOT / ".agents/skills").rglob("SKILL.md"))

# Search relevant source/docs once, excluding ignored caches and environments.
SOURCE_BASENAMES = {p.name for directory in ("bulls", "scripts", "tests", "docs")
                    for p in (ROOT / directory).rglob("*") if p.is_file()}

# Things named in backticks that look like repo files but are not.
EXTERNAL = {"Helvetica.ttc"}

FILE_REF = re.compile(r'`([A-Za-z0-9_./-]+\.(?:py|md|html|csv|sh|json|ttc|cfg|ini|txt))`')


def _docs() -> list[Path]:
    return [ROOT / d for d in ROOT_DOCS] + sorted((ROOT / "docs/reference").glob("*.md")) + sorted((ROOT / "docs/design").glob("*.md")) + SKILLS


@pytest.mark.parametrize("doc", _docs(), ids=lambda p: str(p.relative_to(ROOT)))
def test_file_references_resolve(doc: Path):
    """A doc that points at a file which no longer exists answers nothing."""
    missing = []
    for i, line in enumerate(doc.read_text().splitlines(), 1):
        refs = [m.group(1) for m in FILE_REF.finditer(line)]
        refs += re.findall(r"\]\(([^)]+)\)", line)
        for ref in refs:
            if "://" in ref or ref.startswith("#"):
                continue
            ref = ref.split("#", 1)[0]
            if (doc.parent / ref).exists():
                continue
            if ref in EXTERNAL:
                continue
            direct = ROOT / ref
            if direct.exists():
                continue
            if "/" not in ref and ref in SOURCE_BASENAMES:
                continue
            missing.append(f"{doc.relative_to(ROOT)}:{i} -> {ref}")
    assert not missing, "Documentation points at files that do not exist:\n  " + "\n  ".join(missing)


def test_every_prototype_is_indexed():
    """Every entry point should be discoverable without reading all scripts."""
    index = (ROOT / "scripts/prototypes/README.md").read_text()
    scripts = sorted(p.stem for p in (ROOT / "scripts/prototypes").glob("*.py")
                     if not p.name.startswith("_"))
    missing = [s for s in scripts if f"{s}.py" not in index]
    assert not missing, (
        f"{len(missing)} prototype(s) missing from scripts/prototypes/README.md:\n  "
        + "\n  ".join(missing)
        + "\n\nAdd a row describing what the script builds and what it qualifies on."
    )


def test_indexed_prototypes_still_exist():
    """The reverse: an index row for a deleted script sends a reader nowhere."""
    index = (ROOT / "scripts/prototypes/README.md").read_text()
    listed = set(re.findall(r'`([a-z0-9_]+)\.py`', index))
    on_disk = {p.stem for p in (ROOT / "scripts/prototypes").glob("*.py")}
    elsewhere = {p.stem for p in (ROOT / "scripts").glob("*.py")}
    ghosts = sorted(listed - on_disk - elsewhere)
    assert not ghosts, "Index rows for scripts that no longer exist:\n  " + "\n  ".join(ghosts)


def test_skill_symlinks_are_links_not_copies():
    """AGENTS.md requires `.claude/skills/` to symlink `.agents/skills/`.

    A copy drifts silently: an agent reading one path gets a rule that another
    path has already replaced.
    """
    problems = []
    for canonical in SKILLS:
        mirror = ROOT / ".claude/skills" / canonical.parent.name / "SKILL.md"
        if not mirror.exists():
            problems.append(f"{mirror.relative_to(ROOT)} missing")
        elif not mirror.is_symlink():
            problems.append(f"{mirror.relative_to(ROOT)} is a copy, not a symlink")
        elif mirror.resolve() != canonical.resolve():
            problems.append(f"{mirror.relative_to(ROOT)} points at {mirror.resolve()}")
    assert not problems, "Skill mirror is out of sync:\n  " + "\n  ".join(problems)


def test_prototypes_have_a_module_docstring():
    """The docstring is what a future reader reads first; an unnamed script is a dead end."""
    bare = []
    for p in sorted((ROOT / "scripts/prototypes").glob("*.py")):
        if p.name.startswith("_"):
            continue
        if not ast.get_docstring(ast.parse(p.read_text(errors="ignore"))):
            bare.append(p.name)
    assert not bare, "Prototypes with no module docstring:\n  " + "\n  ".join(bare)
