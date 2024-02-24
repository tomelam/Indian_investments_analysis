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
    
    # Interpolate between the first and last valid values only
    if first_valid_index is not None and last_valid_index is not None:
        fund_series[first_valid_index:last_valid_index] = fund_series[first_valid_index:last_valid_index].interpolate(method='time')
    
    # Update the fund's series in the DataFrame
    all_fund_data[label] = fund_series

# Normalize the NAVs by dividing by the NAV on the start date and multiplying by 100
start_date = all_fund_data.index.min()
all_fund_data_normalized = (all_fund_data.divide(all_fund_data.loc[start_date], axis='columns')) * 100

# Create a figure and a plot
fig, ax = plt.subplots(figsize=(10, 4))
plt.subplots_adjust(left=0.1, bottom=0.25, right=0.9)

# Plot the initial normalized NAV data
lines = [ax.plot(all_fund_data_normalized.index, all_fund_data_normalized[label], color=color, label=label, linewidth=1.5)[0] for label, color in zip(labels, colors)]

vline = ax.axvline(x=start_date, color='black', linewidth=0.5)

# Set up the normalization-date slider
slider_min_date = mdates.date2num(all_fund_data.index.min().to_pydatetime())
slider_max_date = mdates.date2num(all_fund_data.index.max().to_pydatetime())
ax_slider = plt.axes([0.25, 0.1, 0.65, 0.03])
slider = Slider(ax_slider, 'Normalization Date', slider_min_date, slider_max_date, valinit=slider_min_date)
slider.valtext.set_text(mdates.num2date(slider.val).strftime('%d-%m-%Y'))

# Set up the minimum-display-date slider
ax_min_date_slider = plt.axes([0.25, 0.05, 0.65, 0.03])
min_date_slider = Slider(ax_min_date_slider, 'Minimum Display Date', slider_min_date, slider_max_date, valinit=slider_min_date)

# Function to update the plot based on the sliders
def update(val):
    # Convert slider values to datetime objects
    new_base_date = mdates.num2date(slider.val).replace(tzinfo=None)
    min_display_date = mdates.num2date(min_date_slider.val).replace(tzinfo=None)
    
    # Normalize both dates to midnight for comparison and plotting
    new_base_date = new_base_date.replace(hour=0, minute=0, second=0, microsecond=0)
    min_display_date = min_display_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Ensure normalization date is on or after the minimum date
    if new_base_date < min_display_date:
        # Adjust new_base_date to match min_display_date if it's before it
        new_base_date = min_display_date
        # Update the normalization date slider to reflect this change
        slider.set_val(mdates.date2num(new_base_date))  # Convert back to Matplotlib date format for the slider

    # Proceed with filtering data based on min_display_date
    # The NAV data set will have gaps for days that were holidays, Saturdays, or Sundays
    filtered_data_with_gaps = all_fund_data[all_fund_data.index >= min_display_date]
    filtered_data = filtered_data_with_gaps.asfreq('D').ffill()

    # Check if new_base_date is directly available or needs to be forward-filled
    # This check is to understand if the operation was necessary; filtered_data_ffill is already correct
    if new_base_date not in filtered_data_with_gaps.index:
        print(f"Data for {new_base_date} was forward-filled.")

    if new_base_date in filtered_data.index:
        # Normalize the filtered data based on the new base date
        base_navs = filtered_data.loc[new_base_date]
        normalized_data = (filtered_data.divide(base_navs, axis='columns')) * 100

        # Update plot data
        for line, label in zip(lines, labels):
            if label in normalized_data:
                new_y_data = normalized_data[label]
                new_x_data = normalized_data.index
                line.set_data(new_x_data, new_y_data)
        
        # Update vertical line and x-axis limits
        vline.set_xdata([new_base_date, new_base_date])
        ax.set_xlim(left=min_display_date, right=filtered_data.index.max())
        ax.relim()
        ax.autoscale_view()

        # Refresh the plot
        fig.canvas.draw_idle()

    # Correctly format the date displayed beside the minimum-date slider
    slider.valtext.set_text(new_base_date.strftime('%d-%m-%Y'))
    min_date_slider.valtext.set_text(min_display_date.strftime('%m-%d-%Y'))

# Initially set the correct format for the minimum display date slider text
min_date_slider.valtext.set_text(mdates.num2date(min_date_slider.val).strftime('%d-%m-%Y'))

# Set plot title, labels, and legend
ax.set_title('Normalized Mutual Fund NAVs')
ax.set_xlabel('Date')
ax.set_ylabel('Normalized NAV')
legend = ax.legend()

# Increase the linewidth in the legend
for line in legend.get_lines():
    line.set_linewidth(4)  # Set the desired linewidth for legend lines

slider.on_changed(update)
min_date_slider.on_changed(update)

plt.show()
