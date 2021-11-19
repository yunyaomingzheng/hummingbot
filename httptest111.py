#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：hummingbot 
@File    ：httptest111.py
@Author  ：
@Date    ：2021/10/18 10:29 上午 
'''
import asyncio
import aiohttp
from aiohttp import ClientTimeout


async def fetch(url):
    proxies = {
        "http": "http://127.0.0.1:1087",
        "https": "http://127.0.0.1:1087"
    }
    conn = aiohttp.TCPConnector(ssl=False)  # 防止ssl报错
    async with aiohttp.request('GET', url, connector=conn,timeout=ClientTimeout(total=5),proxy="http://127.0.0.1:1087") as resp:
        if resp.status != 200:
            return ''
        return await resp.text()


async def run():
    url = 'https://www.okex.com/api/v5/public/instruments?instType=SPOT'
    html = await fetch(url)
    return html


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(run())
    print(res)
