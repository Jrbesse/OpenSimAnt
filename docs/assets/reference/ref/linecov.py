"""Minimal line coverage for a port module: python linecov.py <module_file.py> <test_script.py> [args...]

Prints the source lines of the module that never ran (ignoring blank lines, comments, docstrings and defs).
"""
import os
import runpy
import sys
import threading

target = os.path.abspath(sys.argv[1])
hit = set()


def tracer(frame, event, arg):
    if frame.f_code.co_filename != target:
        return None if event == 'call' else tracer
    if event == 'line':
        hit.add(frame.f_lineno)
    return tracer


sys.argv = sys.argv[2:]
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
sys.settrace(tracer)
threading.settrace(tracer)
try:
    runpy.run_path(sys.argv[0], run_name='__main__')
except SystemExit:
    pass
finally:
    sys.settrace(None)

src = open(target).read().splitlines()
in_doc = False
missed = []
for n, line in enumerate(src, 1):
    s = line.strip()
    if in_doc:
        if '"""' in s or "'''" in s:
            in_doc = False
        continue
    if s.startswith(('"""', "'''")):
        if s.count(s[:3]) == 1:
            in_doc = True
        continue
    if not s or s.startswith(('#', 'def ', 'class ', '@', 'from ', 'import ', 'else:', 'try:')):
        continue
    if n not in hit:
        missed.append((n, line))
print(f'\n{len(missed)} lines never ran in {os.path.basename(target)}:')
for n, line in missed:
    print(f'{n:5d}  {line}')
