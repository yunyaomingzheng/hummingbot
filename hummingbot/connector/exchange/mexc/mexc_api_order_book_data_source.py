#!/usr/bin/env python
from urllib.parse import urlencode

import aiohttp
import aiohttp.client_ws
import asyncio

import json
import logging
import pandas as pd
import time
from typing import (
    Any,
    AsyncIterable,
    Dict,
    List,
    Optional,
)
import websockets
from websockets.exceptions import ConnectionClosed
from hummingbot.connector.exchange.mexc import mexc_public
from hummingbot.connector.exchange.mexc.mexc_public import (
    convert_from_exchange_trading_pair,
    convert_to_exchange_trading_pair
)
from hummingbot.connector.exchange.mexc import mexc_utils
from hummingbot.core.data_type.order_book_message import OrderBookMessage
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.logger import HummingbotLogger
from hummingbot.connector.exchange.mexc.mexc_order_book import MexcOrderBook
from hummingbot.connector.exchange.mexc.constants import (
    MEXC_SYMBOL_URL,
    MEXC_DEPTH_URL,
    MEXC_TICKERS_URL,
    MEXC_WS_URI_PUBLIC, MEXC_BASE_URL,
)

from dateutil.parser import parse as dateparse
import ssl

ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)


class MexcAPIOrderBookDataSource(OrderBookTrackerDataSource):
    MESSAGE_TIMEOUT = 120.0
    PING_TIMEOUT = 10.0

    _mexcaobds_logger: Optional[HummingbotLogger] = None

    api_key = ""

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._mexcaobds_logger is None:
            cls._mexcaobds_logger = logging.getLogger(__name__)
        return cls._mexcaobds_logger

    def __init__(self, trading_pairs: List[str]):
        super().__init__(trading_pairs)
        self._trading_pairs: List[str] = trading_pairs

    @staticmethod
    async def fetch_trading_pairs() -> List[str]:
        async with aiohttp.ClientSession() as client:
            params: dict() = {}
            # params.update({'api_key': mexc_meta.api_key})
            url = MEXC_BASE_URL + MEXC_SYMBOL_URL
            print("mexc fetch_trading_pairs", url)
            async with client.get(url, ssl=ssl_context,proxy="http://127.0.0.1:1087") as products_response:

                products_response: aiohttp.ClientResponse = products_response
                if products_response.status != 200:
                    raise IOError(f"Error fetching active MEXC. HTTP status is {products_response.status}.")

                data = await products_response.json()
                print("fetch_trading_pairs:",data)
                data = data['data']

                trading_pairs = []
                for item in data:
                    if item['state'] == "ENABLED":
                        trading_pairs.append(convert_from_exchange_trading_pair(item["symbol"]))
        return trading_pairs

    async def get_new_order_book(self, trading_pair: str) -> OrderBook:
        async with aiohttp.ClientSession() as client:
            print("get_snapshot2")
            snapshot: Dict[str, Any] = await self.get_snapshot(client, trading_pair)

            snapshot_msg: OrderBookMessage = MexcOrderBook.snapshot_message_from_exchange(
                snapshot,
                trading_pair,
                timestamp=mexc_public.microseconds(),
                metadata={"trading_pair": trading_pair})
            order_book: OrderBook = self.order_book_create_function()
            order_book.apply_snapshot(snapshot_msg.bids, snapshot_msg.asks, snapshot_msg.update_id)
            return order_book

    @classmethod
    async def get_last_traded_prices(cls, trading_pairs: List[str]) -> Dict[str, float]:
        async with aiohttp.ClientSession() as client:
            params: dict() = {}
            # params.update({'api_key': mexc_meta.api_key})
            url = MEXC_BASE_URL + MEXC_TICKERS_URL
            print("mexc get_last_traded_prices", url)
            async with client.get(url, ssl=ssl_context,proxy="http://127.0.0.1:1087") as products_response:
                products_response: aiohttp.ClientResponse = products_response
                if products_response.status != 200:
                    raise IOError(f"Error get tickers from MEXC markets. HTTP status is {products_response.status}.")
                data = await products_response.json()
                data = data['data']
                all_markets: pd.DataFrame = pd.DataFrame.from_records(data=data)
                all_markets.set_index("symbol", inplace=True)

                out: Dict[str, float] = {}

                for trading_pair in trading_pairs:
                    exchange_trading_pair = convert_to_exchange_trading_pair(trading_pair)
                    out[trading_pair] = float(all_markets['last'][exchange_trading_pair])
                print("out",out)
                return out

    async def get_trading_pairs(self) -> List[str]:
        print("get_trading_pairs")
        if not self._trading_pairs:
            try:
                self._trading_pairs = await self.fetch_trading_pairs()
            except Exception:
                self._trading_pairs = []
                self.logger().network(
                    "Error getting active exchange information.",
                    exc_info=True,
                    app_warning_msg="Error getting active exchange information. Check network connection."
                )
        return self._trading_pairs

    @staticmethod
    async def get_snapshot(client: aiohttp.ClientSession, trading_pair: str) -> Dict[str, Any]:
        params = {}
        params: dict() = {}
        # params.update({'api_key': mexc_meta.api_key})
        trading_pair = convert_to_exchange_trading_pair(trading_pair)
        tick_url = MEXC_DEPTH_URL.format(trading_pair=trading_pair)
        url = MEXC_BASE_URL + tick_url
        print("mexc get_snapshot", url)
        async with client.get(url, ssl=ssl_context,proxy="http://127.0.0.1:1087") as response:
            response: aiohttp.ClientResponse = response
            if response.status != 200:
                raise IOError(f"Error fetching MEXC market snapshot for {trading_pair}. "
                              f"HTTP status is {response.status}.")
            api_data = await response.read()
            data: Dict[str, Any] = json.loads(api_data)['data']
            data['ts'] = mexc_public.microseconds()

            return data

    @classmethod
    def iso_to_timestamp(cls, date: str):
        return dateparse(date).timestamp()

    # async def listen_for_trades(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue):
    #
    #     while True:
    #         try:
    #             trading_pairs: List[str] = self._trading_pairs
    #             async with websockets.connect(MEXC_WS_URI_PUBLIC) as ws:
    #                 ws: websockets.WebSocketClientProtocol = ws
    #
    #                 for trading_pair in trading_pairs:
    #                     subscribe_request: Dict[str, Any] = {
    #                         # "method": "sub.deal",
    #                         # "param": {
    #                         #     "symbol": trading_pair
    #                         # }
    #                         "op": "sub.deal",
    #                         "symbol": trading_pair,
    #                     }
    #                     await ws.send(json.dumps(subscribe_request))
    #
    #                 async for raw_msg in self._inner_messages(ws):
    #                     decoded_msg: str = raw_msg
    #
    #                     self.logger().debug("decode menssae:" + decoded_msg)
    #
    #                     if '"channel":"push.deal"' in decoded_msg:
    #                         self.logger().debug(f"Recived new trade: {decoded_msg}")
    #
    #                         msg = json.loads(decoded_msg)
    #                         for data in msg['data']:
    #                             trading_pair = msg['symbol']
    #                             trade_message: OrderBookMessage = MexcOrderBook.trade_message_from_exchange(
    #                                 data, data['t'], metadata={"trading_pair": trading_pair}
    #                             )
    #                             self.logger().debug(f'Putting msg in queue: {str(trade_message)}')
    #
    #                             output.put_nowait(trade_message)
    #                     else:
    #                         self.logger().debug(f"Unrecognized message received from MEXC websocket: {decoded_msg}")
    #
    #         except asyncio.CancelledError:
    #             raise
    #         except Exception:
    #             self.logger().error("Unexpected error with WebSocket connection ,Retrying after 30 seconds...",
    #                                 exc_info=True)
    #             await asyncio.sleep(30.0)
    #
    # async def _inner_message(self,
    #                          ws: websockets.WebSocketClientProtocol) -> AsyncIterable[str]:
    #     try:
    #         while True:
    #             try:
    #                 msg: str = await asyncio.wait_for(ws.recv(), timeout=self.MESSAGE_TIMEOUT)
    #                 yield msg
    #             except asyncio.TimeoutError:
    #                 pong_waiter = await ws.ping()
    #                 await asyncio.wait_for(pong_waiter, timeout=self.PING_TIMEOUT)
    #     except asyncio.TimeoutError:
    #         self.logger().warning("WebSocket ping timed out . Going to reconnect...")
    #         return
    #     except ConnectionClosed:
    #         return
    #     finally:
    #         await ws.close()
    #
    # async def listen_for_order_book_diffs(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue):
    #     while True:
    #         try:
    #             trading_pairs: List[str] = await  self.get_trading_pairs()
    #             async with websockets.connect(MEXC_WS_URI_PUBLIC) as ws:
    #                 ws: websockets.WebSocketClientProtocol = ws
    #
    #                 for trading_pair in trading_pairs:
    #                     subscribe_request: Dict[str, Any] = {
    #                         "op": "sub.depth",
    #                         "symbol": trading_pair,
    #                     }
    #                     await ws.send(json.dumps(subscribe_request))
    #
    #                 async for raw_msg in self._inner_message(ws):
    #                     decoded_msg: str = raw_msg
    #
    #                     if '"channel":"push.depth"' in decoded_msg:
    #                         msg = json.loads(decoded_msg)
    #                         asks = [
    #                             {
    #                                 'price':ask['p'],
    #                                 'quantity': ask['q']
    #                             }
    #                             for ask in msg["data"]["asks"]]
    #                         bids = [
    #                             {
    #                                 'price':bid['p'],
    #                                 'quantity': bid['q']
    #                             }
    #                             for bid in msg["data"]["bids"]]
    #                         msg['data']['bids'] = asks
    #                         msg['data']['bids'] = bids
    #
    #                         order_book_message: OrderBookMessage = MexcOrderBook.diff_message_from_exchange(
    #                             msg['data'], mexc_public.microseconds(),  metadata={"trading_pair": trading_pair}
    #                         )
    #                         output.put_nowait(order_book_message)
    #                     else:
    #                         self.logger().debug(f"Unrecognized message received from MEXC websocket: {decoded_msg}")
    #         except asyncio.CancelledError:
    #             raise
    #         except Exception:
    #             self.logger().error("Unexpected error with WebSocket connection. Retrying after 30 seconds...",
    #                                 exc_info=True)
    #             await asyncio.sleep(30.0)

    async def listen_for_trades(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue):

        while True:
            try:
                trading_pairs: List[str] = self._trading_pairs
                print("trading_pairs test :",trading_pairs)
                session = aiohttp.ClientSession()
                async with session.ws_connect(MEXC_WS_URI_PUBLIC, ssl=ssl_context) as ws:
                    ws: aiohttp.client_ws.ClientWebSocketResponse = ws

                    for trading_pair in trading_pairs:
                        trading_pair = convert_to_exchange_trading_pair(trading_pair)
                        subscribe_request: Dict[str, Any] = {
                            # "method": "sub.deal",
                            # "param": {
                            #     "symbol": trading_pair
                            # }
                            "op": "sub.deal",
                            "symbol": trading_pair,
                        }
                        await ws.send_str(json.dumps(subscribe_request))

                    async for raw_msg in self._inner_messages(ws):
                        self.logger().warning("WebSocket receive_json ",raw_msg)
                        decoded_msg: dict = raw_msg

                        self.logger().debug("decode menssae:" + str(decoded_msg))

                        if 'channel' in decoded_msg.keys() and decoded_msg['channel'] == 'push.deal':
                            self.logger().debug(f"Recived new trade: {decoded_msg}")

                            for data in decoded_msg['data']['deals']:
                                # print("listen_for_trades ",data)
                                trading_pair = convert_from_exchange_trading_pair(decoded_msg['symbol'])
                                trade_message: OrderBookMessage = MexcOrderBook.trade_message_from_exchange(
                                    data, data['t'], metadata={"trading_pair": trading_pair}
                                )
                                self.logger().debug(f'Putting msg in queue: {str(trade_message)}')
                                # print("trade_message ", str(trade_message))
                                output.put_nowait(trade_message)
                        else:
                            self.logger().debug(f"Unrecognized message received from MEXC websocket: {decoded_msg}")

            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().error("Unexpected error with WebSocket connection ,Retrying after 30 seconds...",
                                    exc_info=True)
                await asyncio.sleep(30.0)
            finally:
                await session.close()

    async def _inner_messages(self,
                              ws: aiohttp.ClientWebSocketResponse) -> AsyncIterable[str]:
        try:
            while True:
                try:
                    msg: str = await asyncio.wait_for(ws.receive_json(), timeout=self.MESSAGE_TIMEOUT)
                    # self.logger().info("WebSocket msg ...",msg)
                    yield msg
                except asyncio.TimeoutError:
                    pong_waiter = ws.ping()
                    self.logger().warning("WebSocket receive_json timeout ...")
                    await asyncio.wait_for(pong_waiter, timeout=self.PING_TIMEOUT)
        except asyncio.TimeoutError:
            print("error")
            self.logger().warning("WebSocket ping timed out . Going to reconnect...")
            return
        except ConnectionClosed:
            return
        finally:
            await ws.close()

    async def listen_for_order_book_diffs(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue):
        while True:
            try:
                trading_pairs: List[str] = await self.get_trading_pairs()
                session = aiohttp.ClientSession()
                async with session.ws_connect(MEXC_WS_URI_PUBLIC, ssl=ssl_context) as ws:
                    ws: aiohttp.client_ws.ClientWebSocketResponse = ws
                    for trading_pair in trading_pairs:
                        trading_pair = convert_to_exchange_trading_pair(trading_pair)
                        subscribe_request: Dict[str, Any] = {
                            "op": "sub.depth",
                            "symbol": trading_pair,
                        }
                        await ws.send_str(json.dumps(subscribe_request))

                    async for raw_msg in self._inner_messages(ws):

                        decoded_msg: dict = raw_msg

                        if 'channel' in decoded_msg.keys() and decoded_msg['channel'] == 'push.depth':
                            if decoded_msg['data'].get('asks'):
                                asks = [
                                    {
                                        'price': ask['p'],
                                        'quantity': ask['q']
                                    }
                                    for ask in decoded_msg["data"]["asks"]]
                                decoded_msg['data']['asks'] = asks
                            if decoded_msg['data'].get('bids'):
                                bids = [
                                    {
                                        'price': bid['p'],
                                        'quantity': bid['q']
                                    }
                                    for bid in decoded_msg["data"]["bids"]]
                                decoded_msg['data']['bids'] = bids
                            order_book_message: OrderBookMessage = MexcOrderBook.diff_message_from_exchange(
                                decoded_msg['data'], mexc_public.microseconds(),
                                metadata={"trading_pair": convert_from_exchange_trading_pair(trading_pair)}
                            )
                            output.put_nowait(order_book_message)
                        else:
                            self.logger().debug(f"Unrecognized message received from MEXC websocket: {decoded_msg}")
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().error("Unexpected error with WebSocket connection. Retrying after 30 seconds...",
                                    exc_info=True)
                await asyncio.sleep(30.0)
            finally:
                await session.close()

    async def listen_for_order_book_snapshots(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue):
        while True:
            try:
                trading_pairs: List[str] = await self.get_trading_pairs()
                async with aiohttp.ClientSession() as client:
                    for trading_pair in trading_pairs:
                        try:
                            snapshot: Dict[str, Any] = await self.get_snapshot(client, trading_pair)
                            snapshot_msg: OrderBookMessage = MexcOrderBook.snapshot_message_from_exchange(
                                snapshot,
                                trading_pair,
                                timestamp=mexc_public.microseconds(),
                                metadata={"trading_pair": trading_pair})
                            output.put_nowait(snapshot_msg)
                            self.logger().debug(f"Saved order book snapshot for {trading_pair}")
                            await asyncio.sleep(5.0)
                        except asyncio.CancelledError:
                            raise
                        except Exception as ex:
                            self.logger().error("Unexpected error." + repr(ex), exc_info=True)
                            await asyncio.sleep(5.0)
                    this_hour: pd.Timestamp = pd.Timestamp.utcnow().replace(minute=0, second=0, microsecond=0)
                    next_hour: pd.Timestamp = this_hour + pd.Timedelta(hours=1)
                    delta: float = next_hour.timestamp() - time.time()
                    await asyncio.sleep(delta)
            except asyncio.CancelledError:
                raise
            except Exception as ex1:
                self.logger().error("Unexpected error." + repr(ex1), exc_info=True)
                await asyncio.sleep(5.0)
