import asyncio
import json
import math
import traceback
import aiohttp
import caching
import datetime
from PIL import Image, ImageDraw
import io
import os
import tqdm

URL = "map.prosperitymc.net"


def build_url(dimension: str, zoom: int, region_coords: tuple[int, int]):
    return f"https://{URL}/tiles/minecraft_{dimension}/{zoom}/{region_coords[0]}_{region_coords[1]}.png"


def download_image(session: aiohttp.ClientSession, dimension: str, zoom: int, region_coords: tuple[int, int]):
    u = build_url(dimension, zoom, region_coords)
    # print(u)
    return caching.get(session, u)


# x,z min max are in blocks
async def build_full_map(name: str, dimension: str, xminmax: tuple[int, int], zminmax: tuple[int, int], *,
                         zoom: int = 3,
                         scaledown: int = 1):
    date_string = datetime.datetime.now().strftime('%Y-%m-%d')
    cache_dir = f"cache_{date_string}"

    print(
        f"{name}: {dimension} X={xminmax[0]}..{xminmax[1]} Z={zminmax[0]}..{zminmax[1]} zoom={zoom} scaledown={scaledown}")

    if os.path.exists(cache_dir):
        os.rename(cache_dir, caching.CACHE_DIR)

    REGION_SIZES = [4096, 2048, 1024, 512]
    PX_PER_REGION = 512 // scaledown
    xmin = xminmax[0]
    xmax = xminmax[1]
    zmin = zminmax[0]
    zmax = zminmax[1]

    try:
        xrange = range(math.floor(xmin / REGION_SIZES[zoom]), math.ceil(xmax / REGION_SIZES[zoom]))
        zrange = range(math.floor(zmin / REGION_SIZES[zoom]), math.ceil(zmax / REGION_SIZES[zoom]))

        count = len(xrange) * len(zrange)

        with tqdm.tqdm(total=count) as pbar:
            async with aiohttp.ClientSession() as session:
                for x in xrange:
                    for z in zrange:
                        img = Image.new(mode='RGB', size=(PX_PER_REGION, PX_PER_REGION))

                        idx = len(zrange) * (x - xrange.start) + z - zrange.start
                        # print(f"loading {dimension},{x},{z} {idx}/{count} {idx * 100 / (count):.2f}%")
                        region = await download_image(session, dimension, zoom, (x, z))
                        if len(region) != 0:
                            os.makedirs(f"maps/{date_string}/{name}/{x}", exist_ok=True)
                            img = Image.open(io.BytesIO(region)).resize((PX_PER_REGION, PX_PER_REGION))
                            img.save(
                                f"maps/{date_string}/{name}/{x}/{z}.webp", quality=60)

                        pbar.update()
    except KeyboardInterrupt:
        pass
    finally:
        os.rename(caching.CACHE_DIR, cache_dir)


with open("areas.json") as f:
    areas = json.load(f)

for name, area in areas.items():
    dimension = area["dimension"]
    xrange = (area["xmin"], area["xmax"])
    zrange = (area["zmin"], area["zmax"])
    zoom = area["zoom"]
    scaledown = area.get("scaledown") or 1

    try:
        asyncio.run(build_full_map(name, dimension, xrange, zrange, zoom=zoom, scaledown=scaledown))
    except Exception:
        print(traceback.format_exc())

# add index
for date in os.listdir("maps"):
    if date == "list.json":
        continue
    for area in os.listdir(f"maps/{date}"):
        area = os.path.splitext(area)[0]
        if not "files" in areas[area]:
            areas[area]["files"] = []
        areas[area]["files"].append(date)

for area in areas.values():
    area["files"].sort()

# remove web hidden ones
for k, v in [*areas.items()]:
    if v.get("webHidden") or False:
        del areas[k]

with open("maps/list.json", "w") as f:
    json.dump(areas, f, indent=4)
