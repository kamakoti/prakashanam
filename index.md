---
layout: default
title: Kamakoti Prakashanam
---

{% assign upcoming = site.pages | where_exp: "p", "p.date and p.date > site.time" | sort: "date" %}

{% if upcoming.size > 0 %}
## Upcoming

<div class="gallery upcoming">
{% for p in upcoming %}
  <a class="gallery-card upcoming" href="{{ p.url | relative_url }}">
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
{% endif %}

{% assign kamakoti = site.pages | where: "parent", "Kamakoti" %}
{% assign vdsp = site.pages | where: "parent", "VDSP" %}
{% assign published = kamakoti | concat: vdsp | where_exp: "p", "p.date == nil or p.date <= site.time" | sort: "date" | reverse %}

## Past Publications

<div class="gallery">
{% for p in published %}
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
