from typing import Any, Dict, List, Optional, Tuple


def _extract_token_transfers(meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    pre_token_balances = meta.get("preTokenBalances", []) or []
    post_token_balances = meta.get("postTokenBalances", []) or []

    key = lambda b: (b.get("owner"), b.get("mint"), b.get("accountIndex"))
    pre_map = {key(b): b for b in pre_token_balances}
    post_map = {key(b): b for b in post_token_balances}

    transfers: List[Dict[str, Any]] = []
    owners = set([b.get("owner") for b in pre_token_balances] + [b.get("owner") for b in post_token_balances])
    mints = set([b.get("mint") for b in pre_token_balances] + [b.get("mint") for b in post_token_balances])

    for owner in owners:
        for mint in mints:
            pre_amount = 0
            post_amount = 0
            for m in [pre_map, post_map]:
                # sum balances for owner+mint across multiple accounts
                for (o, mi, _idx), bal in m.items():
                    if o == owner and mi == mint:
                        ui_amt = bal.get("uiTokenAmount", {})
                        # Fallback to amount if uiAmount not available
                        if ui_amt and ui_amt.get("uiAmount") is not None:
                            amount = float(ui_amt.get("uiAmount"))
                        else:
                            # uiTokenAmount may not include uiAmount for native SOL wrappers, but token balances should
                            amount = float(ui_amt.get("amount", 0)) / (10 ** int(ui_amt.get("decimals", 0))) if ui_amt else 0.0
                        if m is pre_map:
                            pre_amount += amount
                        else:
                            post_amount += amount
            delta = post_amount - pre_amount
            if abs(delta) > 0:
                transfers.append({"owner": owner, "mint": mint, "delta": delta})
    return transfers


def classify_event(
    tx: Dict[str, Any],
    primary_wallet: str,
    secondary_wallet: str,
    bullieve_mint: str,
    incinerator: str,
) -> Tuple[str, Dict[str, Any]]:
    """Return (event_type, details)

    event_type in {"fee_income", "transfer_to_secondary", "burn", "other"}
    """
    meta = tx.get("meta") or {}
    if meta.get("err") is not None:
        return "other", {"reason": "tx_error"}

    transfers = _extract_token_transfers(meta)

    # Helper: detect explicit SPL Token burn instructions (jsonParsed)
    def _detect_parsed_burn_amount() -> float:
        amount_burned = 0.0
        try:
            message = (tx.get("transaction") or {}).get("message") or {}
            instrs = message.get("instructions", []) or []
            # Also check inner instructions
            inner = meta.get("innerInstructions", []) or []
            inner_instrs: List = []
            for entry in inner:
                inner_instrs.extend(entry.get("instructions", []) or [])

            def _accumulate(instr_list: List) -> None:
                nonlocal amount_burned
                for ins in instr_list:
                    parsed = ins.get("parsed") if isinstance(ins, dict) else None
                    if not parsed:
                        continue
                    if parsed.get("type") == "burn":
                        info = parsed.get("info", {})
                        if info.get("mint") == bullieve_mint:
                            amt = info.get("amount")
                            try:
                                amount_burned += float(amt) if isinstance(amt, (int, float)) else float(str(amt))
                            except Exception:
                                # fall back to 0; we will rely on balances heuristic instead
                                pass

            _accumulate(instrs)
            _accumulate(inner_instrs)
        except Exception:
            pass
        return amount_burned

    # Also include SOL (lamports) deltas per owner using accountKeys + pre/postBalances
    try:
        message = (tx.get("transaction") or {}).get("message") or {}
        account_keys_raw = message.get("accountKeys", []) or []
        account_keys: List[str] = []
        for k in account_keys_raw:
            if isinstance(k, dict) and "pubkey" in k:
                account_keys.append(k.get("pubkey"))
            else:
                account_keys.append(str(k))

        pre_balances = meta.get("preBalances", []) or []
        post_balances = meta.get("postBalances", []) or []
        # Map owner address to SOL delta (in SOL units)
        sol_delta_map: Dict[str, float] = {}
        for idx, addr in enumerate(account_keys):
            try:
                pre_lamports = int(pre_balances[idx]) if idx < len(pre_balances) else 0
                post_lamports = int(post_balances[idx]) if idx < len(post_balances) else 0
                delta_sol = (post_lamports - pre_lamports) / 1_000_000_000.0
                if abs(delta_sol) > 0:
                    sol_delta_map[addr] = sol_delta_map.get(addr, 0.0) + delta_sol
            except Exception:
                continue
        for owner, delta in sol_delta_map.items():
            transfers.append({"owner": owner, "mint": "SOL", "delta": delta})
    except Exception:
        # ignore SOL extraction failures
        pass

    # burn detection (SPL Token burn reduces supply; not a transfer)
    parsed_burn_amt = _detect_parsed_burn_amount()
    if parsed_burn_amt > 0:
        # If parsed shows raw token units, balances heuristic below will still capture uiAmount; prefer balances if available
        mint_transfers = [t for t in transfers if t.get("mint") == bullieve_mint]
        if mint_transfers:
            sum_delta = sum(t.get("delta", 0.0) for t in mint_transfers)
            if sum_delta < 0:
                return "burn", {"mint": bullieve_mint, "amount": abs(sum_delta)}
        return "burn", {"mint": bullieve_mint, "amount": parsed_burn_amt}

    # Heuristic burn: for the mint, total delta across all owners is negative and no positive receiver
    mint_transfers = [t for t in transfers if t.get("mint") == bullieve_mint]
    if mint_transfers:
        sum_delta = sum(t.get("delta", 0.0) for t in mint_transfers)
        any_positive = any(t.get("delta", 0.0) > 0 for t in mint_transfers)
        if sum_delta < 0 and not any_positive:
            return "burn", {"mint": bullieve_mint, "amount": abs(sum_delta)}

    # transfer to secondary: SOL or token outflow from primary and inflow to secondary
    # We detect by postBalances delta for SOL, and tokenBalances delta for tokens.
    sec_inflows = [t for t in transfers if t.get("owner") == secondary_wallet and t.get("delta", 0) > 0]
    prim_outflows = [t for t in transfers if t.get("owner") == primary_wallet and t.get("delta", 0) < 0]
    if sec_inflows and prim_outflows:
        return "transfer_to_secondary", {"details": {"primary_out": prim_outflows, "secondary_in": sec_inflows}}

    # fee income: small inflow to primary of Bullieve mint or swap-quote mint
    prim_inflows = [t for t in transfers if t.get("owner") == primary_wallet and t.get("delta", 0) > 0]
    if prim_inflows:
        # Pick the top inflow as representative
        top = max(prim_inflows, key=lambda x: x["delta"])
        return "fee_income", {"mint": top["mint"], "amount": top["delta"]}

    return "other", {"transfers": transfers}


class TransactionParser:
    def __init__(self, primary_wallet: str, secondary_wallet: str, bullieve_mint: str, incinerator: str):
        self.primary_wallet = primary_wallet
        self.secondary_wallet = secondary_wallet
        self.bullieve_mint = bullieve_mint
        self.incinerator = incinerator

    def parse_transaction(self, tx_data: Dict[str, Any], wallet_address: str, wallet_name: str) -> Optional[Dict[str, Any]]:
        """Parse a transaction and return event details if relevant"""
        event_type, details = classify_event(
            tx_data,
            self.primary_wallet,
            self.secondary_wallet,
            self.bullieve_mint,
            self.incinerator
        )
        
        if event_type == "fee_income" and wallet_name == "primary":
            return {
                "type": "fee",
                "amount": details["amount"],
                "mint": details["mint"],
                "symbol": details["mint"] if details["mint"] == "SOL" else "Unknown"
            }
        elif event_type == "burn" and wallet_name == "secondary":
            return {
                "type": "burn",
                "amount": details["amount"],
                "mint": details["mint"],
                "symbol": "BULLIEVE"
            }
        
        return None


