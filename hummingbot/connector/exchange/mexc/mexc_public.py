#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import time

import ssl

ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)

ws_status = {
    1: 'NEW',
    2: 'FILLED',
    3: 'PARTIALLY_FILLED',
    4: 'CANCELED',
    5: 'PARTIALLY_CANCELED'
}


def seconds():
    return int(time.time())


def milliseconds():
    return int(time.time() * 1000)


def microseconds():
    return int(time.time() * 1000000)


def convert_from_exchange_trading_pair(exchange_trading_pair: str) -> str:
    return exchange_trading_pair.replace("_", "-")


def convert_to_exchange_trading_pair(hb_trading_pair: str) -> str:
    return hb_trading_pair.replace("-", "_")


def ws_order_status_convert_to_str(ws_order_status: int) -> str:
    return ws_status[ws_order_status]
