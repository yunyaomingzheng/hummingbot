#!/usr/bin/env python
import asyncio
import hashlib
import json
from urllib.parse import urlencode

import aiohttp
import aiohttp.client_ws

import logging

from typing import (
    Optional,
    AsyncIterable,
    List,
    Dict,
    Any
)

from hummingbot.connector.exchange.mexc.constants import MEXC_WS_URL_PUBLIC
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.logger import HummingbotLogger
from hummingbot.connector.exchange.mexc.mexc_auth import MexcAuth

import time



from websockets.exceptions import ConnectionClosed
import ssl
ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)


class MexcAPIUserStreamDataSource(UserStreamTrackerDataSource):
    _mexcausds_logger: Optional[HummingbotLogger] = None
    MESSAGE_TIMEOUT = 300.0
    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._mexcausds_logger is None:
            cls._mexcausds_logger = logging.getLogger(__name__)

        return cls._mexcausds_logger

    def __init__(self, mexc_auth: MexcAuth, trading_pairs: Optional[List[str]] = []):
        self._current_listen_key = None
        self._current_endpoint = None
        self._listen_for_user_stram_task = None
        self._last_recv_time: float = 0
        self._auth: MexcAuth = mexc_auth
        self._trading_pairs = trading_pairs
        super().__init__()

    @property
    def last_recv_time(self) -> float:
        return self._last_recv_time

    async def _authenticate_client(self):
        pass
        # """
        # Sends an Authentication request to Mexc's WebSocket API Server
        # """
        # await self._websocket_connection.send(json.dumps(self._auth.generate_ws_auth()))
        #
        # resp = await self._websocket_connection.recv()
        # msg = json.loads(resp)
        #
        # if msg["event"] != 'login':
        #     self.logger().error(f"Error occurred authenticating to websocket API server. {msg}")
        #
        # self.logger().info("Successfully authenticated")

    # async  def listen_for_user_stream(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue):
    #     while True:
    #         try:
    #             await self._api_request(method="GET", path_url=MEXC_PING_URL)
    #             self._last_recv_time = time.time()
    #             await asyncio.sleep(8.0)
    #         except asyncio.CancelledError:
    #             raise
    #         except Exception as ex:
    #             self.logger().error(f"Unexpected error occurred! {ex}", exc_info=True)

    async def listen_for_user_stream(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue):
        while True:
            try:
                print("listen_for_user_stream1", "wbsocket monitor")
                session = aiohttp.ClientSession()
                async with session.ws_connect(MEXC_WS_URL_PUBLIC, ssl=ssl_context) as ws:
                    ws: aiohttp.client_ws.ClientWebSocketResponse = ws

                    params: Dict[str, Any] = {
                        'api_key': self._auth.api_key,
                        "op": "sub.personal",
                        'req_time': int(time.time() * 1000),
                        "api_secret": self._auth.secret_key,
                    }
                    print("listen_for_user_stream", "wbsocket monitor")
                    params_sign = urlencode(params)
                    sign_data = hashlib.md5(params_sign.encode()).hexdigest()
                    del params['api_secret']
                    params["sign"] = sign_data

                    await ws.send_str(json.dumps(params))

                    async for raw_msg in self._inner_messages(ws):
                        self._last_recv_time = time.time()
                        # print("WebSocket receive_json ",raw_msg)
                        decoded_msg: dict = raw_msg
                        # print("WS订单信息", decoded_msg)
                        if 'channel' in decoded_msg.keys() and decoded_msg['channel'] == 'push.personal.order':
                            # trading_pair = convert_from_exchange_trading_pair(decoded_msg['symbol'])
                            # trade_message: OrderBookMessage = MexcOrderBook.trade_message_from_exchange(
                            #     data, data['t'], metadata={"trading_pair": trading_pair}
                            # )
                            # self.logger().debug(f'Putting msg in queue: {str(trade_message)}')
                            # print("trade_message ", str(trade_message))
                            output.put_nowait(decoded_msg)
                        elif 'channel' in decoded_msg.keys() and decoded_msg['channel'] == 'sub.personal':
                            pass
                        else:
                            self.logger().debug(f"other message received from MEXC websocket: {decoded_msg}")

            except asyncio.CancelledError:
                raise
            except Exception as ex:
                self.logger().error("Unexpected error with WebSocket connection ,Retrying after 30 seconds..." + str(ex),
                                    exc_info=True)
                await asyncio.sleep(30.0)
            finally:
                await session.close()

    async def _inner_messages(self,
                              ws: aiohttp.ClientWebSocketResponse) -> AsyncIterable[str]:
        try:
            while True:
                msg: str = await asyncio.wait_for(ws.receive_json(), timeout=self.MESSAGE_TIMEOUT)
                # self.logger().info("WebSocket msg ...",msg)
                yield msg
        except asyncio.TimeoutError:
            return
        except ConnectionClosed:
            return
        finally:
            await ws.close()

    # async def listen_for_user_stream(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue):
    #     """
    #     *required
    #     Subscribe to user stream via web socket, and keep the connection open for incoming messages
    #     :param ev_loop: ev_loop to execute this function in
    #     :param output: an async queue where the incoming messages are stored
    #     """
    #     while True:
    #         try:
    #             async with websockets.connect(constants.BAEE_WS_URL) as ws:
    #                 ws: websockets.WebSocketClientProtocol = ws
    #                 ev_loop.create_task(self.custom_ping(ws))
    #
    #                 # Send a auth request first
    #                 auth_request: Dict[str, Any] = {
    #                     "event": constants.WS_AUTH_REQUEST_EVENT,
    #                     "data": self._liquid_auth.get_ws_auth_data()
    #                 }
    #                 await ws.send(ujson.dumps(auth_request))
    #
    #                 quoted_currencies = [
    #                     trading_pair.split('-')[1]
    #                     for trading_pair in self._trading_pairs
    #                 ]
    #
    #                 for trading_pair, quoted_currency in zip(self._trading_pairs, quoted_currencies):
    #                     subscribe_request: Dict[str, Any] = {
    #                         "event": Constants.WS_PUSHER_SUBSCRIBE_EVENT,
    #                         "data": {
    #                             "channel": Constants.WS_USER_ACCOUNTS_SUBSCRIPTION.format(
    #                                 quoted_currency=quoted_currency.lower()
    #                             )
    #                         }
    #                     }
    #                     await ws.send(ujson.dumps(subscribe_request))
    #                 async for raw_msg in self._inner_messages(ws):
    #                     diff_msg = ujson.loads(raw_msg)
    #
    #                     event_type = diff_msg.get('event', None)
    #                     if event_type == 'updated':
    #                         output.put_nowait(diff_msg)
    #                         self._last_recv_time = time.time()
    #                     elif event_type == "pusher:pong":
    #                         self._last_recv_time = time.time()
    #                     elif not event_type:
    #                         raise ValueError(f"Liquid Websocket message does not contain an event type - {diff_msg}")
    #         except asyncio.CancelledError:
    #             raise
    #         except Exception:
    #             self.logger().error("Unexpected error with Liquid WebSocket connection. "
    #                                 "Retrying after 30 seconds...", exc_info=True)
    #             await asyncio.sleep(30.0)
    #
    # async def _inner_messages(self,
    #                           ws: websockets.WebSocketClientProtocol) -> AsyncIterable[str]:
    #     """
    #     Generator function that returns messages from the web socket stream
    #     :param ws: current web socket connection
    #     :returns: message in AsyncIterable format
    #     """
    #     # Terminate the recv() loop as soon as the next message timed out, so the outer loop can reconnect.
    #     try:
    #         while True:
    #             msg: str = await asyncio.wait_for(ws.recv(), timeout=Constants.MESSAGE_TIMEOUT)
    #             yield msg
    #     except asyncio.TimeoutError:
    #         self.logger().warning("WebSocket message timed out. Going to reconnect...")
    #         return
    #     except ConnectionClosed:
    #         return
    #     finally:
    #         await ws.close()
    #
    # async def custom_ping(self, ws: websockets.WebSocketClientProtocol):
    #     """
    #     Sends a ping meassage to the Liquid websocket
    #     :param ws: current web socket connection
    #     """
    #
    #     ping_data: Dict[str, Any] = {"event": "pusher:ping", "data": {}}
    #     try:
    #         while True:
    #             await ws.send(ujson.dumps(ping_data))
    #             await asyncio.sleep(60.0)
    #     except Exception:
    #         return
