#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：hummingbot 
@File    ：mymexctest.py
@Author  ：
@Date    ：2021/10/20 9:51 上午 
'''

from typing import (
    Dict,
    List,
    Optional,
)

from hummingbot.core.data_type.order_book_row import OrderBookRow
from hummingbot.core.data_type.order_book_message import (
    OrderBookMessage,
    OrderBookMessageType,
)

update_id = 123
asks = [
    {
        "price": "182.4417544",
        "quantity": "115.5"
    },
    {
        "price": "182.4217568",
        "quantity": "135.7"
    }
]
asd = [
    # OrderBookRow(float(price.value), float(amount), update_id)
    OrderBookRow(float(values["price"]), float(values["quantity"]), update_id) for values in asks
]

print(asd)
