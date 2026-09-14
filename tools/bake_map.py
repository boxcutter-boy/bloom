"""Bake the Bloom map basemap into one static image.

Downloads basemap tiles covering the frame the app needs, stitches them, and
reports the exact geo bounds so pins can be placed by lat/lng. Leaves the tiles
un-tinted — the CSS filter in index.html does the reskin, so the palette stays
tunable without re-baking.

Source is Esri's Dark Gray Canvas *base* layer. It replaced CARTO Dark Matter,
which now stamps "API KEY REQUIRED" diagonally across every unauthenticated
tile. Two things make the swap a gain rather than a workaround: no key or
account is needed, and the base layer carries no street-name labels — CARTO's
had "Long Island Expressway" and "BROOKLYN" baked in, competing with the app's
own type at every zoom.

Attribution is required and lives in index.html's .map-credit.

Esri serves 256px tiles, so this bakes one zoom level deeper than the old
512px @2x tiles to land on the same ground-per-pixel.

    python3 tools/bake_map.py && python3 tools/crop_map.py
"""
import math, urllib.request, io, json, sys
from PIL import Image

# The frame: Hudson across to Forest Hills, Astoria down past Prospect Park.
# Wide enough that a 2-mile post radius clears every neighborhood in HOODS.
WEST, EAST = -74.030, -73.830
SOUTH, NORTH = 40.628, 40.775

Z = 14
TILE = 256
URL = ('https://services.arcgisonline.com/ArcGIS/rest/services/'
       'Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}')
UA = {'User-Agent': 'bloom-prototype/1.0 (design prototype; contact ferri.illustration@gmail.com)'}


def lon_to_tile(lon, z):
    return (lon + 180.0) / 360.0 * 2 ** z


def lat_to_tile(lat, z):
    r = math.radians(lat)
    return (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * 2 ** z


def tile_to_lon(x, z):
    return x / 2 ** z * 360.0 - 180.0


def tile_to_lat(y, z):
    n = math.pi - 2.0 * math.pi * y / 2 ** z
    return math.degrees(math.atan(math.sinh(n)))


# Derived from the bbox rather than hardcoded, so moving the frame is a
# two-line edit up top instead of arithmetic done by hand.
COLS = range(math.floor(lon_to_tile(WEST, Z)), math.ceil(lon_to_tile(EAST, Z)))
ROWS = range(math.floor(lat_to_tile(NORTH, Z)), math.ceil(lat_to_tile(SOUTH, Z)))

sheet = Image.new('RGB', (TILE * len(COLS), TILE * len(ROWS)))
for cx, x in enumerate(COLS):
    for cy, y in enumerate(ROWS):
        req = urllib.request.Request(URL.format(z=Z, x=x, y=y), headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            img = Image.open(io.BytesIO(r.read())).convert('RGB')
        sheet.paste(img, (cx * TILE, cy * TILE))
    print(f'  col {x} ({cx + 1}/{len(COLS)})', file=sys.stderr)

# Water is the one thing the CSS reskin can't fix downstream. That filter is a
# function of luminance, and Esri draws water DARKER than land (35 vs 71) where
# CARTO drew it brighter — so the same chain that made rivers pale pink turns
# them to pitch. Lift water into the band above the streets and the old
# relationship is restored, tint and all.
#
# Safe to do by threshold: the histogram is two spikes with a hole between them.
# Water is 35 ± 2, land starts at 65, and under 1% of pixels sit in between —
# antialiased shoreline, ramped rather than stepped so the coast doesn't halo.
WATER, EDGE, WATER_OUT = 40, 65, 105
lut = [WATER_OUT if v <= WATER
       else v if v >= EDGE
       else round(WATER_OUT + (EDGE - WATER_OUT) * (v - WATER) / (EDGE - WATER))
       for v in range(256)]
sheet = sheet.convert('L').point(lut)

out = '/Users/eferri/Code/bloom/assets/map-nyc.jpg'
sheet.save(out, 'JPEG', quality=92, optimize=True, progressive=True)

print(json.dumps({
    'file': out,
    'tiles': len(COLS) * len(ROWS),
    'px': sheet.size,
    'west':  tile_to_lon(COLS.start, Z),
    'east':  tile_to_lon(COLS.stop, Z),
    'north': tile_to_lat(ROWS.start, Z),
    'south': tile_to_lat(ROWS.stop, Z),
}, indent=1))
