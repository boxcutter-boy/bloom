"""Crop the baked basemap to the frame the app needs, downscale it to the size
it's actually drawn at, and emit it as a data: URI so index.html stays a single
portable file.

Cropped to an explicit bbox rather than a centre-plus-size: the frame is chosen
so a 2-mile post radius fits around every neighborhood in HOODS, and that's a
statement about edges, not about the middle.
"""
import math, json, base64, io
from PIL import Image

SRC = '/Users/eferri/Code/bloom/assets/map-nyc.jpg'
# geo bounds of the full stitched sheet, straight from bake_map.py
W_, E_ = -74.0478515625, -73.828125
N_, S_ = 40.780541431860314, 40.613952441166596

# what we keep. South of the screenshot's edge by ~1.3km so Crown Heights,
# the tightest of the six, still clears a 2-mile circle.
WEST, EAST = -74.030, -73.830
SOUTH, NORTH = 40.628, 40.775

# 14.45 metres per CSS pixel, matching the old sheet — the feed map's panning
# and its pin scatter are both tuned to that, and this keeps them untouched.
M_PER_CSS_PX = 14.45
DPR = 1.5                        # what the old image shipped at


def merc(lat):
    return math.log(math.tan(math.pi / 4 + lat * math.pi / 360))


def unmerc(m):
    return math.degrees(2 * math.atan(math.exp(m)) - math.pi / 2)


img = Image.open(SRC)
W, H = img.size

yN, yS = merc(N_), merc(S_)
fx = lambda lng: (lng - W_) / (E_ - W_)
fy = lambda lat: (merc(N_) - merc(lat)) / (yN - yS)

left, right = round(fx(WEST) * W), round(fx(EAST) * W)
top, bottom = round(fy(NORTH) * H), round(fy(SOUTH) * H)
assert 0 <= left < right <= W and 0 <= top < bottom <= H, 'crop falls outside the stitch'
crop = img.crop((left, top, right, bottom))

# geo bounds of the crop as actually cut, not as asked for — rounding to whole
# pixels moves the edges slightly, and the app projects against these numbers
west = W_ + (left / W) * (E_ - W_)
east = W_ + (right / W) * (E_ - W_)
north = unmerc(yN - (top / H) * (yN - yS))
south = unmerc(yN - (bottom / H) * (yN - yS))

lat_mid = (north + south) / 2
km_w = (east - west) * 111320 * math.cos(math.radians(lat_mid))
css_w = round(km_w / M_PER_CSS_PX)
css_h = round(css_w * crop.size[1] / crop.size[0])
crop = crop.resize((round(css_w * DPR), round(css_h * DPR)), Image.LANCZOS)

# Stored grayscale: the CSS reskin opens with grayscale(1), so every byte of
# chroma here is discarded at render time. Saves little on these tiles — they're
# already near-achromatic — but it's free and it can't change what's drawn.
buf = io.BytesIO()
crop.convert('L').save(buf, 'JPEG', quality=62, optimize=True, progressive=False)
data = buf.getvalue()

uri = 'data:image/jpeg;base64,' + base64.b64encode(data).decode()
open('/Users/eferri/Code/bloom/assets/map.datauri', 'w').write(uri)

print(json.dumps({
    'jpegBytes': len(data), 'dataUriBytes': len(uri),
    'px': crop.size, 'cssPx': [css_w, css_h],
    'west': west, 'east': east, 'north': north, 'south': south,
    'mPerCssPx': round(km_w / css_w, 2),
}, indent=1))
