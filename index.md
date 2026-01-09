---
layout: default
title: Kamakoti Prakashanam
---

## Kamakoti

<div class="gallery">
{% assign kam = site.pages | where: "parent", "Kamakoti" | sort: "date" | reverse %}
{% for p in kam %}
  <a class="gallery-card" href="{{ p.url | relative_url }}">
    <div class="thumb">
      <img
        src="{{ p.url | append: 'cover.jpg' | relative_url }}"
        alt="{{ p.simple_title }}"
        onerror="this.style.display='none'">
    </div>
    <div class="caption">
      <div class="date">{{ p.date | date: "%d %b %Y" }}</div>
      <div class="title">{{ p.simple_title }}</div>
    </div>
  </a>
{% endfor %}
</div>

## VDSP Sabha

<div class="gallery">
{% assign v = site.pages | where: "parent", "VDSP" | sort: "date" | reverse %}
{% for p in v %}
  <a class="gallery-card" href="{{ p.url | relative_url }}">
    <div class="thumb">
      <img
        src="{{ p.url | append: 'cover.jpg' | relative_url }}"
        alt="{{ p.simple_title }}"
        onerror="this.style.display='none'">
    </div>
    <div class="caption">
      <div class="title">{{ p.simple_title }}</div>
      <div class="date">{{ p.date | date: "%d %b %Y" }}</div>
    </div>
  </a>
{% endfor %}
</div>
