import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone

st.set_page_config(page_title="Solana Meme Coin Auditor", layout="centered")
st.title("🛡️ Solana Meme Coin Fraud Detector")
st.write("Pulls live pair data from DexScreener and runs a rule-based safety scan.")

target_ca = st.text_input(
    "Paste Token Contract Address (CA):",
    placeholder="e.g., EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
)


def clean_address(raw: str) -> str:
    """Strip anything that isn't the raw address (accidental URLs, spaces, slashes)."""
    addr = raw.strip()
    for junk in ["https://", "http://", "dexscreener.com", "gmgn.ai", " "]:
        addr = addr.replace(junk, "")
    return addr.strip("/")


if st.button("Run Forensic Audit"):
    if not target_ca:
        st.warning("Please enter a valid contract address.")
    else:
        clean_ca = clean_address(target_ca)

        # Correct DexScreener endpoint: api.dexscreener.com (not dexscreener.com),
        # path /latest/dex/search, address passed as a query param.
        api_url = "https://api.dexscreener.com/latest/dex/search"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        }
        params = {"q": clean_ca}

        with st.spinner("Fetching live pair data..."):
            try:
                response = requests.get(api_url, headers=headers, params=params, timeout=10)
                data = response.json() if response.status_code == 200 else {}
                pairs = data.get("pairs") or []

                # Prefer a Solana pair if the search matched multiple chains
                solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                candidates = solana_pairs if solana_pairs else pairs
                candidates = sorted(
                    candidates,
                    key=lambda p: (p.get("liquidity") or {}).get("usd", 0) or 0,
                    reverse=True,
                )

                if not candidates:
                    st.error(
                        "No trading pair found for this address on DexScreener. "
                        "Double-check the CA, or the token may be too new to be indexed yet."
                    )
                else:
                    pair_data = candidates[0]

                    token_name = pair_data["baseToken"]["name"]
                    token_symbol = pair_data["baseToken"]["symbol"]
                    chain_id = pair_data.get("chainId", "unknown")
                    market_cap = float(pair_data.get("marketCap") or 0)
                    liquidity_usd = float((pair_data.get("liquidity") or {}).get("usd") or 0)
                    volume = pair_data.get("volume") or {}
                    vol_m5 = float(volume.get("m5") or 0)
                    vol_h1 = float(volume.get("h1") or 0)
                    created_ms = pair_data.get("pairCreatedAt")

                    st.subheader(f"Analyzing: {token_name} ({token_symbol}) — {chain_id}")

                    safety_score = 100
                    red_flags = []

                    # Check 1: Liquidity-to-market-cap ratio
                    if market_cap > 0:
                        liq_ratio = liquidity_usd / market_cap
                        if liq_ratio < 0.05:
                            safety_score -= 30
                            red_flags.append(
                                f"🚨 Thin liquidity: only {liq_ratio*100:.1f}% of market cap is "
                                "backed by pool liquidity (safe threshold ≥5%)."
                            )

                    # Check 2: Absolute liquidity floor
                    if liquidity_usd < 5000:
                        safety_score -= 20
                        red_flags.append(
                            f"🚨 Very low absolute liquidity: ${liquidity_usd:,.0f}. "
                            "A single large sell can move price sharply."
                        )

                    # Check 3: Wash-trading / volume spike vs liquidity
                    if liquidity_usd > 0 and vol_m5 > liquidity_usd:
                        safety_score -= 25
                        red_flags.append(
                            "🚨 5-minute volume exceeds total pool liquidity — "
                            "possible wash trading / bot activity."
                        )

                    # Check 4: Token age vs volume spike
                    age_str = "unknown"
                    if created_ms:
                        created_dt = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
                        age = datetime.now(timezone.utc) - created_dt
                        age_hours = age.total_seconds() / 3600
                        age_str = f"{age_hours:.1f} hours" if age_hours < 48 else f"{age_hours/24:.1f} days"
                        if age_hours < 24 and liquidity_usd > 0 and vol_h1 > liquidity_usd * 0.5:
                            safety_score -= 15
                            red_flags.append(
                                f"⚠️ Token is under 24h old ({age_str}) with a large volume spike "
                                "relative to liquidity — classic pump pattern before a rug."
                            )

                    safety_score = max(safety_score, 0)

                    st.metric(label="Rule-Based Safety Score", value=f"{safety_score}/100")

                    if safety_score >= 90:
                        st.success(
                            "✅ No major red flags in this pass. Still verify mint/freeze "
                            "authority and holder concentration manually."
                        )
                    elif safety_score >= 60:
                        st.warning("⚠️ Caution: some risk factors detected. Review flags below.")
                    else:
                        st.error("❌ High risk: multiple serious red flags detected.")

                    if red_flags:
                        st.write("### Flags")
                        for flag in red_flags:
                            st.write(flag)

                    st.write("### Extracted Metrics")
                    metrics_df = pd.DataFrame(
                        {
                            "Metric": ["Market Cap", "Liquidity (USD)", "Volume (5m)", "Volume (1h)", "Pair Age"],
                            "Value": [
                                f"${market_cap:,.2f}",
                                f"${liquidity_usd:,.2f}",
                                f"${vol_m5:,.2f}",
                                f"${vol_h1:,.2f}",
                                age_str,
                            ],
                        }
                    )
                    st.table(metrics_df)

                    st.caption(
                        "This scan covers pool-level metrics only (liquidity, volume, age). "
                        "It does NOT check mint/freeze authority, LP burn status, or holder "
                        "concentration — cross-check those on RugCheck.xyz or Solscan before trading."
                    )

            except requests.exceptions.RequestException as e:
                st.error(f"Network error while connecting to DexScreener: {e}")
            except (KeyError, IndexError, ValueError) as e:
                st.error(f"Unexpected data format from the API: {e}")
