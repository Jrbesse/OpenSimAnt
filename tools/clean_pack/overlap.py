"""overlap.py: the similarity check for text. Lists every run of N words (default 6) that a file shares with the
original's text resources (string lists, type 4; long texts, type 10) in a pack made from the player's files.

    python tools/clean_pack/overlap.py <file or folder> [...] [--pack=remake/build/original_pack.zip] [--n=6]

Words are lower-case letters and apostrophes; everything else separates them. Run it on specs (docs/clean_pack/*.md)
and on the makers' text (remake/game/assets/clean/src/strings, src/texts, src/menus). Exit status 1 if any run is
shared. The pack is local only (OpenSimAnt.Replay --export-pack); this script prints the shared runs, which are
short, to the terminal only.
"""
import os
import re
import sys
import zipfile

WORD = re.compile(r"[a-z']+")


def words(text):
    return WORD.findall(text.lower())


def original_runs(pack, n):
    runs = {}
    with zipfile.ZipFile(pack) as z:
        for name in z.namelist():
            parts = name.split('/')
            if len(parts) == 3 and parts[1] in ('4', '10'):
                ws = words(z.read(name).decode('latin-1'))
                for i in range(len(ws) - n + 1):
                    runs.setdefault(' '.join(ws[i:i + n]), name)
    return runs


def files_of(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                for f in sorted(names):
                    if f.endswith(('.md', '.json', '.txt')):
                        yield os.path.join(root, f)
        else:
            yield p


def main(argv):
    pack, n, paths = 'remake/build/original_pack.zip', 6, []
    for a in argv:
        if a.startswith('--pack='):
            pack = a[7:]
        elif a.startswith('--n='):
            n = int(a[4:])
        else:
            paths.append(a)
    if not paths:
        print(__doc__)
        return 2
    runs = original_runs(pack, n)
    total = 0
    for f in files_of(paths):
        with open(f, encoding='utf-8', errors='replace') as fh:
            ws = words(fh.read())
        hits = sorted({' '.join(ws[i:i + n]) for i in range(len(ws) - n + 1)} & runs.keys())
        for h in hits:
            print('%s: "%s" (as in %s)' % (f, h, runs[h]))
        total += len(hits)
    print('%d shared runs of %d words' % (total, n))
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
