import os
from dotenv import load_dotenv

load_dotenv()


# ==========================================================
# TELEGRAM
# ==========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

ADMIN_IDS = [
    7943742895,
    6502433991,
    8312407391
]

CHANNEL_LINK = "https://t.me/ZDealsGroup"
GROUP_LINK = "https://t.me/ZDealsStocks"
TOS_LINK = "https://your-site.com/tos"

GROUP_ID = -1003541834339
GROUP_NOTIFICATIONS = True


# ==========================================================
# VERCEL / WEBHOOK
# ==========================================================

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").rstrip("/")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

CRON_SECRET = os.getenv("CRON_SECRET", "")

WEBHOOK_PATH = "api/telegram"

DEPOSIT_CHECK_PATH = "api/deposit_check"


# ==========================================================
# REDIS
# ==========================================================

REDIS_URL = os.getenv("REDIS_URL", "")


# ==========================================================
# STOCK ALERTS
# ==========================================================

STOCK_GROUP_ID = -1003786859226

STOCK_NOTIFICATIONS = True

STOCK_ALERT_THRESHOLDS = [
    40,
    70,
    90,
]


# ==========================================================
# MYSQL / TiDB CLOUD
# ==========================================================

MYSQL_HOST = os.getenv("MYSQL_HOST", "")

MYSQL_PORT = int(
    os.getenv("MYSQL_PORT", "4000")
)

MYSQL_USER = os.getenv("MYSQL_USER", "")

MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

MYSQL_DB = os.getenv(
    "MYSQL_DB",
    "telegram_shop",
)

MYSQL_SSL_CA = os.getenv(
    "MYSQL_SSL_CA",
    "ca.pem",
)


# ==========================================================
# DEPOSIT NETWORKS
# ==========================================================

BEP20_ADDRESS = (
    "0xe0289e12f6f653b5b8364b3ef197c8d078da5eef"
)

POLYGON_ADDRESS = (
    "0xe0289e12f6f653b5b8364b3ef197c8d078da5eef"
)


# Supported deposit coins
BINANCE_DEPOSIT_COINS = [
    "USDT",
    "BUSD",
    "USDC",
]


# ==========================================================
# RPC NETWORKS
# ==========================================================
#
# RPC is used for:
#
# 1. Transaction lookup
# 2. Token transfer verification
# 3. Recipient verification
# 4. Contract verification
# 5. Block number
# 6. Confirmation calculation
# 7. Finality checking
#
# Binance is NOT used to calculate confirmations.
#
# ==========================================================

BSC_RPC_URL = os.getenv(
    "BSC_RPC_URL",
    "https://bsc-dataseed.binance.org",
)

POLYGON_RPC_URL = os.getenv(
    "POLYGON_RPC_URL",
    "https://polygon-rpc.com",
)


RPC_REQUEST_TIMEOUT = int(
    os.getenv(
        "RPC_REQUEST_TIMEOUT",
        "15",
    )
)

RPC_MAX_RETRIES = int(
    os.getenv(
        "RPC_MAX_RETRIES",
        "3",
    )
)

RPC_RETRY_DELAY = float(
    os.getenv(
        "RPC_RETRY_DELAY",
        "1.0",
    )
)


# ==========================================================
# RPC CHAIN IDs
# ==========================================================

BSC_CHAIN_ID = 56

POLYGON_CHAIN_ID = 137


# ==========================================================
# RPC BLOCK SETTINGS
# ==========================================================

BSC_BLOCK_TIME_SECONDS = 3

POLYGON_BLOCK_TIME_SECONDS = 2


# ==========================================================
# BEP20 TOKEN CONTRACTS
# ==========================================================

USDT_CONTRACT_BEP20 = (
    "0x55d398326f99059ff775485246999027b3197955"
)

BUSD_CONTRACT_BEP20 = (
    "0xe9e7cea3dedca5984780bafc599bd69add087d56"
)

USDC_CONTRACT_BEP20 = (
    "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
)


# ==========================================================
# POLYGON TOKEN CONTRACTS
# ==========================================================

USDT_CONTRACT_POLYGON = (
    "0xc2132d05d31c914a87c6611c10748aeb04b58e8f"
)

USDC_CONTRACT_POLYGON = (
    "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359"
)


# ==========================================================
# TOKEN DECIMALS
# ==========================================================

TOKEN_DECIMALS = {
    "USDT": 6,
    "USDC": 6,
    "BUSD": 18,
}


# ==========================================================
# NETWORK TOKEN CONTRACT MAP
# ==========================================================

TOKEN_CONTRACTS = {
    "BEP20": {
        "USDT": USDT_CONTRACT_BEP20,
        "BUSD": BUSD_CONTRACT_BEP20,
        "USDC": USDC_CONTRACT_BEP20,
    },

    "POLYGON": {
        "USDT": USDT_CONTRACT_POLYGON,
        "USDC": USDC_CONTRACT_POLYGON,
    },
}


# ==========================================================
# NETWORK RPC MAP
# ==========================================================

NETWORK_RPC_URLS = {
    "BEP20": BSC_RPC_URL,
    "POLYGON": POLYGON_RPC_URL,
}


# ==========================================================
# NETWORK CHAIN MAP
# ==========================================================

NETWORK_CHAIN_IDS = {
    "BEP20": BSC_CHAIN_ID,
    "POLYGON": POLYGON_CHAIN_ID,
}


# ==========================================================
# DEPOSIT ADDRESS MAP
# ==========================================================

NETWORK_DEPOSIT_ADDRESSES = {
    "BEP20": BEP20_ADDRESS,
    "POLYGON": POLYGON_ADDRESS,
}


# ==========================================================
# TOKEN CONTRACT REQUIREMENT
# ==========================================================

REQUIRE_CONTRACT_MATCH = True


# ==========================================================
# CONFIRMATIONS
# ==========================================================

# Minimum confirmations required before accepting deposit.

MIN_BLOCK_CONFIRMATIONS = 5


# Binance-side confirmation setting.
#
# This should NOT be used as the final blockchain
# confirmation source.
#
# It is kept for compatibility with existing code.

BINANCE_CONFIRMATION_MAP = {
    "BEP20": 5,
    "POLYGON": 5,
}


# Stronger finality threshold.
#
# ENABLE_FINALITY_CHECK controls whether this is required.

FINALITY_CONFIRMATIONS = {
    "BEP20": 15,
    "POLYGON": 60,
}


# ==========================================================
# BINANCE NETWORK MAP
# ==========================================================

BINANCE_NETWORK_MAP = {
    "BEP20": "BSC",
    "POLYGON": "MATIC",
}


# ==========================================================
# BINANCE API
# ==========================================================

BINANCE_API_KEY = os.getenv(
    "BINANCE_API_KEY",
    "",
)

BINANCE_API_SECRET = os.getenv(
    "BINANCE_API_SECRET",
    "",
)


# Binance Pay ID
BINANCE_PAY_ID = "1244022263"


# How far back Binance discovery should search.
BINANCE_PAY_LOOKBACK_DAYS = 7

BINANCE_DEPOSIT_LOOKBACK_DAYS = 7


# ==========================================================
# BINANCE API USAGE CONTROL
# ==========================================================
#
# Important because you have limited API usage.
#
# Binance should be used for discovery only.
#
# Once a transaction hash is obtained, all blockchain
# confirmation checks should use RPC.
#
# ==========================================================

BINANCE_DISCOVERY_ENABLED = True

BINANCE_USE_FOR_CONFIRMATIONS = False

BINANCE_USE_FOR_RPC_VERIFICATION = False


# Minimum delay between Binance discovery requests.
BINANCE_REQUEST_DELAY_SECONDS = float(
    os.getenv(
        "BINANCE_REQUEST_DELAY_SECONDS",
        "1.0",
    )
)


# Binance request timeout.
BINANCE_REQUEST_TIMEOUT = int(
    os.getenv(
        "BINANCE_REQUEST_TIMEOUT",
        "15",
    )
)


# Maximum Binance retries.
BINANCE_MAX_RETRIES = int(
    os.getenv(
        "BINANCE_MAX_RETRIES",
        "2",
    )
)


# ==========================================================
# DEPOSIT CHECKER STRATEGY
# ==========================================================

# Binance:
#
#     Find candidate transaction
#
# RPC:
#
#     Verify transaction
#     Verify contract
#     Verify recipient
#     Verify amount
#     Get block
#     Calculate confirmations
#
# ==========================================================

DEPOSIT_DISCOVERY_PROVIDER = "BINANCE"

DEPOSIT_VERIFICATION_PROVIDER = "RPC"

DEPOSIT_CONFIRMATION_PROVIDER = "RPC"


# ==========================================================
# DEPOSIT — UPI
# ==========================================================

UPI_ID = "7499899965@fam"

IMAP_HOST = "imap.gmail.com"

IMAP_EMAIL = os.getenv(
    "IMAP_EMAIL",
    "",
)

IMAP_APP_PASSWORD = os.getenv(
    "IMAP_APP_PASSWORD",
    "",
)

FAMAPP_SENDER_EMAIL = "no-reply@famapp.in"

IMAP_LOOKBACK_DAYS = 1


# ==========================================================
# DEPOSIT — AMOUNT VERIFICATION
# ==========================================================

DEPOSIT_AMOUNT_TOLERANCE = "0.01"

DEPOSIT_ALLOW_OVERPAY = True


# Maximum number of checks performed by the deposit
# verification process.

DEPOSIT_MAX_CHECK_ATTEMPTS = 60


DEPOSIT_DELETE_FAILED = False


# ==========================================================
# DEPOSIT TIME WINDOW
# ==========================================================

DEPOSIT_BEFORE_TX_GRACE_DAYS = 5

DEPOSIT_MAX_AGE_DAYS = 7


# ==========================================================
# MINIMUM DEPOSIT
# ==========================================================

MIN_DEPOSIT_USD = 0.01


# ==========================================================
# BLOCKCHAIN VERIFICATION
# ==========================================================

ENABLE_CONTRACT_CHECK = True

ENABLE_BLOCKLIST_CHECK = True

ENABLE_SENDER_BLOCKLIST = True

ENABLE_CONFIRMATION_CHECK = True

ENABLE_FINALITY_CHECK = False

ENABLE_TIMESTAMP_CHECK = True

ENABLE_VALUE_CHECK = True

ENABLE_DUST_CHECK = True


# ==========================================================
# TRANSACTION VERIFICATION
# ==========================================================

VERIFY_TRANSACTION_RECEIPT = True

VERIFY_TRANSACTION_SUCCESS = True

VERIFY_RECIPIENT_ADDRESS = True

VERIFY_TOKEN_TRANSFER_EVENT = True

VERIFY_TOKEN_CONTRACT = True

VERIFY_TRANSACTION_BLOCK = True


# ==========================================================
# BLOCK CONFIRMATION METHOD
# ==========================================================
#
# Confirmation calculation:
#
# confirmations = latest_block - tx_block + 1
#
# This is performed through RPC.
#
# ==========================================================

CONFIRMATIONS_FROM_RPC = True

CONFIRMATION_INCLUDE_TX_BLOCK = True


# ==========================================================
# RPC CONFIRMATION POLLING
# ==========================================================

RPC_CONFIRMATION_POLL_INTERVAL = int(
    os.getenv(
        "RPC_CONFIRMATION_POLL_INTERVAL",
        "5",
    )
)


RPC_CONFIRMATION_MAX_ATTEMPTS = int(
    os.getenv(
        "RPC_CONFIRMATION_MAX_ATTEMPTS",
        "60",
    )
)


# ==========================================================
# BLOCKCHAIN SAFETY
# ==========================================================

REJECT_REVERTED_TRANSACTIONS = True

REJECT_ZERO_VALUE_TRANSFERS = True

REJECT_WRONG_RECIPIENT = True

REJECT_WRONG_CONTRACT = True

REJECT_WRONG_NETWORK = True

REJECT_OLD_TRANSACTIONS = True


# ==========================================================
# BLOCKLISTS
# ==========================================================

KNOWN_FAKE_CONTRACTS = []

KNOWN_SCAM_SENDERS = []


# ==========================================================
# EXPLORER CHECK
# ==========================================================

ENABLE_EXPLORER_CHECK = True

BSCSCAN_API_KEY = os.getenv(
    "BSCSCAN_API_KEY",
    "",
)

POLYGONSCAN_API_KEY = os.getenv(
    "POLYGONSCAN_API_KEY",
    "",
)

ETHERSCAN_V2_API_KEY = os.getenv(
    "ETHERSCAN_V2_API_KEY",
    "",
)


# ==========================================================
# EXPLORER SETTINGS
# ==========================================================

BSCSCAN_BASE_URL = (
    "https://api.bscscan.com/api"
)

POLYGONSCAN_BASE_URL = (
    "https://api.polygonscan.com/api"
)

ETHERSCAN_V2_BASE_URL = (
    "https://api.etherscan.io/v2/api"
)


# ==========================================================
# EXPLORER API USAGE
# ==========================================================
#
# Explorer APIs are optional.
#
# RPC remains the primary verification source.
#
# ==========================================================

EXPLORER_FALLBACK_ONLY = True

EXPLORER_REQUEST_TIMEOUT = int(
    os.getenv(
        "EXPLORER_REQUEST_TIMEOUT",
        "10",
    )
)


# ==========================================================
# CURRENCY CONVERSION — USD / USDT → INR
# ==========================================================

CURRENCY_API_URL = (
    "https://api.currencyapi.com/v3/latest"
)


# ==========================================================
# CURRENCY API KEYS
# ==========================================================

CURRENCY_API_KEY_1 = os.getenv(
    "CURRENCY_API_KEY_1",
    "",
)

CURRENCY_API_KEY_2 = os.getenv(
    "CURRENCY_API_KEY_2",
    "",
)

CURRENCY_API_KEY_3 = os.getenv(
    "CURRENCY_API_KEY_3",
    "",
)


# ==========================================================
# AVAILABLE CURRENCY API KEYS
# ==========================================================

CURRENCY_API_KEYS = [
    key
    for key in (
        CURRENCY_API_KEY_1,
        CURRENCY_API_KEY_2,
        CURRENCY_API_KEY_3,
    )
    if key
]


# ==========================================================
# CURRENCY RATE CACHE
# ==========================================================

CURRENCY_RATE_CACHE_MINUTES = 20


# ==========================================================
# CURRENCY SETTINGS
# ==========================================================

CURRENCY_BASE_CURRENCY = "USD"

CURRENCY_TARGET_CURRENCY = "INR"

CURRENCY_REQUEST_TIMEOUT = 10


# ==========================================================
# FALLBACK CURRENCY RATE
# ==========================================================

# Emergency fallback only.

UPI_USDT_INR_RATE = 95.0


# ==========================================================
# CURRENCY API BEHAVIOR
# ==========================================================

CURRENCY_ROTATE_KEYS_ON_ERROR = True

CURRENCY_USE_CACHED_RATE_ON_ERROR = True

CURRENCY_USE_FALLBACK_RATE_ON_ERROR = True

# ==========================================================
# RESELLER API
# ==========================================================

RESELLER_API_URL = os.getenv(
    "RESELLER_API_URL",
    "https://arrsnetworkzone.in",
).rstrip("/")

RESELLER_BASE_URL = os.getenv(
    "RESELLER_BASE_URL",
    "https://arrsnetworkzone.in",
).rstrip("/")


RESELLER_API_KEY = os.getenv(
    "RESELLER_API_KEY",
    "",
)


RESELLER_API_TIMEOUT = int(
    os.getenv(
        "RESELLER_API_TIMEOUT",
        "15",
    )
)