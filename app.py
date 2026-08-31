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
        # Säuberung der Adresse (Entfernt versehentlich mitkopierte Web-Links)
        clean_ca = target_ca.strip().replace("https://", "").replace("dexscreener.com", "").replace("/", "")
        
        with st.spinner("Fetching live on-chain market data arrays..."):
            # --- DIE KORREKTE GLOBAL SEARCH API ROUTE ---
            api_url = f"https://dexscreener.com{clean_ca}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json"
            }
            
            try:
                response = requests.get(api_url, headers=headers, timeout=10)
                
                if response.status_code == 200 and response.json().get('pairs'):
                    # Holt das erste Element aus dem Ergebnis-Array
                    pair_data = response.json()['pairs'][0]
                    
                    # Variablen-Extraktion
                    token_name = pair_data['baseToken']['name']
                    token_symbol = pair_data['baseToken']['symbol']
                    market_cap = float(pair_data.get('marketCap', 0))
                    liquidity_usd = float(pair_data.get('liquidity', {}).get('usd', 0))
                    volume_5m = float(pair_data.get('volume', {}).get('m5', 0))
                    
                    st.subheader(f"Analyzing: {token_name} ({token_symbol})")
                    
                    # --- SAFETY ENGINE ---
                    safety_score = 100
                    red_flags = []
                    
                    if market_cap > 0:
                        liq_ratio = liquidity_usd / market_cap
                        if liq_ratio < 0.05:
                            safety_score -= 30
                            red_flags.append(f"🚨 Thin Liquidity Window: Liquidity is only {liq_ratio*100:.1f}% of Market Cap. High crash risk.")
                    
                    if volume_5m > liquidity_usd and liquidity_usd > 0:
                        safety_score -= 25
                        red_flags.append("🚨 Artificial Wash Trading: 5-min volume exceeds total pool depth. Fake bot volume detected.")
                    
                    # --- DISPLAY RESULTS ---
                    st.metric(label="Calculated Safety Confidence Score", value=f"{safety_score}/100")
                    
                    if safety_score == 100:
                        st.success("✅ Structural data matrix checks passed.")
                    elif safety_score >= 70:
                        st.warning("⚠️ Caution: Minor anomalies detected.")
                    else:
                        st.error("❌ High Risk Environment: Multiple abnormalities found.")
                        
                    if red_flags:
                        st.write("### Data Anomalies Found:")
                        for flag in red_flags:
                            st.write(flag)
                            
                    st.write("### Extracted Structural Vector")
                    metrics_df = pd.DataFrame({
                        "Metric Parameter": ["Market Cap", "Liquidity Pool", "Recent Vol (5m)"],
                        "Value ($USD)": [f"${market_cap:,.2f}", f"${liquidity_usd:,.2f}", f"${volume_5m:,.2f}"]
                    })
                    st.table(metrics_df)
                    
                else:
                    st.error("Token pool data not found. Ensure the token is actively trading and indexed on DexScreener.")
            
            except requests.exceptions.RequestException as e:
                st.error(f"Network error while connecting to the blockchain API: {e}")
