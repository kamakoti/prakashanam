---
layout: default
title: Kamakoti Prakashanam
---

{% assign now_ts = site.time | date: "%s" | plus: 0 %}

{% comment %} 1. Filter pages separately and concat (safer than where_exp) {% endcomment %}
{% assign kam_pages = site.pages | where: "parent", "Kamakoti" %}
{% assign vdsp_pages = site.pages | where: "parent", "VDSP" %}
{% assign all_pages = kam_pages | concat: vdsp_pages %}

{% comment %} 2. Split into Upcoming and Published arrays {% endcomment %}
{% assign upcoming_list = "" | split: "" %}
{% assign published_list = "" | split: "" %}

{% for p in all_pages %}
  {% if p.date %}
    {% assign p_ts = p.date | date: "%s" | plus: 0 %}
    {% if p_ts >= now_ts %}
      {% assign upcoming_list = upcoming_list | push: p %}
    {% else %}
      {% assign published_list = published_list | push: p %}
    {% endif %}
  {% endif %}
{% endfor %}

{% comment %} 3. Sort arrays {% endcomment %}
{% assign upcoming_sorted = upcoming_list | sort: "date" %}
{% assign published_sorted = published_list | sort: "date" | reverse %}


{% if upcoming_sorted.size > 0 %}
## Upcoming

<div class="gallery">
{% for p in upcoming_sorted %}
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
{% endif %}


## Past

<div class="gallery">
{% for p in published_sorted %}
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
