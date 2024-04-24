import streamlit as st
import asyncio
import aiohttp
import pandas as pd
import plotly.express as px

# API headers and URL base
headers = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en",
    "Authorization": "Bearer your_api_key",
    "Content-Type": "application/json",
    "Origin": "https://unusualwhales.com",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}

async def fetch_option_data(session, expiry, call_put, strike):
    base_url = "https://phx.unusualwhales.com/api/historic_chains/"
    option_symbol = f"SPXW{expiry}{call_put}0{strike}000"
    url = f"{base_url}{option_symbol}"
    
    try:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()
            return (strike, data)
    except aiohttp.ClientError as e:
        return (strike, {"error": str(e)})

def run_main(expiry, call_put, central_strike):
    strike_range = range(central_strike - 1250, central_strike + 1250, 5)  # Adjust range and step as needed
    
    async def main():
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_option_data(session, expiry, call_put, strike) for strike in strike_range]
            return await asyncio.gather(*tasks)
    
    # Create new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(main())
    loop.close()
    return results
# Streamlit UI components
expiry = st.sidebar.text_input("Expiry (ddmmyy)", "240419")
call_put = st.sidebar.selectbox("Call or Put", ['C', 'P'], index=0)
central_strike = st.sidebar.number_input("Central Strike", min_value=1000, max_value=10000, value=5100, step=100)

# Convert fetched data to numeric and plot with plotly within Streamlit
if st.sidebar.button("Fetch Data"):
    results = run_main(expiry, call_put, central_strike)
    iv_data = {}
    for strike, result in results:
        if 'error' not in result:
            for chain in result.get('chains', []):
                date = chain['date']
                iv = chain.get('implied_volatility')
                if iv is not None:
                    if date not in iv_data:
                        iv_data[date] = {}
                    iv_data[date][strike] = float(iv)

    if iv_data:
        df = pd.DataFrame([
            {'Date': date, 'Strike': strike, 'Implied Volatility': iv}
            for date, strikes in iv_data.items()
            for strike, iv in strikes.items()
        ])
        df['Implied Volatility'] = pd.to_numeric(df['Implied Volatility'], errors='coerce')  # Convert to numeric, coerce errors to NaN
        fig = px.line(df, x="Strike", y="Implied Volatility", color='Date', title="Implied Volatility Across Dates", labels={"Implied Volatility": "Implied Volatility (%)", "Strike": "Strike Price"})
        # Ensure all data is numeric and calculate max, adjusting y-axis to start from 0
        max_iv = df['Implied Volatility'].max() if pd.notna(df['Implied Volatility']).any() else 0
        fig.update_layout(yaxis=dict(range=[0, max_iv * 1.1]))  # Adjusting y-axis to start from 0
        st.plotly_chart(fig)
    else:
        st.error("No data found or error in fetching data.")
