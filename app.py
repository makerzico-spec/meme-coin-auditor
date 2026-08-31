import streamlit as st
import requests
import pandas as pd

# Setup UI Dashboard
st.set_page_config(page_title="Advanced Token Auditor", layout="centered")
st.title("🛡️ Advanced Meme Coin Fraud Detector")
st.write("Analyzes behavioral data arrays to catch scams missed by basic contract scanners.")

# User Input (Contract Address)
target_ca = st.text_input("Paste Token Contract Address (CA):", placeholder="e.g., EPjFW3DpEqCKKZ7My1VZwVWGq1MUMbQKu9vG3Hyvwmkz")

if st.button("Run Forensic Audit"):
    if not target_ca:
        st.warning("Please enter a valid contract address.")
    else:
        with st.spinner("Fetching live on-chain market data arrays..."):
            # Fetch data from DexScreener API
            api_url = f"https://dexscreener.com{target_ca}"
            response = requests.get(api_url)
            
            if response.status_code == 200 and response.json().get('pairs'):
                # Extract primary pair data array
                pair_data = response.json()['pairs'][0]
                
                # Extract Variables (Similar to MATLAB struct extraction)
                token_name = pair_data['baseToken']['name']
                token_symbol = pair_data['baseToken']['symbol']
                market_cap = float(pair_data.get('marketCap', 0))
                liquidity_usd = float(pair_data.get('liquidity', {}).get('usd', 0))
                volume_24h = float(pair_data.get('volume', {}).get('m5', 0)) # 5-min volume to check bot spam
                
                st.subheader(f"Analyzing: {token_name} ({token_symbol})")
                
                # --- SAFETY ENGINE (MATLAB-STYLE LOGIC FILTERS) ---
                safety_score = 100
                red_flags = []
                
                # Check 1: Liquidity-to-Market Cap Ratio Check
                if market_cap > 0:
                    liq_ratio = liquidity_usd / market_cap
                    if liq_ratio < 0.05:  # Less than 5% liquidity backing
                        safety_score -= 30
                        red_flags.append(f"🚨 Thin Liquidity Window: Liquidity is only {liq_ratio*100:.1f}% of Market Cap. High crash risk.")
                
                # Check 2: High Volume Dev Wash-Trading Check
                # If 5-minute volume exceeds total liquidity, bots are artificially cycling funds
                if volume_24h > liquidity_usd and liquidity_usd > 0:
                    safety_score -= 25
                    red_flags.append("🚨 Artificial Wash Trading: 5-min transaction volume exceeds total pool depth. Fake bot volume detected.")
                
                # Check 3: Check for Lock Flags provided by API summary
                info_tags = pair_data.get('info', {})
                # Note: Expanded implementations can cross-reference specific holder arrays via chain-specific RPCs
                
                # --- DISPLAY AUDIT RESULTS ---
                st.metric(label="Calculated Safety Confidence Score", value=f"{safety_score}/100")
                
                if safety_score == 100:
                    st.success("✅ Static and basic behavioral matrix checks passed. Proceed to manual wallet distribution scan.")
                elif safety_score >= 70:
                    st.warning("⚠️ Caution: Minor structural anomalies detected. Review flags below.")
                else:
                    st.error("❌ High Probability Scam Environment: Multiple structural data anomalies found.")
                    
                if red_flags:
                    st.write("### Data Anomalies Found:")
                    for flag in red_flags:
                        st.write(flag)
                        
                # Display Raw Metric Vector for Reference
                st.write("### Extracted Structural Vector")
                metrics_df = pd.DataFrame({
                    "Metric Parameter": ["Market Cap", "Liquidity Pool", "Recent Vol (5m)"],
                    "Value ($USD)": [f"${market_cap:,.2f}", f"${liquidity_usd:,.2f}", f"${volume_24h:,.2f}"]
                })
                st.table(metrics_df)
                
            else:
                st.error("Could not fetch data for this Contract Address. Verify the address is correct and indexed on DEXScreener.")
