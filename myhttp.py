#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：hummingbot 
@File    ：http.py
@Author  ：
@Date    ：2021/10/18 9:43 上午 
'''
import ssl

import aiohttp
import asyncio

from hummingbot.client.settings import GATEAWAY_CA_CERT_PATH, GATEAWAY_CLIENT_CERT_PATH, GATEAWAY_CLIENT_KEY_PATH


async def httptest():
    # http_client = aiohttp.ClientSession()
    proxies = {
        "http": "http://127.0.0.1:1087",
        "https": "http://127.0.0.1:1087"
    }
    conn = aiohttp.TCPConnector(ssl=False)
    http_client = aiohttp.ClientSession(connector=conn)
    # response_coro =await http_client.request(method="GET", url="https://api.gateio.ws/api/v4/spot/currency_pairs",)
    headers = {"Content-Type": "application/json"}
    response_coro = http_client.request(method="GET", url="https://api.hitbtc.com/api/2/public/symbol",
                                             timeout=5,
                                        headers=headers,params=None,
                                             proxy="http://127.0.0.1:1087"
                                             )
    http_status, parsed_response, request_errors = await aiohttp_response_with_errors(response_coro)
    print(http_status, parsed_response, request_errors)
    await http_client.close()
    print(response_coro)

async def aiohttp_response_with_errors(request_coroutine):
    http_status, parsed_response, request_errors = None, None, False
    try:
        async with request_coroutine as response:
            http_status = response.status
            try:
                parsed_response = await response.json()
            except Exception:
                request_errors = True
                try:
                    parsed_response = str(await response.read())
                    if len(parsed_response) > 100:
                        parsed_response = f"{parsed_response[:100]} ... (truncated)"
                except Exception:
                    pass
            TempFailure = (parsed_response is None or
                           (response.status not in [200, 201] and "error" not in parsed_response))
            if TempFailure:
                parsed_response = response.reason if parsed_response is None else parsed_response
                request_errors = True
    except Exception:
        request_errors = True
    return http_status, parsed_response, request_errors

if __name__ == "__main__":
    asyncio.run(httptest())