#!/usr/bin/env python
import json

import aiohttp
import asyncio
import logging

import hummingbot.connector.exchange.mexc.mexc_constants as CONSTANTS
import hummingbot.connector.exchange.mexc.mexc_utils as mexc_utils

from typing import Dict, Optional, AsyncIterable, Any, List

from hummingbot.connector.exchange.mexc.mexc_auth import MexcAuth
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.utils.tracking_nonce import get_tracking_nonce
from hummingbot.logger import HummingbotLogger


class MexcWebSocketAdaptor:

    AUTH_REQUEST = "public/auth"
    PING_METHOD = "public/heartbeat"
    PONG_METHOD = "public/respond-heartbeat"
    HEARTBEAT_INTERVAL = 15.0
    ONE_SEC_DELAY = 1.0

    DEAL_CHANNEL_ID = "push.deal"
    DEPTH_CHANNEL_ID = "push.depth"
    SUBSCRIPTION_LIST = set([DEAL_CHANNEL_ID, DEPTH_CHANNEL_ID])

    _ID_FIELD_NAME = "id"
    _METHOD_FIELD_NAME = "method"
    _NONCE_FIELD_NAME = "nonce"
    _PARAMS_FIELD_NAME = "params"
    _SIGNATURE_FIELD_NAME = "sig"
    _API_KEY_FIELD_NAME = "api_key"

    _SUBSCRIPTION_OPERATION = "subscribe"
    _CHANNEL_PARAMS = "channels"
    _USER_CHANNEL_LIST = ["user.order", "user.trade", "user.balance"]

    _logger: Optional[HummingbotLogger] = None

    """
    Auxiliary class that works as a wrapper of a low level web socket. It contains the logic to create messages
    with the format expected by Crypto.com API
    """

    MESSAGE_TIMEOUT = 120.0
    PING_TIMEOUT = 10.0

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    def __init__(
            self,
            throttler: AsyncThrottler,
            auth: Optional[MexcAuth] = None,
            shared_client: Optional[aiohttp.ClientSession] = None,
    ):

        self._auth: Optional[MexcAuth] = auth
        self._is_private = True if self._auth is not None else False
        self._WS_URL = CONSTANTS.MEXC_WS_URL_PUBLIC
        self._shared_client = shared_client
        self._websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self._throttler = throttler

    def get_shared_client(self) -> aiohttp.ClientSession:
        if not self._shared_client:
            self._shared_client = aiohttp.ClientSession()
        return self._shared_client

    async def _sleep(self, delay: float = 1.0):
        await asyncio.sleep(delay)

    async def send_request(self, payload: Dict[str, Any]):
        await self._websocket.send_json(payload)

    async def send_request_str(self, payload: Dict[str, Any]):
        await self._websocket.send_str(payload)

    async def subscribe_to_order_book_streams(self, trading_pairs: List[str]):
        try:
            for trading_pair in trading_pairs:
                trading_pair = mexc_utils.convert_to_exchange_trading_pair(trading_pair)
                subscribe_deal_request: Dict[str, Any] = {
                    "op": "sub.deal",
                    "symbol": trading_pair,
                }
                async with self._throttler.execute_task(CONSTANTS.MEXC_WS_URL_PUBLIC):
                    await self.send_request_str(json.dumps(subscribe_deal_request))
                subscribe_depth_request: Dict[str, Any] = {
                    "op": "sub.depth",
                    "symbol": trading_pair,
                }
                async with self._throttler.execute_task(CONSTANTS.MEXC_WS_URL_PUBLIC):
                    await self.send_request_str(json.dumps(subscribe_depth_request))

        except asyncio.CancelledError:
            raise
        except Exception:
            self.logger().error(
                "Unexpected error occurred subscribing to order book trading and delta streams...", exc_info=True
            )
            raise

    async def subscribe_to_user_streams(self):
        try:
            channels = self._USER_CHANNEL_LIST
            subscription_payload = {
                self._ID_FIELD_NAME: get_tracking_nonce(),
                self._METHOD_FIELD_NAME: self._SUBSCRIPTION_OPERATION,
                self._PARAMS_FIELD_NAME: {self._CHANNEL_PARAMS: channels},
            }
            await self.send_request(subscription_payload)

            self.logger().info("Successfully subscribed to user stream...")

        except asyncio.CancelledError:
            raise
        except Exception:
            self.logger().error("Unexpected error occurred subscribing to user streams...", exc_info=True)
            raise

    async def authenticate(self):
        pass
        # request_id = get_tracking_nonce()
        # nonce = get_ms_timestamp()
        #
        # auth = self._auth.generate_auth_dict(
        #     self.AUTH_REQUEST,
        #     request_id=request_id,
        #     nonce=nonce,
        # )
        # auth_payload = {
        #     self._ID_FIELD_NAME: request_id,
        #     self._METHOD_FIELD_NAME: self.AUTH_REQUEST,
        #     self._NONCE_FIELD_NAME: nonce,
        #     self._SIGNATURE_FIELD_NAME: auth["sig"],
        #     self._API_KEY_FIELD_NAME: auth["api_key"],
        # }
        # await self.send_request(auth_payload)

    async def connect(self):
        try:
            self._websocket = await self.get_shared_client().ws_connect(
                url=self._WS_URL, ssl_context=mexc_utils.ssl_context, proxy='http://127.0.0.1:1087')

            # According to Crypto.com API documentation, it is recommended to add a 1 second delay from when the
            # websocket connection is established and when the first request is sent.
            # Ref: https://exchange-docs.crypto.com/spot/index.html#rate-limits
            # await self._sleep(self.ONE_SEC_DELAY)

            # if auth class was passed into websocket class
            # we need to emit authenticated requests
            # if self._is_private:
            #     await self.authenticate()
            #     self.logger().info("Successfully authenticate to user stream...")

        except Exception as e:
            self.logger().error(f"Websocket error: '{str(e)}'", exc_info=True)
            raise

    # disconnect from exchange
    async def disconnect(self):
        print("websocket调用结束")
        if self._websocket is None:
            return
        await self._websocket.close()

    async def iter_messages(self) -> AsyncIterable[Any]:
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(self._websocket.receive_json(), timeout=self.MESSAGE_TIMEOUT)
                    if msg is None:
                        self.logger().info(f"msg is None.")
                        continue
                    yield msg
                except asyncio.TimeoutError:
                    pong_waiter = self._websocket.ping()
                    self.logger().warning("WebSocket receive_json timeout ...")
                    await asyncio.wait_for(pong_waiter, timeout=self.PING_TIMEOUT)
        except ConnectionError:
            return
        # finally:
            # print("调用websocket关闭2")
            # await self.disconnect()
