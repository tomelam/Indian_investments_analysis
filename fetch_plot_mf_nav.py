#!/opt/homebrew/bin/python3

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import Slider
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
#colors = ['brown', 'red', 'green', 'orange']
colors = ['brown', 'red', 'green', 'orange', 'cyan', 'pink', 'blue', 'magenta', 'yellow', 'purple']

# Initialize an empty DataFrame for all fund data
all_fund_data = pd.DataFrame()

# Fetch and process data for each fund
for url, label in zip(urls, labels):
    response = requests.get(url)
    if response.status_code == 200:
        fund_data = response.json()
        df = pd.DataFrame(fund_data['data'])
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
        df.set_index('date', inplace=True)
        df['nav'] = df['nav'].astype(float)
        all_fund_data[label] = df['nav']
    else:
        print(f"Failed to fetch data for {label}")

# Iterate over each column (fund) to apply interpolation only between the first and last valid NAV
for label in all_fund_data.columns:
    # Select the column corresponding to the current fund
    fund_series = all_fund_data[label]
    
    # Find the index of the first non-NaN value
    first_valid_index = fund_series.first_valid_index()
    last_valid_index = fund_series.last_valid_index()

    # Check if there are any valid indices
    if first_valid_index is not None and last_valid_index is not None:
        # Interpolate between the first and last valid values only
        fund_series[first_valid_index:last_valid_index] = fund_series[first_valid_index:last_valid_index].interpolate(method='time')
    
    # Update the fund's series in the DataFrame
    all_fund_data[label] = fund_series

# Normalize the NAVs by dividing by the NAV on the start date and multiplying by 100
start_date = all_fund_data.index.min()
all_fund_data_normalized = (all_fund_data.divide(all_fund_data.loc[start_date], axis='columns')) * 100

# Create a figure and a plot
fig, ax = plt.subplots()
plt.subplots_adjust(bottom=0.25)

# Plot the initial normalized NAV data
lines = [ax.plot(all_fund_data_normalized.index, all_fund_data_normalized[label], color=color, label=label, linewidth=1.5)[0] for label, color in zip(labels, colors)]

# Create a vertical line at the start date
#vline = ax.axvline(x=start_date, color='gray', linestyle='--', linewidth=1)
vline = ax.axvline(x=start_date, color='black', linewidth=0.5)

# Function to update the plot based on the slider
def update(val):
    # Convert slider value to a naive pandas Timestamp and normalize (to remove time component)
    new_base_date = pd.to_datetime(mdates.num2date(val)).tz_localize(None).normalize()

    # Check if the new_base_date is in the DataFrame index
    if new_base_date in all_fund_data.index:
        # Normalize the data based on the new base date selected by the slider
        base_navs = all_fund_data.loc[new_base_date]
        normalized_data = (all_fund_data.divide(base_navs, axis='columns')) * 100

        # Update each line in the plot
        for line, label in zip(lines, labels):
            line.set_ydata(normalized_data[label])
        
        # Move the vertical line to the new base date
        vline.set_xdata([new_base_date, new_base_date])

        # Update the slider's displayed date to the new date in 'dd-mm-yyyy' format
        slider.valtext.set_text(new_base_date.strftime('%d-%m-%Y'))

        # Recalculate the limits of the current axes and autoscale
        ax.relim()
        ax.autoscale_view()
        
        # Redraw the canvas
        fig.canvas.draw_idle()
    else:
        # If the date is not in the DataFrame, find the last valid date that is less than or equal to the chosen date
        idx = all_fund_data.index.get_indexer([new_base_date], method='pad')[0]
        last_valid_date = all_fund_data.index[idx]
        print(f"Selected date {new_base_date.strftime('%d-%m-%Y')} is not in the data range. Reverting to {last_valid_date.strftime('%d-%m-%Y')}.")

        # Set the slider to the last valid date and update the plot accordingly
        slider.set_val(mdates.date2num(last_valid_date))
        update(mdates.date2num(last_valid_date))  # Recursive call to update the plot with the last valid date


# Setup the slider
slider_min_date = mdates.date2num(all_fund_data.index.min().to_pydatetime())
slider_max_date = mdates.date2num(all_fund_data.index.max().to_pydatetime())
ax_slider = plt.axes([0.25, 0.1, 0.65, 0.03])
slider = Slider(ax_slider, 'Normalization Date', slider_min_date, slider_max_date, valinit=slider_min_date)
slider.on_changed(update)

# Set the initial text for the slider's value to the start date in the correct format
slider.valtext.set_text(mdates.num2date(slider.val).strftime('%d-%m-%Y'))

# Set plot title, labels, and legend
ax.set_title('Normalized Mutual Fund NAVs')
ax.set_xlabel('Date')
ax.set_ylabel('Normalized NAV')
legend = ax.legend()

# Increase the linewidth in the legend
for line in legend.get_lines():
    line.set_linewidth(4)  # Set the desired linewidth for legend lines

# After creating your plot, set the background color of the axes
#ax = plt.gca()  # Get the current Axes instance
#ax.set_facecolor('gray')  # Set the inner plot background color
ax.set_facecolor('0.9')  # Set the inner plot background color

# Display the plot
plt.show()

