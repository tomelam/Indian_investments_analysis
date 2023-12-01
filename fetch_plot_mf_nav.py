#!/opt/homebrew/bin/python3

import requests
import matplotlib.pyplot as plt
import pandas as pd
import json

# The URLs for the API; get these from www.mfapi.in
urls = ["https://api.mfapi.in/mf/119364",   # Bank of India Manu & Infra, Direct, Growth
        "https://api.mfapi.in/mf/145454",   # DSP Healthcare, Direct, Growth
        "https://api.mfapi.in/mf/119028"    # DSP Natural Resources & New Energy, Direct, Growth
        # "https://api.mfapi.in/mf/119277", # DSP World Gold, Direct Growth
                                            # ICICI Dividend Yield, Direct, Growth - can't find it
        # "https://api.mfapi.in/mf/120587", # ICICI FMCG, Direct, Growth
        ]
colors = ['blue', 'green', 'red']
labels = ['BoI Manu', 'Healthcare', 'Nat Rsrc']

plt.figure(figsize=(10, 5))
        
for url, colour, label in zip(urls, colors, labels):
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        fund_data = response.json()
        # Assuming 'data' is the key containing the NAV records, similar to the JSON structure you provided
        nav_data = fund_data.get('data', [])
        
        # Convert to a DataFrame
        df = pd.DataFrame(nav_data)
        
        # Convert date strings to datetime objects and nav strings to floats
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
        df['nav'] = df['nav'].astype(float)
        
        # Sort by date
        df = df.sort_values('date')
        
        # Extract the 'scheme_name' value
        scheme_name = fund_data['meta']['scheme_name']
        
        # Create a plot
        plt.plot(df['date'], df['nav'], linewidth=0.5)
        
        # Set the title using the 'scheme_name' value
        plt.title(f"NAV Data for {scheme_name}")
        
        # Set the labels for the axes
        plt.xlabel("Date")
        plt.ylabel("NAV")
        
        # Optionally, enable the grid
        plt.grid(True)
        
        # Display the plot
        #plt.show()
    else:
        print("Failed to fetch data: Status code", response.status_code)

plt.show()
