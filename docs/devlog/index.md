---
layout: default
title: Dev log
permalink: /devlog/
---

# Dev log

The engineering record: what is being built, how it is verified, and the bugs that a byte-exact comparison
finds that nothing else would.

<ul>
{% for post in site.posts %}
  <li>
    <strong><a href="{{ post.url | relative_url }}">{{ post.title }}</a></strong><br>
    <small>{{ post.date | date: "%B %-d, %Y" }}</small>
    <p>{{ post.excerpt | strip_html | normalize_whitespace | truncate: 320 }}</p>
  </li>
{% endfor %}
</ul>

---

Release notes, which are the player-facing version of the same weeks, are in the repository's
`docs/RELEASE_NOTES_TEMPLATE.md`. The decoded rules — every address, every table, every behaviour the
simulation is built from — live in `docs/SIM_NOTES.md`, which stays in the repository rather than on this
site: it is a working document, not a publication.
