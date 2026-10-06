#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Breadboard layout for Irin, the 12V battery monitor (400-point half-size board: 30 columns, rows a-j, two rails each side).

Placements are hand-chosen; module pin positions come from the project's
footprints (Irin.pretty) rotated onto the 0.1" grid. The layout is
validated against the KiCad netlist before anything is drawn: every net must
be exactly one connected group, no two nets may short, and unused module pins
must sit in otherwise-empty strips.

    python3 make_breadboard.py            # validate + write breadboard.html
"""
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NETLIST = HERE.parent / 'irin.net'
OUT = HERE / 'breadboard.html'

NCOLS = 30
TOP_ROWS, BOT_ROWS = 'abcde', 'fghij'
# Rail assignment
RAILS = {'T+': '12V PROT', 'T-': 'GND', 'B+': '3V3', 'B-': 'GND'}

# ---------------------------------------------------------------- placement
# hole = (row, col) with row in a-j or a rail name.
parts = {}      # ref -> dict(kind, pins={pin: hole}, label, ...)


def module(ref, label, pins, body, color):
    """pins: {pin: (row, col, name)}; body: (col0, row0, col1, row1) in grid units."""
    parts[ref] = dict(kind='module', label=label, body=body, color=color,
                      pins={p: (r, c) for p, (r, c, _) in pins.items()},
                      names={p: n for p, (r, c, n) in pins.items()})


def two_lead(ref, label, a, b, color, polar=None):
    parts[ref] = dict(kind='lead', label=label, color=color, polar=polar,
                      pins={'1': a, '2': b})


# Off-board: bench supply (later the battery) through the inline fuse holder.
parts['J1'] = dict(kind='off', pins={'2': ('T-', 1)})
parts['F1'] = dict(kind='off', pins={'2': ('T+', 1)})

# MP1584 (HW-133) straddling the channel, input edge up, right of the ESP32.
# Footprint: IN- x=-5.08,-2.54 / IN+ x=+2.54,+5.08 at y=-8.89; OUT same x at y=+8.89.
module('U1', 'U1 MP1584', {
    '2': ('c', 11, 'IN−'), '2b': ('c', 12, 'IN−'),
    '1': ('c', 14, 'IN+'), '1b': ('c', 15, 'IN+'),
    '4': ('h', 11, 'OUT−'), '4b': ('h', 12, 'OUT−'),
    '3': ('h', 14, 'OUT+'), '3b': ('h', 15, 'OUT+'),
}, body=(10.0, 'c-', 16.0, 'h+'), color='#1d4ed8')

# Input protection / bulk, straight across the top rail pair.
two_lead('D1', 'D1 P6KE18A (opt.)', ('T+', 5), ('T-', 5), '#555', polar='K at T+ (band)')
two_lead('C3', 'C3 0.1uF', ('T+', 8), ('T-', 8), '#d97706')
two_lead('C2', 'C2 100uF/35V', ('T+', 13), ('T-', 13), '#2563eb', polar='+ at T+')

# ESP32-C3-0.42LCD straddling the channel at the left end, power pins
# bottom-left so the USB-C end (assumed to be the 5V/GND/3V3 end) hangs off
# the left edge of the breadboard for flashing. GPIO side faces up.
# Footprint left column (x=0), y=0..17.78: 4(GPIO3) 7 5(GPIO5) 6(GPIO6) 8 9 10 11
# right column (x=17.78):                12 13 14 15 16 2(3V3) 3(GND) 1(5V)
# Rotation (x,y) -> (col = c0 + 7 - y/2.54, row = top if x==0 else bottom)
C0 = 1
left = ['4', '7', '5', '6', '8', '9', '10', '11']
right = ['12', '13', '14', '15', '16', '2', '3', '1']
names = {'4': 'GPIO3', '5': 'GPIO5', '6': 'GPIO6', '1': '5V', '2': '3V3', '3': 'GND'}
esp = {}
for k, p in enumerate(left):
    esp[p] = ('c', C0 + 7 - k, names.get(p, '—'))
for k, p in enumerate(right):
    esp[p] = ('h', C0 + 7 - k, names.get(p, '—'))
module('U2', 'U2 ESP32-C3', esp, body=(C0 - 1.6, 'c-', C0 + 7.8, 'h+'), color='#111827')

# J2 / remote DHT22: no header on the breadboard. The sensor cable's three
# leads land directly: VCC in the 3V3 rail, GND in the GND rail, DATA in the
# GPIO3 column.
parts['J2'] = dict(kind='cable', label='remote DHT22 leads', color='#7c3aed',
                   pins={'1': ('B+', 16), '2': ('b', 8), '3': ('B-', 16)},
                   names={'1': 'DHT VCC', '2': 'DHT DATA', '3': 'DHT GND'})

# ADS1115 in the bottom half, pins in row j, rotated 180° so the board hangs
# out over the bottom rails. Silkscreen order (pins down) VDD GND SCL SDA ADDR
# ALRT A0 A1 A2 A3 reads reversed left→right from this side.
ads_order = [('10', 'A3'), ('9', 'A2'), ('8', 'A1'), ('6', 'A0'), ('7', 'ALRT'),
             ('5', 'ADDR'), ('4', 'SDA'), ('3', 'SCL'), ('2', 'GND'), ('1', 'VDD')]
ADS0 = 18
module('U3', 'U3 ADS1115 (0x48)',
       {p: ('j', ADS0 + k, n) for k, (p, n) in enumerate(ads_order)},
       body=(ADS0 - 0.6, 'j-', ADS0 + 9.6, 'B-+'), color='#0f766e')

# Divider in the top half, above the ADS1115: 12 V strip 17 -> R1 -> node
# strip 21 -> R2 / C1 -> strip 25. Node drops straight across the channel to A0.
# Strip 25 returns to the ADS1115 GND strip (26), NOT to a rail: the divider and
# ADC share one analog ground that meets power ground at a single jumper. Tying
# them to different rails put a ~15 mV, load-dependent rail-to-rail drop in series
# with A0 (~86 mV at the battery after the 5.7:1 scale-up). Found 2026-10-06.
two_lead('R1', 'R1 47k', ('c', 17), ('c', 21), '#b45309')
two_lead('R2', 'R2 10k', ('d', 21), ('d', 25), '#b45309')
two_lead('C1', 'C1 2x1000pF mica', ('e', 21), ('e', 25), '#d97706')

# ---------------------------------------------------------------- jumpers
# (from, to, colour, net label)
RED, BLK, ORG, YEL, BLU, GRN, WHT, VIO = ('#dc2626', '#1f2937', '#ea580c', '#ca8a04',
                                          '#2563eb', '#16a34a', '#9ca3af', '#7c3aed')
jumpers = [
    (('T-', 11), ('a', 11), BLK, 'buck IN− → GND'),
    (('T+', 15), ('a', 15), RED, 'buck IN+ ← 12V'),
    (('j', 11), ('B-', 11), BLK, 'buck OUT− → GND'),
    (('i', 14), ('i', 1), ORG, '5V: buck OUT+ → ESP 5V'),
    (('T-', 10), ('B-', 10), BLK, 'GND tie, top ↔ bottom rails'),
    (('j', 2), ('B-', 2), BLK, 'ESP GND'),
    (('j', 3), ('B+', 3), RED, 'ESP 3V3 → 3V3 rail'),
    (('T+', 17), ('a', 17), RED, '12V to divider top'),
    (('a', 25), ('h', 26), BLK, 'divider GND → ADS GND strip'),
    (('b', 21), ('f', 21), GRN, 'A0 node → ADS A0'),
    (('a', 6), ('f', 24), BLU, 'GPIO5 → SDA'),
    (('a', 5), ('f', 25), YEL, 'GPIO6 → SCL'),
    (('g', 23), ('g', 26), BLK, 'ADDR → GND (0x48)'),
    (('T-', 26), ('f', 26), BLK, 'analog GND: single tie to power GND'),
    (('i', 27), ('B+', 29), RED, 'ADS VDD ← 3V3'),
]


# ---------------------------------------------------------------- validation
def node_of(hole):
    row, col = hole
    if row in RAILS:
        return ('rail', row)
    if row in TOP_ROWS:
        return ('top', col)
    if row in BOT_ROWS:
        return ('bot', col)
    raise ValueError(hole)


def validate():
    errs = []
    used = {}
    for ref, p in parts.items():
        for pin, hole in p['pins'].items():
            r, c = hole
            if not (1 <= c <= NCOLS):
                errs.append(f'{ref}.{pin} off board at {hole}')
            if hole in used:
                errs.append(f'hole {r}{c} used by {used[hole]} and {ref}.{pin}')
            used[hole] = f'{ref}.{pin}'
    for a, b, _, lab in jumpers:
        for h in (a, b):
            if h in used:
                errs.append(f'jumper "{lab}" end {h[0]}{h[1]} collides with {used[h]}')
            used[h] = f'jumper {lab}'

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    for a, b, _, _ in jumpers:
        union(node_of(a), node_of(b))
    # redundant MP1584 holes are internally the same net
    for p in '1234':
        union(node_of(parts['U1']['pins'][p]), node_of(parts['U1']['pins'][p + 'b']))
    # off-board: J1.1 -- F1.1 (battery+ through the fuse) is not on the board

    t = NETLIST.read_text()
    nets = {}
    for m in re.finditer(r'\(net\s*\(code "\d+"\)\s*\(name "([^"]*)"\)(.*?)\n\t\t\)', t[t.index('(nets'):], re.S):
        nets[m[1]] = re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', m[2])
    if not nets:
        errs.append('no nets parsed from netlist')

    group_net = {}
    net_report = []
    for net, nodes in nets.items():
        groups = set()
        for ref, pin in nodes:
            hole = parts.get(ref, {}).get('pins', {}).get(pin)
            if hole is None:
                if parts.get(ref, {}).get('kind') == 'off':
                    continue
                errs.append(f'{net}: {ref}.{pin} not placed')
                continue
            groups.add(find(node_of(hole)))
        if len(groups) > 1:
            errs.append(f'{net}: OPEN — split across {len(groups)} groups')
        for g in groups:
            if g in group_net and group_net[g] != net:
                errs.append(f'SHORT: {net} and {group_net[g]}')
            group_net[g] = net
        net_report.append((net, len(nodes)))

    # rails must carry the nets they are labelled with
    # (unnamed nets get auto-names that shift with refs, so identify by a member pin)
    net_with = lambda ref, pin: next(n for n, nodes in nets.items() if (ref, pin) in nodes)
    expect = {'T+': '/12vPROT', 'T-': '/GND', 'B+': net_with('U2', '2'), 'B-': '/GND'}
    for rail, want in expect.items():
        got = group_net.get(find(('rail', rail)), '(nothing)')
        if got != want:
            errs.append(f'rail {rail} should carry {want} but carries {got}')

    # unused module pins must be isolated
    netted = {(r, p) for nodes in nets.values() for r, p in nodes}
    for ref in ('U2', 'U3'):
        for pin, hole in parts[ref]['pins'].items():
            if (ref, pin) in netted:
                continue
            g = find(node_of(hole))
            if g in group_net:
                errs.append(f'unused {ref}.{pin} lands on net {group_net[g]}')
            others = [who for h2, who in used.items()
                      if h2[0] not in RAILS and h2 != hole and node_of(h2) == node_of(hole)]
            if others:
                errs.append(f'unused {ref}.{pin} shares strip with {others}')
    return errs, net_report


# ---------------------------------------------------------------- rendering
P = 18                      # px per 0.1"
X0, Y0 = 70, 70
ROW_Y = {'T+': 0, 'T-': 1, **{r: 3 + i for i, r in enumerate(TOP_ROWS)},
         **{r: 10 + i for i, r in enumerate(BOT_ROWS)}, 'B+': 16, 'B-': 17}


def xy(hole):
    r, c = hole
    return X0 + (c - 1) * P, Y0 + ROW_Y[r] * P


def ry(spec):
    """'c-' = half a pitch above row c, 'h+' = half below row h."""
    r, s = spec[:-1], spec[-1]
    return Y0 + ROW_Y[r] * P + (-0.5 if s == '-' else 0.5) * P * 1.6


def render(net_report):
    W = X0 * 2 + (NCOLS - 1) * P
    H = Y0 * 2 + 17 * P + 40
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
         f'font-family="ui-monospace,Menlo,monospace">']
    s.append(f'<rect x="{X0-40}" y="{Y0-40}" width="{(NCOLS-1)*P+80}" height="{17*P+80}" rx="10" fill="#f4f1ea" stroke="#cfc8b8"/>')
    # rails
    for rail, col in (('T+', '#dc2626'), ('T-', '#2563eb'), ('B+', '#dc2626'), ('B-', '#2563eb')):
        y = Y0 + ROW_Y[rail] * P
        s.append(f'<line x1="{X0-10}" x2="{X0+(NCOLS-1)*P+10}" y1="{y + (-P*0.55 if rail in ("T+","B+") else P*0.55)}" '
                 f'y2="{y + (-P*0.55 if rail in ("T+","B+") else P*0.55)}" stroke="{col}" stroke-width="2"/>')
        s.append(f'<text x="{X0-34}" y="{y+4}" font-size="11" fill="{col}">{rail}</text>')
        s.append(f'<text x="{X0+(NCOLS-1)*P+16}" y="{y+4}" font-size="10" fill="{col}">{RAILS[rail]}</text>')
    # channel
    s.append(f'<rect x="{X0-10}" y="{Y0+7.6*P}" width="{(NCOLS-1)*P+20}" height="{1.8*P}" fill="#e7e1d3"/>')
    # holes + labels
    for c in range(1, NCOLS + 1):
        x = X0 + (c - 1) * P
        if c == 1 or c % 5 == 0:
            s.append(f'<text x="{x}" y="{Y0+2.2*P}" font-size="9" text-anchor="middle" fill="#8a8374">{c}</text>')
            s.append(f'<text x="{x}" y="{Y0+15.3*P}" font-size="9" text-anchor="middle" fill="#8a8374">{c}</text>')
        for r in ROW_Y:
            s.append(f'<rect x="{x-3}" y="{Y0+ROW_Y[r]*P-3}" width="6" height="6" fill="#3b3830" opacity=".55"/>')
    for r in TOP_ROWS + BOT_ROWS:
        s.append(f'<text x="{X0-22}" y="{Y0+ROW_Y[r]*P+4}" font-size="10" fill="#8a8374">{r}</text>')

    # modules
    for ref, p in parts.items():
        if p['kind'] != 'module':
            continue
        c0, r0, c1, r1 = p['body']
        x0, x1 = X0 + (c0 - 1) * P, X0 + (c1 - 1) * P
        y0, y1 = ry(r0), ry(r1)
        s.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" rx="4" fill="{p["color"]}" '
                 f'fill-opacity=".18" stroke="{p["color"]}" stroke-width="2"/>')
        ly = Y0 + 8.5 * P + 4 if ref in ('U1', 'U2') else y1 + 14
        if ref == 'J2':
            ly = y1 + 30
        s.append(f'<text x="{(x0+x1)/2}" y="{ly}" font-size="11" font-weight="bold" text-anchor="middle" '
                 f'fill="{p["color"]}">{html.escape(p["label"])}</text>')
        for pin, hole in p['pins'].items():
            x, y = xy(hole)
            nm = p['names'][pin]
            used_pin = nm not in ('—', 'A1', 'A2', 'A3', 'ALRT')
            s.append(f'<rect x="{x-5}" y="{y-5}" width="10" height="10" fill="{p["color"] if used_pin else "#bbb"}"/>')
            if nm != '—':
                up = hole[0] in 'abc' or ref == 'J2'
                ty = y - 8 if up else y + 10
                anchor = 'start' if up else 'end'
                s.append(f'<text x="{x+2}" y="{ty}" font-size="8.5" text-anchor="{anchor}" '
                         f'transform="rotate(-50 {x+2} {ty})" fill="{p["color"]}">{html.escape(nm)}</text>')

    # cable landings
    for ref, p in parts.items():
        if p['kind'] != 'cable':
            continue
        for pin, hole in p['pins'].items():
            x, y = xy(hole)
            s.append(f'<circle cx="{x}" cy="{y}" r="6" fill="none" stroke="{p["color"]}" stroke-width="2.5"/>')
            dx = 14 if hole[0] not in RAILS else -14       # rail landings label to the left, clear of U3
            s.append(f'<path d="M{x},{y} l{dx},-10" stroke="{p["color"]}" stroke-width="2.5" stroke-dasharray="3 2"/>')
            s.append(f'<text x="{x+dx*1.15}" y="{y-12}" font-size="9" text-anchor="{"start" if dx > 0 else "end"}" '
                     f'fill="{p["color"]}">{html.escape(p["names"][pin])}</text>')

    # two-lead parts
    for ref, p in parts.items():
        if p['kind'] != 'lead':
            continue
        (xa, ya), (xb, yb) = xy(p['pins']['1']), xy(p['pins']['2'])
        s.append(f'<line x1="{xa}" y1="{ya}" x2="{xb}" y2="{yb}" stroke="#666" stroke-width="2"/>')
        mx, my = (xa + xb) / 2, (ya + yb) / 2
        if ya == yb:
            s.append(f'<rect x="{mx-P*0.9}" y="{my-5}" width="{P*1.8}" height="10" rx="4" fill="{p["color"]}"/>')
            s.append(f'<text x="{mx}" y="{my-9}" font-size="9" text-anchor="middle" fill="#333">{html.escape(p["label"])}</text>')
        else:
            s.append(f'<rect x="{mx-5}" y="{my-P*0.45}" width="10" height="{P*0.9}" rx="3" fill="{p["color"]}"/>')
            if p['pins']['1'][0] in RAILS:      # rail-to-rail part: label above the board, angled
                ly = Y0 - P * 1.1
                s.append(f'<text x="{mx}" y="{ly}" font-size="9" fill="#333" '
                         f'transform="rotate(-40 {mx} {ly})">{html.escape(p["label"])}</text>')
            else:
                s.append(f'<text x="{mx+9}" y="{my+3}" font-size="9" fill="#333">{html.escape(p["label"])}</text>')
        for h in p['pins'].values():
            x, y = xy(h)
            s.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="#666"/>')

    # jumpers
    for a, b, col, lab in jumpers:
        (xa, ya), (xb, yb) = xy(a), xy(b)
        if ya == yb:
            path = f'M{xa},{ya} Q{(xa+xb)/2},{ya-P*1.2} {xb},{yb}'
        elif xa == xb:
            path = f'M{xa},{ya} L{xb},{yb}'
        else:
            path = f'M{xa},{ya} C{xa},{(ya+yb)/2} {xb},{(ya+yb)/2} {xb},{yb}'
        s.append(f'<path d="{path}" fill="none" stroke="{col}" stroke-width="3.2" stroke-linecap="round" opacity=".9"><title>{html.escape(lab)}</title></path>')
        for x, y in ((xa, ya), (xb, yb)):
            s.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{col}"/>')

    # bench lead
    x, y = xy(('T+', 1))
    s.append(f'<text x="{x-58}" y="{y-56}" font-size="9" fill="#dc2626">bench + via F1 fuse → T+ @1</text>')
    x, y = xy(('T-', 1))
    s.append(f'<text x="{x-58}" y="{y+18}" font-size="9" fill="#2563eb">bench −</text>')
    s.append('</svg>')
    return '\n'.join(s)


def hole_name(h):
    return f'{h[0]} rail @{h[1]}' if h[0] in RAILS else f'{h[0]}{h[1]}'


def build_table():
    rows = []
    for ref, p in parts.items():
        if p['kind'] in ('module', 'cable'):
            used = [f'{p["names"][k]}={hole_name(h)}' for k, h in p['pins'].items() if p['names'][k] != '—']
            rows.append((ref, p['label'], ', '.join(used)))
        elif p['kind'] == 'lead':
            note = f' — {p["polar"]}' if p.get('polar') else ''
            rows.append((ref, p['label'], f'{hole_name(p["pins"]["1"])} ↔ {hole_name(p["pins"]["2"])}{note}'))
    jr = [(hole_name(a), hole_name(b), lab) for a, b, _, lab in jumpers]
    return rows, jr


def main():
    errs, net_report = validate()
    if errs:
        print('LAYOUT ERRORS:')
        for e in errs:
            print('  ', e)
        sys.exit(1)
    print(f'OK: {len(net_report)} nets, no opens, no shorts, unused pins isolated')
    rows, jr = build_table()
    svg = render(net_report)
    td = lambda cells: '<tr>' + ''.join(f'<td>{html.escape(c)}</td>' for c in cells) + '</tr>'
    OUT.write_text(f'''<!doctype html><meta charset="utf-8"><title>Irin breadboard</title>
<style>body{{font:14px -apple-system,system-ui,sans-serif;margin:24px;background:#fff;color:#222}}
table{{border-collapse:collapse;margin:8px 0 24px}}td,th{{border:1px solid #ddd;padding:4px 8px;text-align:left;vertical-align:top}}
th{{background:#f4f1ea}} .wrap{{overflow-x:auto}} code{{background:#f4f1ea;padding:1px 4px}}</style>
<h2>Irin 12V battery monitor — breadboard (400-point, 30 columns)</h2>
<p>Generated by <code>make_breadboard.py</code> and validated against <code>irin.net</code>:
every net connected, no shorts, unused module pins isolated. Hover a jumper for its purpose.</p>
<div class="wrap">{svg}</div>
<h3>Parts</h3><table><tr><th>Ref</th><th>Part</th><th>Holes</th></tr>{''.join(td(r) for r in rows)}</table>
<h3>Jumpers</h3><table><tr><th>From</th><th>To</th><th>Purpose</th></tr>{''.join(td(r) for r in jr)}</table>
''')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
