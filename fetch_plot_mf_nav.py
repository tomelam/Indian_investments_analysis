# ================================================
#             IMPORTS
# ================================================

import logging
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from matplotlib.widgets import Slider, Button, TextBox
from matplotlib.dates import num2date
import requests
from matplotlib.lines import Line2D
from datetime import timedelta
#import numpy  # Just for debugging

# ================================================
#             CONSTANTS
# ================================================

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
    '01. BoI Mfg & Infra',           # brown
    '02. DSP Healthcare',            # red
    '03. DSP Nat Rsrc & New Energy', # green
    '04. DSP World Gold',            # orange
    '05. ICICI Div Yld Eqty',        # cyan
    '06. ICICI FMCG',                # pink
    '07. ICICI Value',               # blue
    '08. Invesco Infra',             # magenta
    '09. quant Active',              # yellow
    '10. Templeton Eqty Income'      # purple
]

colors = ['brown', 'red', 'green', 'orange', 'cyan', 'pink', 'blue', 'magenta', 'yellow', 'purple']

# For debugging calle to fig.canvas.draw_idle()
set_up_subplots_debugging = True

# It can sometimes help with debugging to make the following `False`
make_plot_interactive = True

#set_log_scale = False

# ================================================
#             SET UP A LOGGER
# ================================================

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

# Turn off excessive logger messages
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# logger.setLevel(logging.WARNING)  # Turn off info and debug messages
logger.setLevel(logging.DEBUG)  # Turn on info and debug messages
# logger.setLevel(logging.INFO)  # Turn on info messages but not debug messages (good for most users)

logger.info("")
logger.info("===== STARTING THE PROGRAM =====")
logger.info("")

# ================================================
#             THE DataFrame
# ================================================

logger.info("")
logger.info("Initializing the Dataframe")
logger.info("")

# Initialize an empty DataFrame for all fund data
all_fund_data = pd.DataFrame()

# Fetch and process data for each fund
# QUESTION: What does `zip` do? Is `labels` used here?
for url, label in zip(urls, labels):
    response = requests.get(url)  # Fetch all the data for one fund from the web service
    if response.status_code == 200:
        fund_data = response.json()  # Parse the web service's response
        logger.debug(f'Type of fund_data: {type(fund_data)}')
        df = pd.DataFrame(fund_data['data'])  # Access the fund's NAV data.
        logger.debug(f'Type of df: {type(df)}')
        #df.loc['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')  # Convert the 'date' column to datetime format
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')

        # Example access of a single NAV
        # nav = df.loc[specific_date, 'nav']
        specific_date = '07-04-2020'
        df.set_index('date', inplace=True)  # Sets the datetime-format dates in the 'date' column as the index of the DataFrame
        #logger.debug(f"Type of df.loc[specific_date, 'nav']: {type(df.loc[specific_date, 'nav'])}")

        # Print the first 2 values in the DataFrame
        logger.debug(f"First value in the DataFrame holding one fund's NAVs: {df.head(1)}")

        df['nav'] = df['nav'].astype(float)
        all_fund_data[label] = df['nav']
    else:
        logger.debug(f"Failed to fetch data for {label}")

logger.info("")
logger.info("Iterating over each column (fund)")
logger.info("")

# FIXME: Iterate over each column (fund) to apply interpolation only between the first and last valid NAV
# Probably this should use the ffill method, not interpolation.
logger.debug(f"for label in all_fund_data: {all_fund_data.columns}")
for label in all_fund_data.columns:
    logger.debug("")
    logger.debug(f"label: {label}")
    # Select the column corresponding to the current fund
    fund_series = all_fund_data[label]
    fund_series = fund_series.to_frame()
    # Ensure the date column is in datetime format
    # fund_series['date'] = pd.to_datetime(fund_series['date'])
    logger.debug(f"Initial type of fund_series: {type(fund_series)}")
    logger.debug(f"Is fund_series DataFrame: {isinstance(fund_series, pd.DataFrame)}")
    logger.debug(f"Index of fund_series is DatetimeIndex: {isinstance(fund_series.index, pd.DatetimeIndex)}")
    logger.debug(f"Column names in fund_series: {fund_series.columns}")
    
    # Find the index of the first non-NaN value
    first_valid_index = fund_series.first_valid_index()
    logger.debug(f'first_valid_index: {first_valid_index}')
    last_valid_index = fund_series.last_valid_index()
    logger.debug(f'last_valid_index: {last_valid_index}')

    # Ensure that the index is a DatetimeIndex
    logger.debug(f"fund_series.index is DatatimeIndex: {isinstance(fund_series.index, pd.DatetimeIndex)}")
    if not isinstance(fund_series.index, pd.DatetimeIndex):
        fund_series.index = pd.to_datetime(fund_series.index, format='%d-%m-%Y')
    logger.debug(f"fund_series.index is DatatimeIndex: {isinstance(fund_series.index, pd.DatetimeIndex)}")
    
    # Print out the dates as they appear in the DataFrame
    #logger.debug("Dates as they appear in the DataFrame:")
    #for date in fund_series.index:
    #    logger.debug(date)

    # Interpolate between the first and last valid values only
    if first_valid_index is not None and last_valid_index is not None:
        # ValueError: time-weighted interpolation only works on Series or DataFrames with a DatetimeIndex
        logger.debug(f'Type of fund_series: {type(fund_series)}')
        fund_series[first_valid_index:last_valid_index] = fund_series[first_valid_index:last_valid_index].interpolate(method='time')
    else:
        raise ValueError("Error: The DataFrame does not have both a first and last valid index. Cannot proceed with the program.")

    # Check fund_series
    logger.debug(f"After modification, type of fund_series: {type(fund_series)}")
    logger.debug(f"Is fund_series DataFrame: {isinstance(fund_series, pd.DataFrame)}")
    logger.debug(f"Index of fund_series is DatetimeIndex: {isinstance(fund_series.index, pd.DatetimeIndex)}")
    
    # Update the fund's series in the DataFrame
    all_fund_data[label] = fund_series

logger.debug("Exited `for label in all_fun_data.columns`")

# Optionally debug the data
def debug_data():
    logger.debug("Entering `debug_data`")

    # Check the type of the index
    index_type = type(all_fund_data.index)
    logger.debug(f"Index type: {index_type}")

    # Print the index values to inspect for anomalies
    logger.debug("Index values:")
    logger.debug(all_fund_data.index)

    # Check if there are mixed types in the index
    index_types = all_fund_data.index.map(type).unique()
    logger.debug(f"Unique index types: {index_types}")

    # Print the first few rows of the DataFrame to inspect the data
    logger.debug("First few rows of all_fund_data:")
    logger.debug(all_fund_data.head())

    # Print the dates with `NaN` values
    nan_rows = all_fund_data.isna().any(axis=1)  # Check for NaN values in the DataFrame
    dates_with_nan = all_fund_data.index[nan_rows]  # Extract dates where NaN values are present
    logger.debug("Dates with NaN values in all_fund_data:")
    for date in dates_with_nan:
        logger.debug(date)

    # Get the first date, last date, and count of dates with NaN values and print the information
    first_date_with_nan = dates_with_nan.min()
    last_date_with_nan = dates_with_nan.max()
    count_of_nan_dates = dates_with_nan.size
    logger.debug("First date with NaN values:", first_date_with_nan)
    logger.debug("Last date with NaN values:", last_date_with_nan)
    logger.debug("Number of dates with NaN values:", count_of_nan_dates)

#debug_data()

logger.info("")
logger.info("Normalizing the NAVs")
logger.info("")

# Normalize the NAVs by dividing by the NAV on the start date and multiplying by 100
start_date = all_fund_data.index.min()
end_date = all_fund_data.index.max()
# FIXME: Use 0 as the base, and +5%, +10%, -5%, -10%, etc. as the y-axis scale.
all_fund_data_normalized = (all_fund_data.divide(all_fund_data.loc[start_date], axis='columns')) * 100
logger.debug(f'Type of all_fund_data_normalized: {type(all_fund_data_normalized)}')

# ================================================
#             The Figure, a Plot,
#             and a Line to Show
#             the NAV-Normalization Date
# ================================================

logger.info("")
logger.info("Setting up the figure, a plot, and a date cursor line")
logger.info("")

# Create a figure and a plot
fig, ax = plt.subplots(figsize=(10, 6))

# Set up a way to debug calls to `fig.canvas.draw_idle`
def execute_draw_idle(fig):
    if set_up_subplots_debugging:
        logger.debug("Debugging fig.canvas.draw_idle calls")
        logger.debug("Calling fig.canvas.draw_idle()...")
        try:
            fig.canvas.draw_idle()
            logger.debug("fig.canvas.draw_idle() executed successfully.")
        except Exception as e:
            logger.debug(f"Error during fig.canvas.draw_idle(): {e}")
    else:
        fig.canvas.draw_idle()

# Set up a way to debug ax method calls
def ax_method_call(method_name, *args, **kwargs):
    """
    Call a method on the ax object with the provided arguments and keyword arguments.

    :param method_name: The name of the method to call.
    :param args: Positional arguments for the method.
    :param kwargs: Keyword arguments for the method.

    Example calls:
    ax_method_call('set_xlim', [0, 100])  # This replaces `ax.set_xlim(0, 100)`
    ax_method_call('set_ylim', [1, 1000])  # This replaces `ax.set_ylim(1, 1000)`
    ax_method_call('set_xlim', [start_date, end_date])  # This replaces `ax.set_xlim(left=start_date, right=end_date)`
    ax_method_call('set_xlim', left=start_date, right=end_date])  # This replaces `ax.set_xlim(left=start_date, right=end_date)`
    line = ax_method_call('axvline', x=start_date, color='black', linewidth=0.5)
    """

    logger.debug(f"Calling ax.{method_name} with args: {args}, kwargs: {kwargs}")
    method = getattr(ax, method_name)
    try:
        result = method(*args, **kwargs)
        logger.debug(f"ax.{method_name} executed successfully.")
        return result
    except Exception as e:
        logger.debug(f"Error during ax.{method_name}: {e}")
        raise

ax_method_call('set_xlim', [start_date, end_date])

# Create a vertical line to act as a user-controlled cursor
# FIXME: Check that the following line replaces `vertical_line = ax_method_call('axvline', [start_date, 'gray', 1])`
vertical_line = ax_method_call('axvline', x=start_date, color='gray', linewidth=1)

# Initialize cursor visibility state
cursor_enabled = False

plt.subplots_adjust(left=0.1, bottom=0.4, top=0.95, right=0.95)

logger.info("")
logger.info("Plotting the normalized NAV data")
logger.info("")

# Plot the initial normalized NAV data
# The following `for` loop could be encapsulated as 
#   lines = [ax.plot(all_fund_data_normalized.index, all_fund_data_normalized[label], color=color, label=label, linewidth=1.5)[0] for label, color in zip(labels, colors)]
# However, for simpler debugging, it is expressed in a `for` loop instead.
lines = []
for label, color in zip(labels, colors):
    logger.debug(f"Plotting label: {label} with color: {color}")

    # Sample minimal data
    #mocked_index = numpy.linspace(1, 10, 100)
    #mocked_data = numpy.logspace(0, 2, 100)
    #logger.debug(f"Truncated Index: {list(mocked_index)}")
    #logger.debug(f"Truncated Data: {list(mocked_data)}")
    #line, = ax.plot(truncated_index, truncated_data, color=color, label=label, linewidth=1.5)

    logger.debug(f"all_fund_data_normalized.index: {all_fund_data_normalized.index}")
    # FIXME: use `ax_method_call`
    line, = ax.plot(all_fund_data_normalized.index, all_fund_data_normalized[label], color=color, label=label, linewidth=1.5)

    lines.append(line) 
    logger.debug(f"Plotted line: {line}")

logger.debug(f'Type of lines: {type(lines)}, len(lines): {len(lines)}, lines[0]: {lines[0]}')

# ================================================
#             Date-Sliders, Date-Input Boxes,
#             Plot Update Based upon Them,
#             and Y-Scale Toggle Switch
# ================================================

logger.info("")
logger.info("Setting up date sliders, text boxes, and toggle switch")
logger.info("")

# Set up the normalization-date slider
plot_min_date = mdates.date2num(start_date.to_pydatetime())
plot_max_date = mdates.date2num(end_date.to_pydatetime())
ax_norm_date_slider = plt.axes([0.25, 0.29, 0.55, 0.03])
norm_date_slider = Slider(ax_norm_date_slider, 'Normalization Date', plot_min_date, plot_max_date, valinit=plot_min_date)
norm_date_slider.valtext.set_text(mdates.num2date(norm_date_slider.val).strftime('%d-%m-%Y'))

# Set up the minimum-display-date slider
ax_min_date_slider = plt.axes([0.25, 0.24, 0.55, 0.03])
min_date_slider = Slider(ax_min_date_slider, 'Minimum Display Date', plot_min_date, plot_max_date, valinit=plot_min_date)
min_date_slider.valtext.set_text(mdates.num2date(min_date_slider.val).strftime('%d-%m-%Y'))

# Set up the maximum-display-date slider
ax_max_date_slider = plt.axes([0.25, 0.19, 0.55, 0.03])
max_date_slider = Slider(ax_max_date_slider, 'Maximum Display Date', plot_min_date, plot_max_date, valinit=plot_max_date)
max_date_slider.valtext.set_text(mdates.num2date(max_date_slider.val).strftime('%d-%m-%Y'))

# Set up text boxes for user input of dates
ax_box_min = plt.axes([0.18, 0.06, 0.2, 0.04])
min_date_text_box = TextBox(ax_box_min, 'Min Date', initial=start_date.strftime('%d-%m-%Y'))

ax_box_max = plt.axes([0.18, 0.02, 0.2, 0.04])
max_date_text_box = TextBox(ax_box_max, 'Max Date', initial=end_date.strftime('%d-%m-%Y'))

ax_box_norm = plt.axes([0.18, 0.10, 0.2, 0.04])
norm_date_text_box = TextBox(ax_box_norm, 'Norm Date', initial=start_date.strftime('%d-%m-%Y'))

class ToggleSwitch:
    def __init__(self):
        self.state = "linear"
        self.button_ax = fig.add_axes([0.75, 0.06, 0.1, 0.04])  # The parameters are left, bottom, width, height
        self.button = Button(self.button_ax, 'Linear Scale')
        self.button.on_clicked(self.toggle)
        logger.debug("Toggle state: {self.state}")

    def toggle(self, event):
        logger.info("Toggling y-axis scale type (linear or log)")
        logger.info(f"Toggle switch state before change: {self.state}")
        self.state = "log" if self.state == "linear" else "linear"
        logger.info(f"Toggle switch state after change: {self.state}")
        self.button.label.set_text('Log Scale' if self.state == "log" else 'Linear Scale')
        set_log_yaxis_scale(self.state)
        fig.canvas.draw()

    def show(self):
        logger.debug("Showing toggle switch")
        #plt.show()  # FIXME: not sure what this would be good for, if anything

# Instantiate the toggle switch
toggle_switch = ToggleSwitch()
toggle_switch.show()

def submit_dates(text):
    logger.debug(f"Entering `submit_dates` with argument: {text}")
    try:
        min_date = pd.to_datetime(min_date_text_box.text, format='%d-%m-%Y')
        max_date = pd.to_datetime(max_date_text_box.text, format='%d-%m-%Y')
        norm_date = pd.to_datetime(norm_date_text_box.text, format='%d-%m-%Y')
        
        min_date_num = mdates.date2num(min_date.to_pydatetime())
        max_date_num = mdates.date2num(max_date.to_pydatetime())
        norm_date_num = mdates.date2num(norm_date.to_pydatetime())
        
        min_date_slider.set_val(min_date_num)
        max_date_slider.set_val(max_date_num)
        norm_date_slider.set_val(norm_date_num)
    except Exception as e:
        logger.debug(f"Error parsing dates: {e}")

min_date_text_box.on_submit(submit_dates)
max_date_text_box.on_submit(submit_dates)
norm_date_text_box.on_submit(submit_dates)

norm_data_line = ax_method_call('axvline', start_date, color='black', linewidth=0.5)

# Function to update the plot based on the sliders
# FIXME: Try to use `def update(val)`
def update(val, event_source=None):
    logger.debug(f"Entering `update` with argument: {val}")
    # Convert slider values to datetime objects
    new_base_date = mdates.num2date(norm_date_slider.val).replace(tzinfo=None)
    min_display_date = mdates.num2date(min_date_slider.val).replace(tzinfo=None)
    max_display_date = mdates.num2date(max_date_slider.val).replace(tzinfo=None)
    
    # Normalize both dates to midnight for comparison and plotting
    new_base_date = new_base_date.replace(hour=0, minute=0, second=0, microsecond=0)
    min_display_date = min_display_date.replace(hour=0, minute=0, second=0, microsecond=0)
    max_display_date = max_display_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Ensure normalization date is on or after the minimum date
    if new_base_date < min_display_date:
        new_base_date = min_display_date
        norm_date_slider.set_val(mdates.date2num(new_base_date))

    # Ensure maximum display date is after the minimum display date
    if max_display_date < min_display_date:
        max_display_date = min_display_date + timedelta(days=1)
        max_date_slider.set_val(mdates.date2num(max_display_date))

    # Ensure normalization date is on or before the maximum date
    if new_base_date > max_display_date:
        new_base_date = max_display_date
        norm_date_slider.set_val(mdates.date2num(new_base_date))

    # Filter data based on display dates
    filtered_data_with_gaps = all_fund_data[(all_fund_data.index >= min_display_date) & (all_fund_data.index <= max_display_date)]
    filtered_data = filtered_data_with_gaps.asfreq('D').ffill()

    if new_base_date in filtered_data.index:
        base_navs = filtered_data.loc[new_base_date]
        normalized_data = (filtered_data.divide(base_navs, axis='columns')) * 100

        logger.debug(f'Type of lines: {type(lines)}')
        for line, label in zip(lines, labels):
            if label in normalized_data:
                new_y_data = normalized_data[label]
                new_x_data = normalized_data.index
                line.set_data(new_x_data, new_y_data)
                logger.debug(f'Type of line: {type(line)}')

        norm_data_line.set_xdata([new_base_date, new_base_date])
        logger.debug(f"left: {min_display_date}, right: {max_display_date}")
        ax_method_call('set_xlim', [min_display_date, max_display_date])
        ax_method_call('relim')
        ax_method_call('autoscale_view')

        logger.debug("`new_base_date` found in `filtered_data.index`. Redrawing figure.")
        execute_draw_idle(fig)
    else:
        logger.debug("`new_base_date` not found in `filtered_data.index`. Is this a problem?")

    norm_date_slider.valtext.set_text(new_base_date.strftime('%d-%m-%Y'))
    min_date_slider.valtext.set_text(min_display_date.strftime('%d-%m-%Y'))
    max_date_slider.valtext.set_text(max_display_date.strftime('%d-%m-%Y'))
    logger.debug("Leaving 'update'")

norm_date_slider.on_changed(lambda val: update(val, event_source='slider'))
min_date_slider.on_changed(lambda val: update(val, event_source='slider'))
max_date_slider.on_changed(lambda val: update(val, event_source='slider'))
# Attaching the update function to sliders directly
#min_date_slider.on_changed(update)
#max_date_slider.on_changed(update)
#norm_date_slider.on_changed(update)

# ================================================
#             Clickable, Hideable Legend
#             for the Plot
# ================================================

# Make the legend items clickable
def on_legend_click(event):
    logger.debug("Legend clicked")
    legline = event.artist
    origline = legline_to_origline[legline]
    vis = not origline.get_visible()
    origline.set_visible(vis)
    legline.set_alpha(1.0 if vis else 0.2)
    logger.debug("Legend clicked. Redrawing figure.")
    #execute_draw_idle(fig)
    fig.canvas.draw_idle()

# Set plot title, labels, and legend
ax.set_title('Normalized Indian Mutual Fund NAVs')
ax.set_xlabel('Date')
ax.set_ylabel('Normalized NAV')
legend = ax.legend()

# Global variable to remember the selected fund
selected_fund = None

def on_move(event):
    global selected_fund
    if not cursor_enabled:
        return
    if selected_fund is None:
        post_log_message("First please select a fund by typing its 2-digit identifier")
    elif event.inaxes == ax:
        vertical_line.set_xdata([event.xdata])  # Update the position of the vertical line
        vertical_line.set_visible(True)  # Make the line visible
        logger.debug("Mouse moved. Redrawing figure.")
        execute_draw_idle(fig)
        # for line in lines:
        line = lines[selected_fund]
        logger.debug(f'Type of lines: {type(lines)}, type of line: {type(line)}')
        if line.get_visible():  # Check if the line is visible
            xdata, ydata = line.get_data()
            if len(xdata) == 0:  # Check if xdata is empty
                raise ValueError(f"Unexpected data after `xdata, ydata = line.get_data()`: {xdata}, {ydata}; can't continue")
            # Convert xdata to numerical dates
            numerical_xdata = mdates.date2num(xdata)
            # Find the closest x value to the cursor position
            closest_x = min(numerical_xdata, key=lambda x: abs(x - event.xdata))
            # Get the corresponding y value
            index = list(numerical_xdata).index(closest_x)

            # Print the datatype of ydata
            logger.debug(f'Type of ydata: {type(ydata)}')

            # Debugging line added to print the index and check data existence
            logger.debug(f'Index: {index}, Data at index: {ydata[index] if index < len(ydata) else "Index out of range"}')

            # Convert ydata to pandas Series
            ydata_series = pd.Series(ydata)

            valid_indices = ydata_series[:index+1].last_valid_index()

            # Print the datatype of ydata after conversion
            logger.debug(f'Type of ydata after conversion: {type(ydata_series)}')
            logger.debug(f'Type of ydata[:index+1]: {type(ydata[:index+1])}')
            logger.debug(f'Type of valid_indices: {type(valid_indices)}')

            # Find the last valid (non-NaN) value up to the date
            valid_indices = ydata[:index+1].last_valid_index()
            if valid_indices is not None:
                nav_value = ydata[valid_indices]
            else:
                # nav_value = float('nan')  # or handle it as per your need
                raise ValueError(f"No valid indices found in `ydata`; can't continue")

            # Print the found nav_value
            logger.debug(f'NAV value: {nav_value}')

            if not pd.isna(nav_value):  # Only print if nav_value is not NaN
                logger.debug("nav_value is NaN")
                date = num2date(closest_x).strftime('%d-%m-%Y')
                post_log_message(f'Fund: {labels[selected_fund]}, Date: {date}, NAV: {line.get_ydata[index]:.2f}')
            else:
                # date = num2date(closest_x).strftime('%d-%m-%Y')
                # post_log_message(f'Fund: {labels[selected_fund]}, Date: {date}, NAV: {line.get_ydata()[index]:.2f}')
                raise ValueError(f"No valid indices found in `ydata`; can't continue")

def on_leave(event):
    logger.debug("Mouse leaving plot area")
    vertical_line.set_visible(False)  # Hide the vertical line
    execute_draw_idle(fig)

# Function to select the fund
def select_fund(index):
    global selected_fund
    index = int(index) - 1
    if 0 <= index < len(urls):
        post_log_message(f"Selected fund: {labels[index]}")
        selected_fund = index
    else:
        post_log_message("Invalid fund index")

# Global variable to store input digits
input_digits = ""

# Modify the existing key press event handler
def on_key(event):
    global input_digits, cursor_enabled
    logger.debug("Key pressed: {event.key}")
    if event.key.isdigit():
        input_digits += event.key
        if len(input_digits) == 2:
            select_fund(input_digits)
            input_digits = ""
    elif event.key == 'c':
        cursor_enabled = not cursor_enabled
        vertical_line.set_visible(cursor_enabled)
        execute_draw_idle(fig)
        logger.debug("In `on_key`: `fig.canvas.draw_idle` returned successfully")

fig.canvas.mpl_connect('key_press_event', on_key)
fig.canvas.mpl_connect('motion_notify_event', on_move)
fig.canvas.mpl_connect('axes_leave_event', on_leave)  # Trigger on leaving the plot area

# Make the legend items clickable
legline_to_origline = {legline: origline for legline, origline in zip(legend.get_lines(), lines)}
for legline in legend.get_lines():
    logger.debug(f"legline: {legline}")
    legline.set_picker(True)
    legline.set_pickradius(5)

fig.canvas.mpl_connect('pick_event', on_legend_click)

for line in legend.get_lines():
    line.set_linewidth(4)

# ================================================
#             SHOW THE PLOT
# ================================================

def set_log_yaxis_scale(scale_type):
    logger.info("Setting y-axis scale type ...")
    match scale_type:
        case "linear":
            logger.info("to linear")
            ax_method_call('set_yscale', 'linear')
        case "log":
            logger.info("to log")
            ax_method_call('set_yscale', 'log')
            ax.yaxis.set_major_formatter(ticker.ScalarFormatter())  # Set y-axis formatter for log scale
            #ax.set_yticks([10, 20, 50, 100, 200, 500, 1000])  # Example ticks, adjust as needed
            ax_method_call('set_yticks', [10, 20, 50, 100, 200, 500, 1000])  # Example ticks, adjust as needed
        case _:
            logger.info("failed")

set_log_yaxis_scale('linear')

logger.info("")
logger.info('Showing the plot')
logger.info("")
try:
    # This blocking invocation will not return until the window is closed.
    plt.show()
    # This non-blocking invocation would return, allowing the plot to be shown while the script continues.
    # It can be used to allow debug statements to be printed, for example.
    # plt.show(block=False)

    # Not shown before the window is closed if the blocking call is used.
    logger.debug("plt.show() called successfully.")
except Exception as e:
    logger.debug(f"Error during plt.show(): {e}")
