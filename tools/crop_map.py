"""Crop the baked basemap down to just what the map view needs, then emit it
as a data: URI so index.html stays a single portable file."""
import math, json, base64, io
from PIL import Image

SRC = '/Users/eferri/Code/bloom/assets/map-brooklyn.jpg'
# geo bounds of the full stitched sheet
W_, E_ = -74.00390625, -73.828125
N_, S_ = 40.847060356071225, 40.613952441166596

CENTRE = (40.7005, -73.9280)     # middle of the pin cluster
OUT_CSS = (576, 928)             # CSS px; image is 2x this for retina
SCALE = 2


def merc(lat):
    return math.log(math.tan(math.pi / 4 + lat * math.pi / 360))


def unmerc(m):
    return math.degrees(2 * math.atan(math.exp(m)) - math.pi / 2)


img = Image.open(SRC)
W, H = img.size                                   # 2048 x 3584

fx = (CENTRE[1] - W_) / (E_ - W_)
yN, yS = merc(N_), merc(S_)
fy = (yN - merc(CENTRE[0])) / (yN - yS)

ow, oh = OUT_CSS[0] * SCALE, OUT_CSS[1] * SCALE
left = round(fx * W - ow / 2)
top = round(fy * H - oh / 2)
left = max(0, min(left, W - ow))                  # clamp inside the sheet
top = max(0, min(top, H - oh))

crop = img.crop((left, top, left + ow, top + oh))

buf = io.BytesIO()
crop.save(buf, 'JPEG', quality=78, optimize=True, progressive=False)
data = buf.getvalue()

# geo bounds of the crop
west = W_ + (left / W) * (E_ - W_)
east = W_ + ((left + ow) / W) * (E_ - W_)
north = unmerc(yN - (top / H) * (yN - yS))
south = unmerc(yN - ((top + oh) / H) * (yN - yS))

uri = 'data:image/jpeg;base64,' + base64.b64encode(data).decode()
open('/private/tmp/claude-501/-Users-eferri-Code-bloom/6ac95b60-1ef7-42c9-b284-30f920228e21/scratchpad/map.datauri', 'w').write(uri)

print(json.dumps({
    'jpegBytes': len(data), 'dataUriBytes': len(uri),
    'px': crop.size, 'cssPx': OUT_CSS,
    'west': west, 'east': east, 'north': north, 'south': south,
}, indent=1))
