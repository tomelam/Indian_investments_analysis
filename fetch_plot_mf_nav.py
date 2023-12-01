#!/opt/homebrew/bin/python3

# Fetch the NAVs of some Indian mutual fund schemes, normalize them, and plot them.
#
# A scheme number can be obtained by typing some part of the mutual fund name into the textbox at
# https://www.mfapi.in/ . Sometimes it seems a scheme's number can only be found be searching
# https://api.mfapi.in/mf .
#
# -Tom Elam
# github.com/tomelam

import matplotlib.pyplot as plt
import pandas as pd
import requests

# URLs for the fund data API
urls = [
    'https://api.mfapi.in/mf/119364', # Bank of India Manu & Infra, Direct, Growth
    'https://api.mfapi.in/mf/145454', # DSP Healthcare, Direct, Growth
    'https://api.mfapi.in/mf/119028', # DSP Natural Resources & New Energy, Direct, Growth
    'https://api.mfapi.in/mf/119277', # DSP World Gold FoF, Direct, Growth
    'https://api.mfapi.in/mf/129312', # ICICI Prudential Dividend Yield Equity, Direct, Growth
    'https://api.mfapi.in/mf/120587', # ICICI FMCG, Direct, Growth
    'https://api.mfapi.in/mf/120323', # ICICI Value Discovery, Direct, Growth
    'https://api.mfapi.in/mf/106654', # Invesco India Infrastructure, Direct, Growth
    'https://api.mfapi.in/mf/120823', # quant Active, Direct, Growth
    'https://api.mfapi.in/mf/118527'  # Templeton India Equity Income, Direct, Growth
]

labels = [
    'BoI Mfg & Infra',           # brown
    'DSP Healthcare',            # red
    'DSP Nat Rsrc & New Energy', # green
    'DSP World Gold',            # orange
    'ICICI Div Yld Eqty',        # cyan
    'ICICI FMCG',                # pink
    'ICICI Value',               # blue
    'Invesco Infra',             # magenta
    'quant Active',              # yellow
    'Templeton Eqty Income'      # purple
]

#colors = ['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'orange', 'purple', 'brown', 'pink']
colors = ['brown', 'red', 'green', 'orange', 'cyan', 'pink', 'blue', 'magenta', 'yellow', 'purple']

plt.figure(figsize=(10, 5))

# Iterate over each fund URL
for url, color, label in zip(urls, colors, labels):
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        fund_data = response.json()
        df = pd.DataFrame(fund_data['data'])

        # Convert date strings to datetime objects and nav to float
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
        df['nav'] = df['nav'].astype(float)

        # Filter the DataFrame to only include rows from 2015 onwards
        df = df[df['date'].dt.year >= 2015]

        # Sort by date to ensure the first NAV is the earliest
        df.sort_values(by='date', inplace=True)

        # Normalize the NAVs by dividing by the first NAV and multiplying by 100
        df['normalized_nav'] = (df['nav'] / df['nav'].iloc[0]) * 100

        # Plot the normalized NAVs for each fund
        plt.plot(df['date'], df['normalized_nav'], color=color, label=label, linewidth=1.1)
    else:
        print(f"Failed to fetch data for {label}")

# Set the title, labels, and legend
plt.title("Comparison of Normalized NAVs for Multiple Funds")
plt.xlabel("Date")
plt.ylabel("Normalized NAV")
legend = plt.legend()

# Set the linewidth of each legend handle
for line in legend.get_lines():
    line.set_linewidth(4.0)  # Set the desired linewidth here

# Optionally, enable the grid
plt.grid(True)

# Set the background color
ax = plt.gca()  # Get the current Axes instance
ax.set_facecolor('gray')  # Set the inner plot background color

# Display the plot
plt.show()
