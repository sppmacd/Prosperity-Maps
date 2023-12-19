import hashlib
import logging
import os
import aiohttp

cache = {}

CACHE_DIR = ".cache"


def url_hash(url: str) -> str:
    """Calculate hash of url in cache"""
    return hashlib.md5(url.encode()).hexdigest()


async def get(session: aiohttp.ClientSession, url: str, **kwargs) -> bytes:
    """GET url or read from cache/ if it exists"""
    cache_path = f"{CACHE_DIR}/{url_hash(url)}"
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return f.read()
    logging.info(f"Downloading: {url}")
    async with session.get(url, **kwargs) as response:
        if response.status == 200:
            if not os.path.isdir(CACHE_DIR):
                os.mkdir(CACHE_DIR)
            content = await response.read()
            with open(cache_path, "wb") as f:
                f.write(content)
            return content
        raise Exception(f"HTTP ERROR {response.status}: {await response.text()}")


def remove_from_cache(url: str):
    """Remove url from cache so that it will be downloaded again"""
    os.remove(f"{CACHE_DIR}/{hash(url)}")
