from aiokafka import ConsumerRecord
import bz2
import logging
from sqlalchemy.engine import RowProxy
from typing import (
    Any,
    Optional,
    Dict
)
import ujson

from hummingbot.connector.exchange.mexc.mexc_order_book_message import MexcOrderBookMessage
from hummingbot.logger import HummingbotLogger
from hummingbot.core.event.events import TradeType
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_message import OrderBookMessage, OrderBookMessageType

_mexcob_logger = None

cdef class MexcOrderBook(OrderBook):
    @classmethod
    def logger(cls) -> HummingbotLogger:
        global _mexcob_logger
        if _mexcob_logger is None:
            _mexcob_logger = logging.getLogger(__name__),
            print("mexc:__name__", __name__)
        return _mexcob_logger

    @classmethod
    def snapshot_message_from_exchange(cls,
                                       msg: Dict[str, Any],
                                       trading_pair: str,
                                       timestamp: Optional[float] = None,
                                       metadata: Optional[Dict] = None) -> OrderBookMessage:
        if metadata:
            msg.update(metadata)
        msg_ts = int(timestamp * 1e-3)
        content = {
            "trading_pair": trading_pair,
            "update_id": msg_ts,
            "bids": msg["bids"],
            "asks": msg["asks"]
        }
        return MexcOrderBookMessage(OrderBookMessageType.SNAPSHOT, content, timestamp or msg_ts)

    @classmethod
    def trade_message_from_exchange(cls,
                                    msg: Dict[str, Any],
                                    timestamp: Optional[float] = None,
                                    metadata: Optional[Dict] = None) -> OrderBookMessage:
        if metadata:
            msg.update(metadata)
        msg_ts = int(timestamp * 1e-3)
        content = {
            "trading_pair": msg["trading_pair"],
            "trade_type": float(TradeType.SELL.value) if msg["T"] == 2 else float(TradeType.BUY.value),
            "trade_id": msg["t"],
            "update_id": msg["t"],
            "amount": msg["v"],
            "price": msg["p"]
        }
        return MexcOrderBookMessage(OrderBookMessageType.TRADE, content, timestamp or msg_ts)

    @classmethod
    def diff_message_from_exchange(cls,
                                   data: Dict[str, Any],
                                   timestamp: float = None,
                                   metadata: Optional[Dict] = None) -> OrderBookMessage:
        if metadata:
            data.update(metadata)

        msg_ts = int(timestamp * 1e-3)
        content = {
            "trading_pair": data["trading_pair"],
            "update_id": msg_ts,
            "bids": data.get("bids",[]),
            "asks": data.get("asks",[])
        }
        return MexcOrderBookMessage(OrderBookMessageType.DIFF, content, timestamp or msg_ts)

    @classmethod
    def snapshot_message_from_db(cls, record: RowProxy, metadata: Optional[Dict] = None) -> OrderBookMessage:
        ts = record["timestamp"]
        msg = record["json"] if type(record["json"]) == dict else ujson.loads(record["json"])
        if metadata:
            msg.update(metadata)

        return MexcOrderBookMessage(OrderBookMessageType.SNAPSHOT, {
            "trading_pair": msg["ch"].split(".")[1],
            "update_id": int(ts),
            "bids": msg["tick"]["bids"],
            "asks": msg["tick"]["asks"]
        }, timestamp=ts * 1e-3)

    @classmethod
    def diff_message_from_db(cls, record: RowProxy, metadata: Optional[Dict] = None) -> OrderBookMessage:
        ts = record["timestamp"]
        msg = record["json"] if type(record["json"]) == dict else ujson.loads(record["json"])
        if metadata:
            msg.update(metadata)
        return MexcOrderBookMessage(OrderBookMessageType.DIFF, {
            "trading_pair": msg["s"],
            "update_id": int(ts),
            "bids": msg["b"],
            "asks": msg["a"]
        }, timestamp=ts * 1e-3)

    @classmethod
    def snapshot_message_from_kafka(cls, record: ConsumerRecord, metadata: Optional[Dict] = None) -> OrderBookMessage:
        ts = record.timestamp
        msg = ujson.loads(record.value.decode())
        if metadata:
            msg.update(metadata)
        return MexcOrderBookMessage(OrderBookMessageType.SNAPSHOT, {
            "trading_pair": msg["ch"].split(".")[1],
            "update_id": ts,
            "bids": msg["tick"]["bids"],
            "asks": msg["tick"]["asks"]
        }, timestamp=ts * 1e-3)

    @classmethod
    def diff_message_from_kafka(cls, record: ConsumerRecord, metadata: Optional[Dict] = None) -> OrderBookMessage:
        decompressed = bz2.decompress(record.value)
        msg = ujson.loads(decompressed)
        ts = record.timestamp
        if metadata:
            msg.update(metadata)
        return MexcOrderBookMessage(OrderBookMessageType.DIFF, {
            "trading_pair": msg["s"],
            "update_id": ts,
            "bids": msg["bids"],
            "asks": msg["asks"]
        }, timestamp=ts * 1e-3)

    @classmethod
    def trade_message_from_db(cls, record: RowProxy, metadata: Optional[Dict] = None):
        msg = record["json"]
        ts = record.timestamp
        data = msg["tick"]["data"][0]
        if metadata:
            msg.update(metadata)
        return MexcOrderBookMessage(OrderBookMessageType.TRADE, {
            "trading_pair": msg["ch"].split(".")[1],
            "trade_type": float(TradeType.BUY.value) if data["direction"] == "sell"
            else float(TradeType.SELL.value),
            "trade_id": ts,
            "update_id": ts,
            "price": data["price"],
            "amount": data["amount"]
        }, timestamp=ts * 1e-3)

    @classmethod
    def from_snapshot(cls, msg: OrderBookMessage) -> "OrderBook":
        retval = MexcOrderBook()
        retval.apply_snapshot(msg.bids, msg.asks, msg.update_id)
        return retval
