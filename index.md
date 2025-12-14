---
layout: default
title: Kamakoti Prakashanam
---

## Kamakoti

<ul>
{% assign kam = site.pages | where: "parent", "Kamakoti" | sort: "date" | reverse %}
{% for p in kam %}
  <li>
    <a href="prakashanam/{{ p.url }}">{{ p.simple_title }}</a>
    ({{ p.date | date: "%Y-%m-%d" }})
  </li>
{% endfor %}
</ul>

## VDSP Sabha

<ul>
{% assign v = site.pages | where: "parent", "VDSP" | sort: "date" | reverse %}
{% for p in v %}
  <li>
    <a href="prakashanam/{{ p.url }}">{{ p.simple_title }}</a>
    ({{ p.date | date: "%Y-%m-%d" }})
  </li>
{% endfor %}
</ul>
