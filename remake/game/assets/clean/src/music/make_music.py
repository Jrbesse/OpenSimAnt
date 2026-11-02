"""Writes all 30 songs: runs the two batches' scripts (each writes its own .mid files into this folder)."""
import os, runpy

HERE = os.path.dirname(os.path.abspath(__file__))
for name in ('make_music_a.py', 'make_music_b.py'):
    runpy.run_path(os.path.join(HERE, name), run_name='__main__')
