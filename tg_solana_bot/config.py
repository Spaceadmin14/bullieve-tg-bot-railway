import os
from dataclasses import dataclass
from typing import List


def _get_env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value.strip()


@dataclass
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_chat_ids: List[str]
    solana_rpc_url: str
    solana_alt_rpc_url: str
    manual_price_file_path: str
    primary_wallet_address: str
    secondary_wallet_address: str
    bullieve_mint_address: str
    burn_incinerator_address: str
    poll_interval_seconds: int
    state_file_path: str
    notify_fee_media_url: str
    notify_burn_media_url: str


def load_settings() -> Settings:
    chat_id = _get_env("TELEGRAM_CHAT_ID")
    chat_ids_env = _get_env("TELEGRAM_CHAT_IDS")
    chat_ids: List[str] = []
    if chat_ids_env:
        chat_ids = [c.strip() for c in chat_ids_env.split(",") if c.strip()]
    elif chat_id:
        chat_ids = [chat_id]

    return Settings(
        telegram_bot_token=_get_env("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=chat_id,
        telegram_chat_ids=chat_ids,
        solana_rpc_url=_get_env("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
        solana_alt_rpc_url=_get_env("SOLANA_ALT_RPC_URL", ""),
        manual_price_file_path=_get_env("MANUAL_PRICE_FILE_PATH", "/data/manual_prices.json"),
        primary_wallet_address=_get_env(
            "PRIMARY_WALLET_ADDRESS",
            "6674vbB9LRJKymhEz9DxxJc5HyXbCsSVFh1jGuL7xM6B",
        ),
        secondary_wallet_address=_get_env(
            "SECONDARY_WALLET_ADDRESS",
            "5aYBTU9x6F8qmytdmAiLcRQyPEVjBiGN2tHArFbop8V5",
        ),
        bullieve_mint_address=_get_env("BULLIEVE_MINT_ADDRESS"),
        burn_incinerator_address=_get_env(
            "BURN_INCINERATOR_ADDRESS",
            "1nc1nerator11111111111111111111111111111111",
        ),
        poll_interval_seconds=int(_get_env("POLL_INTERVAL_SECONDS", "15")),
        state_file_path=_get_env("STATE_FILE_PATH", os.path.join("tg_solana_bot", "state.json")),
        notify_fee_media_url=_get_env("NOTIFY_FEE_MEDIA_URL"),
        notify_burn_media_url=_get_env("NOTIFY_BURN_MEDIA_URL"),
    )


