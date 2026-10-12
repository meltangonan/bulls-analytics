"""Check or remove metadata in exported PNG pages, then send them to iCloud Photos.

Canva tags every page of a design as AI-generated once any AI feature touched it,
including pages that are only our charts and text. ``--check`` reports the tags.
``--photos`` writes each page to a temporary folder with only the chunks needed to
draw the image (asserting the pixel data is byte-identical), imports the clean copies
into Apple Photos, which syncs them to iCloud, and deletes the temporary folder.

Name the files in carousel order: Photos can't sort them by date once metadata is gone.

Export pages from Canva at 2x (2160 px wide). Canva's own 1080 export blurs small text (edge
variance less than half that of a clean resize, measured 2026-10-12), so ``--photos`` halves a
2x page with Lanczos before cleaning it, and warns about a page exported at 1080.

    venv/bin/python scripts/strip_image_metadata.py --check page1.png page2.png
    venv/bin/python scripts/strip_image_metadata.py --photos <slug>-1.png <slug>-2.png
"""

import argparse
import io
import re
import struct
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
# Chunks that affect how the image looks; everything else is metadata.
FEED_WIDTH = 1080
RENDER_CHUNKS = {b'IHDR', b'PLTE', b'IDAT', b'IEND', b'tRNS', b'sRGB', b'gAMA', b'iCCP', b'cHRM', b'pHYs'}
AI_MARKERS = re.compile(rb'c2pa|TrainedAlgorithmicMedia|ContainsAiGeneratedContent', re.I)


def chunks(data):
    assert data[:8] == PNG_SIGNATURE, 'not a PNG file'
    i = 8
    while i < len(data):
        (length,) = struct.unpack('>I', data[i:i + 4])
        yield data[i + 4:i + 8], data[i:i + 12 + length]
        i += 12 + length


def ai_tags(data):
    return sorted({m.decode().lower() for m in AI_MARKERS.findall(data)})


def clean_png(data, name):
    clean = PNG_SIGNATURE + b''.join(c for t, c in chunks(data) if t in RENDER_CHUNKS)
    pixels = lambda d: b''.join(c for t, c in chunks(d) if t == b'IDAT')
    assert pixels(clean) == pixels(data), f'{name}: pixel data changed'
    assert not ai_tags(clean), f'{name}: AI tags remain'
    return clean


def feed_size(data, name):
    """Halve a 2x page to the feed width with Lanczos; warn about a 1x Canva export."""
    image = Image.open(io.BytesIO(data))
    if image.width == FEED_WIDTH:
        print(f'{name}: warning, 1080 px export; Canva blurs text at this size, so export at 2x')
        return data
    assert image.size == (2 * FEED_WIDTH, image.height) and image.height % 2 == 0, (
        f'{name}: expected a 2x page {2 * FEED_WIDTH} px wide, got {image.width}x{image.height}')
    out = io.BytesIO()
    image.convert('RGB').resize((FEED_WIDTH, image.height // 2), Image.LANCZOS).save(out, 'PNG')
    print(f'{name}: halved {image.width}x{image.height} to {FEED_WIDTH}x{image.height // 2}')
    return out.getvalue()


def import_to_photos(paths):
    files = ', '.join(f'POSIX file "{p}"' for p in paths)
    script = f'tell application "Photos" to import {{{files}}} skip check duplicates true'
    subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
    print(f'imported {len(paths)} files into Photos')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('files', nargs='+', type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true', help='report tags without writing')
    mode.add_argument('--photos', action='store_true', help='clean and import into Apple Photos')
    args = parser.parse_args()

    if args.check:
        for path in args.files:
            tags = ai_tags(path.read_bytes())
            print(f'{path.name}: {"AI tags: " + ", ".join(tags) if tags else "no AI tags"}')
        return

    with tempfile.TemporaryDirectory() as tmp:
        written = []
        for path in args.files:
            original = path.read_bytes()
            data = feed_size(original, path.name)
            dest = Path(tmp) / path.name
            dest.write_bytes(clean_png(data, path.name))
            written.append(dest)
            dropped = sorted({t.decode() for t, _ in chunks(original) if t not in RENDER_CHUNKS})
            print(f'{path.name}: removed {", ".join(dropped) or "nothing"}; pixels identical')
        import_to_photos(written)


if __name__ == '__main__':
    main()
