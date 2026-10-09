"""Get the slides onto the user's phone: a Photos album, which iCloud Photos syncs, where Instagram picks images.

The album is "Bulls recaps", or photos_album in ~/.config/bulls-recap/notify.json; RECAP_ALBUM overrides it, so
test runs stay out of the real one. Delivery never fails a run: the slides are already in iCloud Drive, so
problems are logged and the run continues. (An iMessage with the slides was tried on 2026-10-08 and dropped: a
text to oneself never alerts, and the attachments would pile up in Messages; the alert is Claude's push.)

Instagram must never label a post as AI-made (user, 2026-10-08), so every slide must carry image data and
nothing else. clean_png() keeps only the header, pixel and end sections of each PNG and reports anything it
removed (text, EXIF, C2PA content credentials); after the Photos import the stored originals are exported
again and compared byte for byte, so Photos is shown not to have added anything either.
"""
import hashlib
import json
import os
import struct
import subprocess
import tempfile
from pathlib import Path

CONFIG = Path.home() / ".config" / "bulls-recap" / "notify.json"
IMAGE_ONLY = {b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND"}  # what a picture needs; anything else is metadata


def chunks(data: bytes):
    pos = 8
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        yield kind, data[pos:pos + 12 + length]
        pos += 12 + length


def clean_png(path: Path) -> list:
    """Remove every non-image section of a PNG in place; return the names of the sections removed."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path.name} is not a PNG")
    parts = list(chunks(data))
    extra = [kind.decode("latin-1") for kind, _ in parts if kind not in IMAGE_ONLY]
    if extra:
        path.write_bytes(data[:8] + b"".join(raw for kind, raw in parts if kind in IMAGE_ONLY))
    return extra


def osascript(script: str, *args: str) -> str:
    done = subprocess.run(["osascript", "-e", script, *args], capture_output=True, text=True, timeout=300)
    if done.returncode:
        raise RuntimeError(done.stderr.strip() or f"osascript exit {done.returncode}")
    return done.stdout.strip()


PHOTOS = """
on run argv
  set albumName to item 1 of argv
  set outFolder to item 2 of argv
  set theFiles to {}
  repeat with p in items 3 thru -1 of argv
    set end of theFiles to (POSIX file (p as text)) as alias
  end repeat
  tell application "Photos"
    if not (exists album albumName) then make new album named albumName
    set imported to import theFiles into album albumName skip check duplicates true
    export imported to (POSIX file outFolder as alias) with using originals
    return (count of imported) as text
  end tell
end run
"""

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def to_photos(slides: list, album: str) -> str:
    with tempfile.TemporaryDirectory() as back:
        count = osascript(PHOTOS, album, back, *map(str, slides))
        stored = {p.name: digest(p) for p in Path(back).iterdir()}
    changed = [s.name for s in slides if stored.get(s.name) != digest(s)]
    if changed:
        return f"{count} slides added to Photos album \"{album}\", but Photos changed {', '.join(changed)}: check before posting"
    return f"{count} slides added to Photos album \"{album}\"; the stored originals match the exported slides exactly"


def deliver(slides: list) -> list:
    """Clean every slide and add them to the Photos album. Returns one log line per step."""
    lines = []
    for s in slides:
        removed = clean_png(s)
        if removed:
            lines.append(f"metadata removed from {s.name}: {', '.join(removed)}")
    lines.append(f"slides hold image data only ({len(slides)} checked)")
    config = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    album = os.environ.get("RECAP_ALBUM", config.get("photos_album", "Bulls recaps"))
    try:
        lines.append(to_photos(slides, album))
    except Exception as e:  # never fail the run: the slides are already in iCloud Drive
        lines.append(f"Photos failed: {type(e).__name__}: {e}")
    return lines
