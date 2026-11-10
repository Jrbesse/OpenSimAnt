---
layout: default
title: OpenSimAnt
---

# OpenSimAnt

**A faithful, 1:1 remake of *SimAnt* (Maxis, 1991) — rebuilt in Godot 4 and C# from a reverse-engineered understanding of the DOS executable, and verified against the original running in an emulator.**

OpenSimAnt is not a homage, a reimagining, or "inspired by". The simulation is a port of the original's
machine code: the same routines, called in the same order, reading and writing a memory layout that is
deliberately identical to the 1991 program's. The yard generator, the nest AI, the spider, the lawnmower,
the pheromone decay — each is checked byte for byte against the original's own state.

Two things make that possible, and both live in this repository:

- **The oracle.** A Unicorn-based emulator boots the player's own `SIMANT.EXE`, plays a seeded Quick Game, and
  caches snapshots of memory. Any ported routine can be run against those snapshots and its output compared
  with the original routine's, 150,160 bytes at a time.
- **The Python reference.** `tools/ref/simant_ref` is a readable, line-by-line translation of the whole
  simulation — the specification the C# remake is ported from. It is published here in full, with the decoded
  rules beside it, so anyone can read it, run it, or build their own version.

---

## The dev log

These entries are the technical counterpart to the release notes: what changed, how it works, what broke,
and what it cost. First person, no marketing.

<ul>
{% for post in site.posts %}
  <li>
    <strong><a href="{{ post.url | relative_url }}">{{ post.title }}</a></strong><br>
    <small>{{ post.date | date: "%B %-d, %Y" }}</small>
  </li>
{% endfor %}
</ul>

---

## The reference implementation

The Python port is the most useful artifact in this project for anyone who wants to understand — or rebuild —
the original game. Every module is documented on its own page, with what it ports, which routine it came from,
and its full source, downloadable as a `.py` file:

- **[Reference index]({{ site.baseurl }}/reference/)** — all 26 modules, grouped by the part of the game they own.
- **[Reverse-engineering toolchain]({{ site.baseurl }}/reference/#reverse-engineering-toolchain)** — the disassembler,
  the flat memory image builder, the emulator, the screen comparators.

You will need your own copy of *SimAnt* to use the reference for real: the constant tables and the starting state
are read from `SIMANT.EXE` at runtime and are not committed here. Nothing extracted from the original is
distributed; every byte of it comes from the machine you run the tools on.

---

## Status

The simulation matches the original in the emulator, every screen and sound is built, and the clean-room asset
pack is complete — 810 files, so the game runs with no original files at all. What remains is the release work:
the licences and the public decision, the last similarity review, and the play-testing only a person can do.

The tech: **C# / .NET 8** for the simulation and data layers, **Godot 4.6** for the shell, **Python** for the
reference and the tooling.
