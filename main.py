import asyncio
import os
import sys
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

sys.path.append(str(Path(__file__).parent))

from tg_solana_bot.config import load_settings
from tg_solana_bot.solana_client import SolanaClient
from tg_solana_bot.tx_parser import TransactionParser
from tg_solana_bot.notifier import TelegramNotifier
from tg_solana_bot.state import StateStore
from dotenv import load_dotenv
from tg_solana_bot.price_client import PriceClient
from tg_solana_bot.manual_price_store import ManualPriceStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

price_client: PriceClient

def _fmt_amount(val: float, max_decimals: int = 9) -> str:
    s = f"{val:.{max_decimals}f}".rstrip("0").rstrip(".")
    if s.startswith("."):
        s = "0" + s
    if s == "-0":
        s = "0"
    return s

async def process_single_address(
    client: SolanaClient,
    notifier: TelegramNotifier,
    state: StateStore,
    addr: str,
    wallet: str,
    settings,
    tx_parser: TransactionParser,
    wallet_type: str = "primary",  # Add wallet_type parameter
) -> None:
    try:
        last_sig = state.load_last_signature(addr)
        
        # Optimized: Check only the latest signature first
        latest_sig_response = await client.get_signatures_for_address(addr, before=None, limit=1)
        if not latest_sig_response:
            return
            
        latest_sig = latest_sig_response[0].get("signature")
        
        # If no stored signature, initialize
        if last_sig is None:
            logger.info(f"[init] addr={addr} initialize last_sig to {latest_sig} (skip history)")
            state.save_last_signature(addr, latest_sig)
            return
            
        # If latest signature is the same as stored, no new transactions
        if latest_sig == last_sig:
            return
            
        # If different, fetch more signatures until we find the stored one
        signatures = await client.get_signatures_for_address(addr, before=None, limit=5)
        
        new_sigs: List[str] = []
        for entry in signatures:
            sig = entry.get("signature")
            if sig == last_sig:
                break
            new_sigs.append(sig)

        if not new_sigs:
            return

        logger.info(f"[poll] addr={addr} new_sigs={len(new_sigs)}")
    except Exception as exc:
        logger.error(f"[error] get_signatures_for_address failed addr={addr}: {exc}")
        return

    for sig in reversed(new_sigs):
        try:
            tx = await client.get_transaction(sig)
        except Exception as exc:
            logger.error(f"[error] get_transaction failed signature={sig}: {exc}")
            continue
        if not tx:
            continue

        event = tx_parser.parse_transaction(tx, wallet, wallet_type)  # Use wallet_type instead of "primary"
        if event:
            event_type = event.get("type")
            details = event
        else:
            event_type = "other"
            details = {}
        
        logger.info(f"[event] owner={wallet} via={addr} sig={sig} type={event_type} details={details}")

        if event and event.get("type") == "fee":
            logger.info(f"[FEE DETECTED] wallet={wallet} amount={event.get('amount')} mint={event.get('mint')}")
            mint = event.get("mint", "")
            amount = float(event.get("amount", 0))
            symbol = event.get("symbol", mint)
            signer = client.get_first_signer_address(tx) or "unknown"
            
            if mint == "So11111111111111111111111111111111111111112":
                symbol = "SOL"
            elif mint == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v":
                symbol = "USDC"
            elif mint == "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB":
                symbol = "USDT"
            elif mint == "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn":
                symbol = "PUMP"
            elif mint == "63LfDmNb3MQ8mw9MtZ2To9bEA2M71kZUUGq5tiJxcqj9":
                symbol = "GIGA"
            elif mint == "A8C3xuqscfmyLrte3VmTqrAq8kgMASius9AFNANwpump":
                symbol = "FWOG"
            elif mint == "6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN":
                symbol = "TRUMP"
            elif mint == "2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv":
                symbol = "PENGU"
            elif mint == "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump":
                symbol = "FARTCOIN"
            elif mint == "J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr":
                symbol = "SPX"
            elif mint == "26VfKb7jjtdEdvfovoBijScoZmJbWWasFZkgfUD5w7cy":
                symbol = "MOG"
            elif mint == "21AErpiB8uSb94oQKRcwuHqyHF93njAxBSbdUrpupump":
                symbol = "WIF"
            elif mint == "HdzMjvQvFP9nxp1X2NbHFptZK1G6ASsyRcxNdn65ABxi":
                symbol = "BULLIEVE"
            elif mint == "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr":
                symbol="POPCAT"
            elif mint == "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263":
                symbol="BONK"

            usd = None
            if amount and symbol:
                usd_price = await price_client.get_usd_price(symbol)
                if usd_price:
                    usd = amount * usd_price
            amt_txt = _fmt_amount(amount, 9)
            
            caption = (
                "NEW BULLIEVE-SWAP COMPLETED! 💰\n\n"
                f"FEES COLLECTED: {amt_txt} {symbol}"
            )
            if usd is not None:
                caption += f" (~${usd:,.2f})"
            caption += (
                "\n\n🔥 Let's burn more: bullieve.com 🔥"
            )

            try:
                await notifier.send_media("/app/media/alert.jpg", caption=caption, media_type="photo")
            except Exception as exc:
                logger.error(f"[error] telegram send fee_income failed: {exc}")
        elif event and event.get("type") == "burn":
            logger.info(f"[BURN DETECTED] wallet={wallet} amount={event.get('amount')} mint={event.get('mint')}")
            amount = float(event.get("amount", 0))
            symbol = "BULLIEVE"
            usd = None
            try:
                usd_price = await price_client.get_usd_price(symbol) or await price_client.get_usd_price(
                    settings.bullieve_mint_address
                )
                if usd_price:
                    usd = amount * usd_price
            except Exception as exc:
                logger.warning(f"Could not get USD price for burn: {exc}")
                usd = None
            amt_txt = _fmt_amount(amount, 9)
            
            caption = (
                "BULLIEVE BURN! 🔥\n\n"
                f"AMOUNT BURNED: {amt_txt} {symbol}"
            )
            if usd is not None:
                caption += f" (~${usd:,.2f})"
            caption += "\n\n🔥 Let's burnnnnn 🔥"

            try:
                await notifier.send_media("/app/media/alert.jpg", caption=caption, media_type="photo")
            except Exception as exc:
                logger.error(f"[error] telegram send burn failed: {exc}")
        else:
            logger.debug(f"[NO EVENT] wallet={wallet} event_type={event_type}")

        state.save_last_signature(addr, new_sigs[0])

async def process_wallet_and_token_accounts(
    client: SolanaClient,
    notifier: TelegramNotifier,
    state: StateStore,
    wallet: str,
    settings,
    wallet_type: str = "primary",  # Add wallet_type parameter
) -> None:
    try:
        token_accounts = await client.get_token_accounts_by_owner(wallet)
    except Exception as exc:
        logger.error(f"[error] get_token_accounts_by_owner failed for {wallet}: {exc}")
        token_accounts = []

    addresses: List[str] = [wallet] + token_accounts
    logger.info(f"[poll] owner={wallet} addresses={len(addresses)} (wallet + token accounts)")

    tx_parser = TransactionParser(
        settings.primary_wallet_address,
        settings.secondary_wallet_address,
        settings.bullieve_mint_address,
        settings.burn_incinerator_address,
    )

    semaphore = asyncio.Semaphore(5)
    
    async def process_with_semaphore(addr: str):
        async with semaphore:
            await process_single_address(client, notifier, state, addr, wallet, settings, tx_parser, wallet_type)  # Pass wallet_type
    
    tasks = [process_with_semaphore(addr) for addr in addresses]
    await asyncio.gather(*tasks, return_exceptions=True)

async def main() -> None:
    if os.path.exists(".env"):
        load_dotenv(".env")
    settings = load_settings()
    logger.info(
        f"[start] polling every {settings.poll_interval_seconds}s on primary={settings.primary_wallet_address} secondary={settings.secondary_wallet_address}"
    )
    client = SolanaClient(settings.solana_rpc_url, settings.solana_alt_rpc_url)
    global price_client
    manual_store = ManualPriceStore(settings.manual_price_file_path)
    price_client = PriceClient(manual_store)
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id, settings.telegram_chat_ids)
    state = StateStore(settings.state_file_path)
    try:
        while True:
            try:
                manual_store.refresh()
            except Exception as exc:
                logger.error(f"Failed to refresh manual prices: {exc}")
                pass
            await process_wallet_and_token_accounts(client, notifier, state, settings.primary_wallet_address, settings, "primary")
            await process_wallet_and_token_accounts(client, notifier, state, settings.secondary_wallet_address, settings, "secondary")
            await asyncio.sleep(settings.poll_interval_seconds)
    finally:
        await notifier.close()
        await client.close()
        await price_client.close()

if __name__ == "__main__":
    asyncio.run(main())
