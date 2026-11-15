"""The fixed file-dialog listing both sides of the comparison see (#54).

The reference capture (screens.py, the original served the folder as C:\\ via emu.find_dir) and the
remake's render (compare_screens.py, --file-dir) must list the same files, or the diff measures the
machine's directory, not the renderer. This module owns the fixture's names and the sidecar that
records them beside the capture: screens.py builds the folder from FIXTURE and writes <name>.files
after the capture, and compare_screens.py rebuilds a fresh directory from the sidecar (or from FIXTURE
for a capture set recorded before the sidecar existed) for the --file-dir render, so the pair is
comparable on any machine.
"""
import os
import shutil

# three empty saved games, a text file the dialog leaves out, a sub-folder
FIXTURE = ('GAME1.ANT', 'MYCOLONY.ANT', 'README.TXT', 'SAVES/', 'ZEBRA.ANT')


def _add(d, entry):
    os.makedirs(os.path.join(d, entry)) if entry.endswith('/') else open(os.path.join(d, entry), 'wb').close()


def make_fixture(path):
    """(Re)build the fixture directory at path with exactly FIXTURE's entries."""
    os.makedirs(path, exist_ok=True)
    for n in os.listdir(path):
        p = os.path.join(path, n)
        (shutil.rmtree if os.path.isdir(p) else os.remove)(p)   # rmtree: a non-empty stray dir must not break the rebuild
    for e in FIXTURE:
        _add(path, e)


def served(d):
    """What a dialog listing folder d sees: the entries as named, directories '/'-suffixed, sorted.

    The sidecar records this, not FIXTURE: the dialog lists the folder it was served, so the sidecar
    is the observation beside the capture, not a restatement of the fixture's intent."""
    return [n + ('/' if os.path.isdir(os.path.join(d, n)) else '') for n in sorted(os.listdir(d))]


def write_sidecar(out_dir, name, entries):
    """Record the names the capture listed, one per line, in <name>.files beside it."""
    with open(os.path.join(out_dir, name + '.files'), 'w') as f:
        f.write('\n'.join(entries) + '\n')


def build_for_render(out_dir, name):
    """A fresh directory the remake's --file-dir can list: the capture's recorded names if its
    <name>.files sidecar exists, else the canonical fixture. The caller deletes it when done."""
    import tempfile
    p = os.path.join(out_dir, name + '.files')
    entries = open(p).read().split() if os.path.exists(p) else list(FIXTURE)
    d = tempfile.mkdtemp(prefix=name + '-fixture-')
    for e in entries:
        _add(d, e)
    return d
