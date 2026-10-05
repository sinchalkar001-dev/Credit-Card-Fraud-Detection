"""Draw the guilloche line-work used across the interface.

Guilloche is the woven engraving on banknotes and cheques: several copies of
one wavy ring, each shifted in phase so they braid through each other. Every
ring here is r(t) = R + A * sin(N * t + phase), written out as cubic Bezier
segments whose handles follow the curve's true tangent, so it stays smooth at
any size.

Run it again after changing the numbers below:

    python tools/guilloche.py

It rewrites three generated files:

    app/templates/partials/guilloche.html   the rosette and the brand mark, as Jinja macros
    app/static/img/guilloche-band.svg       one tile of the woven rule (used as a CSS mask)
    app/static/img/favicon.svg              the brand mark as a favicon
"""

import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTIAL = os.path.join(ROOT, 'app', 'templates', 'partials', 'guilloche.html')
BAND = os.path.join(ROOT, 'app', 'static', 'img', 'guilloche-band.svg')
FAVICON = os.path.join(ROOT, 'app', 'static', 'img', 'favicon.svg')

# name: (radius, amplitude, lobes, copies)
ROSETTE = {
    'outer': (206, 30, 16, 6),
    'middle': (132, 22, 10, 6),
    'inner': (70, 15, 6, 4),
}

SEGMENTS_PER_LOBE = 4

# Brand colours for the favicon, which cannot read the page's CSS variables.
FAVICON_LIGHT = '#2055be'  # --blue-600
FAVICON_DARK = '#91b7fe'   # --blue-300


def trim(text):
    """Drop trailing zeros and the sign of a rounded-away zero."""
    text = text.rstrip('0').rstrip('.') if '.' in text else text
    return '0' if text in ('-0', '') else text


def number(value):
    return trim(f'{value:.1f}')


def ring(radius, amplitude, lobes, phase, precision=number):
    def point(t):
        r = radius + amplitude * math.sin(lobes * t + phase)
        return r * math.cos(t), r * math.sin(t)

    def tangent(t):
        r = radius + amplitude * math.sin(lobes * t + phase)
        dr = amplitude * lobes * math.cos(lobes * t + phase)
        return dr * math.cos(t) - r * math.sin(t), dr * math.sin(t) + r * math.cos(t)

    def pair(x, y):
        return f'{precision(x)} {precision(y)}'

    segments = lobes * SEGMENTS_PER_LOBE
    step = 2 * math.pi / segments
    path = ['M' + pair(*point(0))]
    for i in range(segments):
        t0, t1 = i * step, (i + 1) * step
        (x0, y0), (x1, y1) = point(t0), point(t1)
        (dx0, dy0), (dx1, dy1) = tangent(t0), tangent(t1)
        path.append('C' + ' '.join((
            pair(x0 + dx0 * step / 3, y0 + dy0 * step / 3),
            pair(x1 - dx1 * step / 3, y1 - dy1 * step / 3),
            pair(x1, y1))))
    return ''.join(path) + 'Z'


def band(radius, amplitude, lobes, copies):
    return [ring(radius, amplitude, lobes, 2 * math.pi * k / copies) for k in range(copies)]


def rosette_macro():
    groups = []
    for name, spec in ROSETTE.items():
        paths = '\n'.join(
            f'    <path class="guilloche__line" style="--i:{i}" pathLength="1" d="{d}"/>'
            for i, d in enumerate(band(*spec)))
        groups.append(
            f'  <g id="guilloche-{name}" class="guilloche__band guilloche__band--{name}">\n{paths}\n  </g>')
    body = '\n'.join(groups)
    return (
        "{% macro rosette(class='', draw=false) -%}\n"
        '<svg class="guilloche {{ class }}" viewBox="-250 -250 500 500" fill="none" '
        'stroke-linejoin="round" aria-hidden="true" focusable="false"'
        '{% if draw %} data-draw{% endif %}>\n'
        f'{body}\n'
        '</svg>\n'
        '{%- endmacro %}\n')


def mark_paths():
    """Two rings in opposite phase: a small seal."""
    return [ring(8.6, 1.9, 8, phase, lambda value: trim(f'{value:.2f}')) for phase in (0, math.pi)]


def mark_macro():
    paths = ''.join(f'<path d="{d}"/>' for d in mark_paths())
    return (
        "{% macro brand_mark(class='') -%}\n"
        '<svg class="{{ class }}" viewBox="-12 -12 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.35" stroke-linejoin="round" aria-hidden="true" focusable="false">'
        f'{paths}<circle r="2.7" fill="currentColor" stroke="none"/></svg>\n'
        '{%- endmacro %}\n')


def band_tile(width=96, height=24, copies=6, amplitude=9):
    paths = []
    for k in range(copies):
        phase = 2 * math.pi * k / copies
        points = [
            f'{x} {number(height / 2 + amplitude * math.sin(2 * math.pi * x / width + phase))}'
            for x in range(0, width + 1, 2)]
        paths.append(f'<path d="M{"L".join(points)}"/>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}"><g fill="none" stroke="#000" stroke-width="0.7">'
        f'{"".join(paths)}</g></svg>\n')


def favicon():
    paths = ''.join(f'<path d="{d}"/>' for d in mark_paths())
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-12 -12 24 24">'
        f'<style>g{{stroke:{FAVICON_LIGHT};fill:{FAVICON_LIGHT}}}'
        f'@media (prefers-color-scheme:dark){{g{{stroke:{FAVICON_DARK};fill:{FAVICON_DARK}}}}}</style>'
        f'<g stroke-width="1.5" stroke-linejoin="round"><g fill="none">{paths}</g>'
        '<circle r="2.7" stroke="none"/></g></svg>\n')


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print(f'{os.path.relpath(path, ROOT)}  {len(content):,} bytes')


def main():
    header = '{# Generated by tools/guilloche.py. Edit the script, not this file. #}\n'
    write(PARTIAL, header + rosette_macro() + '\n' + mark_macro())
    write(BAND, band_tile())
    write(FAVICON, favicon())


if __name__ == '__main__':
    main()
