import os
import os.path

import tqdm


import requests
import aiohttp
import aiofiles
import asyncio
import urllib
import urllib.parse
import bs4
from stat import S_ISREG

semaphore = asyncio.Semaphore(3)
user_agent = "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
parser = 'html.parser'


async def site_read_get_links(site_url: str) -> list:
    links: list = []

    response = requests.get(site_url, headers={'User-Agent': user_agent})
    header = response.headers.get('content-type', '').split(";")[0].lower()

    if not header or response.status_code != 200:
        return links

    soup = bs4.BeautifulSoup(response.content, parser)

    for map_links in soup.find_all('a', href=True):
        if ".zip" in map_links['href']:
            links.append(map_links['href'])
    return links


def prepare_folders() -> None:
    os.makedirs("action", exist_ok=True)
    os.chmod("action", 0o755)
    os.makedirs("action/maps", exist_ok=True)
    os.makedirs("action/texture", exist_ok=True)
    os.makedirs("action/env", exist_ok=True)
    os.makedirs("action/sound", exist_ok=True)
    os.makedirs("tmp", exist_ok=True)
    os.chmod("tmp", 0o755)


async def download_maps(src: str, ssl=True):
    async  with aiohttp.ClientSession() as session:
        name = os.path.basename(urllib.parse.urlparse(src).path)
        req = await session.get(src)
        content = await req.read()


        async with aiofiles.open(f"tmp/{name}", "wb") as f:
            await f.write(content)


async def safe_download_maps(url: str):
    async with semaphore:
        return await download_maps(url)



def check_map_downloaded(src: str):
    name = os.path.basename(urllib.parse.urlparse(src).path)
    if os.path.exists(f"tmp/{name}"):
        return True
    return False



async def start_download():
    links = await site_read_get_links("https://www.lahtela.com/action-quake-2-maps/")

    count = 0
    tasks = set()

    for valid_link in links:
        task = asyncio.create_task(safe_download_maps(valid_link))
        if not check_map_downloaded(valid_link):
            continue

        tasks.add(task)
        task.add_done_callback(tasks.discard)

    for u in tqdm.tqdm(asyncio.as_completed(tasks), total=len(tasks)):
        await u

    """
    tasks = []

    for valid_link in links:
            tasks.append(asyncio.ensure_future(safe_download_maps(valid_link)))

    total_tasks = [
        await f for f in tqdm.tqdm(asyncio.as_completed(tasks), total=len(links))
    ]

    return total_tasks
    """

if __name__ == "__main__":

    prepare_folders()

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(start_download())
    finally:
        loop.shutdown_asyncgens()
        loop.close()


