#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import time


def seconds():
    return int(time.time())


def milliseconds():
    return int(time.time() * 1000)


def microseconds():
    return int(time.time() * 1000000)


def convert_from_exchange_trading_pair(exchange_trading_pair: str) -> str:
    return str.replace("_", "-");


def convert_to_exchange_trading_pair(hb_trading_pair: str) -> str:
    return str.replace("-", "_");

