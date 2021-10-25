from urllib.parse import urljoin

# URLs

MEXC_BASE_URL = "https://www.mexc.com"

MEXC_SYMBOL_URL = urljoin(MEXC_BASE_URL, '/open/api/v2/market/symbols')
MEXC_TICKERS_URL = urljoin(MEXC_BASE_URL, '/open/api/v2/market/ticker')
MEXC_DEPTH_URL = urljoin(MEXC_BASE_URL,
                         '/open/api/v2/market/depth?symbol={trading_pair}&sz=200')  # Size=200 by default?
MEXC_PRICE_URL = urljoin(MEXC_BASE_URL, '/open/api/v2/market/ticker?symbol={trading_pair}')
MEXC_PING_URL = '/open/api/v2/common/ping'
# Doesn't include base URL as the tail is required to generate the signature


# Auth required

MEXC_PLACE_ORDER = "/open/api/v2/order/place"
MEXC_ORDER_DETAILS_URL = '/open/api/v2/order/query'
MEXC_ORDER_CANCEL = '/open/api/v2/order/cancel'
MEXC_BATCH_ORDER_CANCEL = '/open/api/v2/order/cancel'
MEXC_BALANCE_URL = '/open/api/v2/account/info'

# WS
MEXC_WS_URI_PUBLIC = "wss://wbs.mxc.co/raw/ws"
MEXC_WS_URI_PRIVATE = "wss://ws.okex.com:8443/ws/v5/private"

MEXC_WS_CHANNEL_ACCOUNT = "account"
MEXC_WS_CHANNEL_ORDERS = "orders"

MEXC_WS_CHANNELS = {
    MEXC_WS_CHANNEL_ACCOUNT,
    MEXC_WS_CHANNEL_ORDERS
}
