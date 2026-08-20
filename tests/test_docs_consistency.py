"""Catch documentation drift the way we catch data drift: with a failing test.

Every stale reference found in this repository so far was found by someone
reading the docs and noticing — a `DESIGN.md §8` pointing at Faces, a skill still
carrying a versioning rule the guides had replaced, six CSVs describing deleted
files as archived, fourteen prototypes missing from their index. All of them were
mechanically checkable. None of them were mechanically checked.

An audit finds drift once. A test finds it every run, which is the difference
between a rule that holds and a rule someone has to remember.

These checks only cover claims a machine can verify: does the file exist, does the
section exist, is every prototype indexed. Rules needing judgment stay in the
owner documents.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ROOT_DOCS = ["AGENTS.md", "DEVELOPMENT.md", "DESIGN.md", "POSTING_WORKFLOW.md",
             "STRATEGY.md", "README.md"]
SKILLS = sorted((ROOT / ".agents/skills").rglob("SKILL.md"))

# Things named in backticks that look like repo files but are not.
EXTERNAL = {"Helvetica.ttc"}

FILE_REF = re.compile(r'`([A-Za-z0-9_./-]+\.(?:py|md|html|csv|sh|json|ttc|cfg|ini|txt))`')
SECTION_REF = re.compile(r'([A-Z_]+\.md)`?\s*§\s*(\d+)')


def _docs() -> list[Path]:
    return [ROOT / d for d in ROOT_DOCS] + SKILLS


def _numbered_sections(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text().splitlines():
        m = re.match(r'^#+\s*(\d+)\.\s*(.+)$', line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


@pytest.mark.parametrize("doc", _docs(), ids=lambda p: p.name if p.parent.name == p.parent.name else str(p))
def test_file_references_resolve(doc: Path):
    """A doc that points at a file which no longer exists answers nothing."""
    missing = []
    for i, line in enumerate(doc.read_text().splitlines(), 1):
        for m in FILE_REF.finditer(line):
            ref = m.group(1)
            if ref in EXTERNAL:
                continue
            direct = ROOT / ref
            if direct.exists():
                continue
            if "/" not in ref and any(
                p for p in ROOT.rglob(ref) if "venv" not in p.parts
            ):
                continue
            missing.append(f"{doc.relative_to(ROOT)}:{i} -> {ref}")
    assert not missing, "Documentation points at files that do not exist:\n  " + "\n  ".join(missing)


def test_section_cross_references_resolve():
    """`DESIGN.md §8` must name a section that is actually numbered 8.

    Renumbering a document silently invalidates every reference to it. This has
    already happened once: a reference to §8 survived after §8 became Voice &
    Caption, then survived again after Voice & Caption moved out.
    """
    targets = {d: _numbered_sections(ROOT / d) for d in ROOT_DOCS if (ROOT / d).exists()}
    sources = _docs() + sorted((ROOT / "scripts").rglob("*.py")) + sorted((ROOT / "bulls").rglob("*.py"))
    broken = []
    for src in sources:
        for i, line in enumerate(src.read_text(errors="ignore").splitlines(), 1):
            for m in SECTION_REF.finditer(line):
                doc, num = m.group(1), m.group(2)
                if doc in targets and num not in targets[doc]:
                    broken.append(f"{src.relative_to(ROOT)}:{i} -> {doc} §{num}")
    assert not broken, "Cross-references point at section numbers that do not exist:\n  " + "\n  ".join(broken)


def test_every_prototype_is_indexed():
    """`scripts/prototypes/README.md` is the only map of what has been built.

    The integration checklist says to update it, and the index still fell fourteen
    scripts behind, because a step you have to remember is a step that gets
    skipped when the post is finished and the branch is ready.
    """
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
