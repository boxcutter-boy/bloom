"""Bake the Bloom map basemap into one static image.

Downloads CARTO Dark Matter tiles (@2x) covering the Brooklyn view, stitches
them, and reports the exact geo bounds so pins can be placed by lat/lng.
Leaves the tiles un-tinted — the CSS filter in index.html still does the reskin,
so the palette stays tunable without re-baking.
"""
import math, urllib.request, io, json, sys
from PIL import Image

Z = 13
TILE = 512                      # @2x tiles
COLS = range(2412, 2416)        # x
ROWS = range(3076, 3083)        # y
UA = {'User-Agent': 'bloom-prototype/1.0 (design prototype; contact ferri.illustration@gmail.com)'}


def tile_to_lon(x, z):
    return x / 2 ** z * 360.0 - 180.0


def tile_to_lat(y, z):
    n = math.pi - 2.0 * math.pi * y / 2 ** z
    return math.degrees(math.atan(math.sinh(n)))


sheet = Image.new('RGB', (TILE * len(COLS), TILE * len(ROWS)))
for cx, x in enumerate(COLS):
    for cy, y in enumerate(ROWS):
        url = f'https://a.basemaps.cartocdn.com/dark_all/{Z}/{x}/{y}@2x.png'
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            img = Image.open(io.BytesIO(r.read())).convert('RGB')
        sheet.paste(img, (cx * TILE, cy * TILE))
        print(f'  {x},{y}', file=sys.stderr)

out = '/Users/eferri/Code/bloom/assets/map-brooklyn.jpg'
sheet.save(out, 'JPEG', quality=82, optimize=True, progressive=True)

print(json.dumps({
    'file': out,
    'px': sheet.size,
    'cssPx': [sheet.size[0] // 2, sheet.size[1] // 2],
    'west':  tile_to_lon(COLS.start, Z),
    'east':  tile_to_lon(COLS.stop, Z),
    'north': tile_to_lat(ROWS.start, Z),
    'south': tile_to_lat(ROWS.stop, Z),
}, indent=1))
