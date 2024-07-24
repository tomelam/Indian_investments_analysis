##
##  Program to fetch and plot Indian mutual fund NAVs (net asset values)
##
##  One of mfapi.in's web services provides a complete series of NAVs for a fund
##  via an API endpoint like "https://api.mfapi.in/mf/129312". See the README for
##  instructions on how to get the URL for a particular fund.
##

# ===================================================================================================
#                   IMPORTS
# ===================================================================================================

import logging
import argparse
import toml
import pandas
from datetime import timedelta
import requests
import numpy  # For debugging in function `on_mouse_move`
import pickle
import sys
import traceback

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from matplotlib.widgets import Slider, Button, TextBox
from matplotlib.dates import num2date
from matplotlib.lines import Line2D

# ===================================================================================================
#                   GLOBALS
# ===================================================================================================

# Loggers for different functions or purposes, created by the `logging` module
logger = None                # A general purpose logger instance
logger_update = None         # A logger instance for the `update` function
logger_on_mouse_move = None  # A logger instance for the `on_mouse_move` function

fdm = None                   # The FundDataManager singleton
pm = None                    # The PlotManager singleton
plm = None                   # The PlotLineManager singleton
lines = []                   # Array of line created by ax.plot(...)
labels = []                  # Arbitrary, short names of the funds, for the legend
cursor_enabled = False       # User-controlled cursor is visible?
legline_to_origline = None   # ?
selected_fund = None         # The raw NAV of this fund can be shown

# ===================================================================================================
#                   CLASS DEFINITIONS
# ===================================================================================================

class FundDataManager:
    _instance = None
    all_fund_data = None
    all_fund_data_normalized = None
    start_date = None
    end_date = None

    # This method implements the singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(FundDataManager, \
                                  cls).__new__( cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, *args, **kwargs):
        if not hasattr(self, '_initialized'):
            self.all_fund_data = pandas.DataFrame()
            self._initialized = True

    def concatenate_fund_data(self, fund_dataframe):
        # Concatenate along columns (axis=1)
        self.all_fund_data = pandas.concat( \
                                [self.all_fund_data, fund_dataframe], axis=1)

    def get_all_fund_data(self):
        return self.all_fund_data

    def get_all_fund_data_columns(self):
        return self.all_fund_data.columns

    def extract_fund_data(self, data, start_date, end_date):
        """
        Extracts data from a DataFrame within the specified date range.
        
        Parameters:
        data (pd.DataFrame): The input DataFrame with a DateTime index.
        start_date (str or pd.Timestamp): The start date for the data extraction.
        end_date (str or pd.Timestamp): The end date for the data extraction.
        
        Returns:
        pd.DataFrame: The extracted data within the specified date range.
        """
        # Ensure the index is a DateTimeIndex
        if not isinstance(data.index, pandas.DatetimeIndex):
            raise ValueError("The DataFrame index must be a DateTimeIndex.")
        
        # Convert start and end dates to Timestamps if they are not already
        start_date = pandas.to_datetime(start_date)
        end_date = pandas.to_datetime(end_date)

        # Print the number of entries and their indices
        num_entries = data.shape[0]
        indices = data.index
        
        # Filter the data within the date range
        extracted_data = data[(data.index >= start_date) & (data.index <= end_date)]

        # Print the number of entries and their indices
        num_entries = extracted_data.shape[0]
        indices = extracted_data.index

        return extracted_data

    def interpolate_fund_series_frame(self, label):
        fund_series_frame = self.all_fund_data[label].to_frame()
        # Get the first and last non-NaN values in `fund_series`
        first_valid_index = fund_series_frame.first_valid_index()
        last_valid_index = fund_series_frame.last_valid_index()
        
        # Ensure that the index is a DatetimeIndex.
        # Time-weighted interpolation only works on Series or DataFrames with a
        # DatetimeIndex.
        if not isinstance(fund_series_frame.index, pandas.DatetimeIndex):
            logger.debug("fund_series_frame.index not an instance of pandas.DatetimeIndex")
            fund_series_frame.index = pandas.to_datetime(fund_series_frame.index, format='%d-%m-%Y')

        # Interpolate between the first and last valid values only
        if first_valid_index is not None and last_valid_index is not None:
            fund_series_frame[first_valid_index:last_valid_index] = \
              fund_series_frame[first_valid_index:last_valid_index].interpolate(method='time')
        else:
            raise ValueError( \
                "Error: The DataFrame does not have both a first and a last valid index.")
            sys.exit(1)
        self.all_fund_data_interpolated = fund_series_frame

    def get_all_fund_data_interpolated(self):
        return self.all_fund_data_interpolated()
    
    def set_start_date(self, date):
        self.start_date = date

    def set_end_date(self, date):
        self.end_date = date
    
    def get_start_date(self):
        return self.start_date

    def get_end_date(self):
        return self.end_date

    # FIXME: Consider using 0 as the base, and +5%, +10%, -5%, -10%, etc. as the y-axis scale.
    def normalize_all_fund_data(self):
        self.start_date = self.all_fund_data.index.min()
        self.end_date = self.all_fund_data.index.max()
                
        # Check the data at start_date
        try:
            base_navs = self.all_fund_data.loc[self.start_date]
        except KeyError as e:
            print(f"Error: {e}")
            print("The start_date is not present in the index of all_fund_data.")
            sys.exit(1)

        # Perform the division and handle NaN values
        try:
            # Forward fill to handle gaps
            self.all_fund_data = self.all_fund_data.asfreq('D').ffill()
            if self.start_date in self.all_fund_data.index:
                normalized_data = (self.all_fund_data.divide(self.all_fund_data.loc[self.start_date], axis='columns')) * 100
            else:
                raise ValueError(f"Start date {self.start_date} not in data index.")

            self.all_fund_data_normalized = self.all_fund_data.divide(base_navs, axis='columns') * 100
        except Exception as e:
            print(f"Error during normalization: {e}")
            sys.exit(1)

    def get_all_fund_data_normalized(self):
        return self.all_fund_data_normalized
# End class FundDataManager

class PlotManager:
    _instance = None
    instructions = "Press 'c' to add cursor, then enter a fund's index. Press 'c' to remove cursor."
    cursor_line = None
    msg_box = None            # A box for the user to enter cursor commands and to see NAVs
    norm_date_slider = None   # A slider to set the date at which all NAVs are normalized to 100
    min_date_slider = None    # A slider to set the earliest date of the plot
    max_date_slider = None    # A slider to set the latest date of the plot
    norm_date_text_box = None # A TextBox to set the date at which all NAVs are normalized to 100
    min_date_text_box = None  # A TextBox to set the earliest date of the plot
    max_date_text_box = None  # A TextBox to set the latest date of the plot
    norm_date_line = None     # The vertical line showing the normalization dat
    input_digits = ""         # The digits input by the user to select a fund to view a single NAV

    # This method implements the singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PlotManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False  # Add this line to track initialization
        return cls._instance

    def __init__(self, *args, **kwargs):
        if self._initialized:  # Check if already initialized
            return
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.fdm = FundDataManager()
        self._initialized = True  # Mark as initialized

    def get_ax(self):
        return self.ax

    def get_fig(self):
        return self.fig
    
    def post_log_message(self, message):
        self.msg_box.set_val(message)

    def get_cursor_line(self):
        return self.cursor_line

    def get_norm_date_slider(self):
        return self.norm_date_slider

    def get_min_date_slider(self):
        return self.min_date_slider

    def get_max_date_slider(self):
        return self.max_date_slider

    def get_norm_date_line(self):
        return self.norm_date_line

    def ax_method_call(self, method_name, *args, **kwargs):
        method = getattr(self.ax, method_name)
        try:
            result = method(*args, **kwargs)
            return result
        except Exception as e:
            raise
        
    def add_cursor_line(self, cursor_line_x):
        if self.cursor_line is None:
            self.cursor_line = \
                self.ax_method_call('axvline', x=cursor_line_x, color='gray', linewidth=1)

    def create_figure_components(self, start_date, end_date):
        logger.info("Setting up the figure, a message box, a plot, and a date-cursor line")
        # The dimensions and positions of the figure components
        ax_msg_box = plt.axes([0.39, 0.02, 0.6, 0.05])
        ax_norm_date_slider = plt.axes([0.25, 0.29, 0.55, 0.03])
        ax_min_date_slider = plt.axes([0.25, 0.24, 0.55, 0.03])
        ax_max_date_slider = plt.axes([0.25, 0.19, 0.55, 0.03])
        ax_box_norm = plt.axes([0.09, 0.10, 0.2, 0.04])
        ax_box_min = plt.axes([0.09, 0.06, 0.2, 0.04])
        ax_box_max = plt.axes([0.09, 0.02, 0.2, 0.04])
        
        self.msg_box = TextBox(ax_msg_box, "Messages:", initial=self.instructions)
        
        self.ax_method_call('set_xlim', [fdm.get_start_date(), fdm.get_end_date()])
        
        # Create a vertical line to act as a user-controlled date cursor to query a single NAV
        self.add_cursor_line(fdm.get_start_date())
        
        plt.subplots_adjust(left=0.1, bottom=0.4, top=0.95, right=0.95)
        
        logger.info( \
            "Setting up date sliders, text boxes, and a line indicating the normalization date")
            
        # Set the earliest and latest dates of any NAV in the funds to be plotted
        plot_min_date = mdates.date2num(start_date.to_pydatetime())
        plot_max_date = mdates.date2num(end_date.to_pydatetime())
        
        # Set up the normalization-date slider    
        self.norm_date_slider = Slider(ax_norm_date_slider, 'Normalization Date', \
                                       plot_min_date, plot_max_date, valinit=plot_min_date)
        self.norm_date_slider.valtext.set_text( \
                                     mdates.num2date(self.norm_date_slider.val).strftime('%d-%m-%Y'))
        
        # Set up the minimum-display-date slider
        self.min_date_slider = Slider(ax_min_date_slider, 'Minimum Display Date', \
                                      plot_min_date, plot_max_date, valinit=plot_min_date)
        self.min_date_slider.valtext.set_text( \
                                    mdates.num2date(self.min_date_slider.val).strftime('%d-%m-%Y'))
        
        # Set up the maximum-display-date slider
        self.max_date_slider = Slider(ax_max_date_slider, 'Maximum Display Date', \
                                      plot_min_date, plot_max_date, valinit=plot_max_date)
        self.max_date_slider.valtext.set_text( \
                                    mdates.num2date(self.max_date_slider.val).strftime('%d-%m-%Y'))
        
        # Set up text boxes for user input of dates
        self.norm_date_text_box = TextBox(ax_box_norm, 'Norm Date', \
                                          initial=start_date.strftime('%d-%m-%Y'))
        self.min_date_text_box = TextBox(ax_box_min, 'Min Date', \
                                         initial=start_date.strftime('%d-%m-%Y'))
        self.max_date_text_box = TextBox(ax_box_max, 'Max Date', \
                                         initial=end_date.strftime('%d-%m-%Y'))    
         
        # The vertical line showing the normalization date
        self.norm_date_line = self.ax_method_call('axvline', start_date, color='black', \
                                                  linewidth=0.5)

    def setup_event_handlers(self):
        # Connect input events to their handlers
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        # Trigger a handler when the mouse pointer leaves the plot area
        self.fig.canvas.mpl_connect('axes_leave_event', self.on_leave)
        self.fig.canvas.mpl_connect('pick_event', self.on_legend_click)

        # Connect the text boxes with code
        self.norm_date_text_box.on_submit(self.submit_dates)
        self.min_date_text_box.on_submit(self.submit_dates)
        self.max_date_text_box.on_submit(self.submit_dates)
        
        # Connect the sliders to the `update` function
        self.norm_date_slider.on_changed(lambda val: self.update(val, event_source='slider'))
        self.min_date_slider.on_changed(lambda val: self.update(val, event_source='slider'))
        self.max_date_slider.on_changed(lambda val: self.update(val, event_source='slider'))
        # FIXME: Try to attach the update function to sliders directly
        #min_date_slider.on_changed(update)
        #max_date_slider.on_changed(update)
        #norm_date_slider.on_changed(update)

    # Modify the existing key-press event handler
    def on_key(self, event):
        global labels, cursor_enabled, selected_fund

        # Skip the event handling if a TextBox has focus
        if event.inaxes in [self.norm_date_text_box.ax, \
                            self.min_date_text_box.ax, \
                            self.max_date_text_box.ax]:
            return

        if event.key.isdigit():
            self.input_digits += event.key
            if len(self.input_digits) == 2:
                selected_fund = self.select_fund(self.input_digits)
                cursor_line = pm.get_cursor_line()
                cursor_line.set_visible(cursor_enabled)
                pm.get_fig().canvas.draw_idle()
                self.input_digits = ""
        elif event.key == 'c':
            cursor_enabled = not cursor_enabled
            pm.get_fig().canvas.draw_idle()
            if cursor_enabled:
                self.input_digits = ""
                pm.post_log_message("Now select a fund by typing its 2-digit identifier.")
            else:
                cursor_line = pm.get_cursor_line()
                cursor_line.set_visible(cursor_enabled)
                pm.get_fig().canvas.draw_idle()
                selected_fund = None
                pm.post_log_message(self.instructions)

    # Select one of the funds; takes the number-ID of the fund returns the fund's index
    def select_fund(self, id):
        global selected_fund
        index = int(id) - 1
        if 0 <= index < len(labels):
            pm.post_log_message(f"Selected fund: {labels[index]}")
            return index
        else:
            pm.post_log_message(f"Invalid fund ID: {id}")
            return None

    def submit_dates(self, text):
        global pm
        try:
            norm_date = pandas.to_datetime(pm.norm_date_text_box.text, format='%d-%m-%Y')
            min_date = pandas.to_datetime(pm.min_date_text_box.text, format='%d-%m-%Y')
            max_date = pandas.to_datetime(pm.max_date_text_box.text, format='%d-%m-%Y')
            
            norm_date_num = mdates.date2num(norm_date.to_pydatetime())
            min_date_num = mdates.date2num(min_date.to_pydatetime())
            max_date_num = mdates.date2num(max_date.to_pydatetime())
            
            pm.get_norm_date_slider().set_val(norm_date_num)
            pm.get_min_date_slider().set_val(min_date_num)
            pm.get_max_date_slider().set_val(max_date_num)
            pm.get_fig().canvas.draw_idle()
        except Exception as e:
            logger.debug(f"Error parsing dates: {e}")

    # Function to update the plot based on the sliders
    # FIXME: Try to use `def update(self, val)`
    def update(self, val, event_source=None):
        global pm, norm_date_slider, lines, labels, norm_date_line

        logger_update.debug("Entering update")
        all_fund_data = fdm.get_all_fund_data()
        
        # Convert slider values to datetime objects
        new_base_date = mdates.num2date(pm.get_norm_date_slider().val).replace(tzinfo=None)
        min_display_date = mdates.num2date(pm.get_min_date_slider().val).replace(tzinfo=None)
        max_display_date = mdates.num2date(pm.get_max_date_slider().val).replace(tzinfo=None)
        
        # Normalize the dates to midnight for comparison and plotting
        new_base_date = new_base_date.replace(hour=0, minute=0, second=0, microsecond=0)
        min_display_date = min_display_date.replace(hour=0, minute=0, second=0, microsecond=0)
        max_display_date = max_display_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Ensure normalization date is on or after the minimum date
        if new_base_date < min_display_date:
            new_base_date = min_display_date
            pm.get_norm_date_slider().set_val(mdates.date2num(new_base_date))
            
        # Ensure maximum display date is after the minimum display date
        if max_display_date < min_display_date:
            max_display_date = min_display_date + timedelta(days=1)
            pm.get_max_date_slider().set_val(mdates.date2num(max_display_date))
            
        # Ensure normalization date is on or before the maximum date
        if new_base_date > max_display_date:
            new_base_date = max_display_date
            pm.get_norm_date_slider().set_val(mdates.date2num(new_base_date))

        fdm.set_start_date(min_display_date)
        fdm.set_end_date(max_display_date)
            
        # Filter data based on display dates
        filtered_data_with_gaps = all_fund_data[(all_fund_data.index >= min_display_date) \
                                                & (all_fund_data.index <= max_display_date)]
        filtered_data = filtered_data_with_gaps.asfreq('D').ffill()
        
        if new_base_date in filtered_data.index:
            base_navs = filtered_data.loc[new_base_date]
            normalized_data = (filtered_data.divide(base_navs, axis='columns')) * 100
                
            for line, label in zip(lines, labels):
                if label in normalized_data:
                    new_y_data = normalized_data[label]
                    new_x_data = normalized_data.index
                    line.set_data(new_x_data, new_y_data)
                    #logger_update.debug(f'Type of line: {type(line)}')
                    
            pm.get_norm_date_line().set_xdata([new_base_date, new_base_date])
            self.ax_method_call('set_xlim', [min_display_date, max_display_date])
            self.ax_method_call('relim')
            self.ax_method_call('autoscale_view')
            
            pm.get_fig().canvas.draw_idle()
        else:
            print("`new_base_date` not found in `filtered_data.index`.")
            sys.exit(1)
            
        pm.get_norm_date_slider().valtext.set_text(new_base_date.strftime('%d-%m-%Y'))
        pm.get_min_date_slider().valtext.set_text(min_display_date.strftime('%d-%m-%Y'))
        pm.get_max_date_slider().valtext.set_text(max_display_date.strftime('%d-%m-%Y'))

    # Make a vertical cursor line follow the mouse
    def on_mouse_move(self, event):
        global pm, cursor_enabled, selected_fund, labels
        ax = pm.get_ax()
        cursor_line = pm.get_cursor_line()

        if not cursor_enabled:
            return

        if selected_fund is None:
            return

        if event.inaxes == ax:
            cursor_line.set_xdata([event.xdata])  # Update the position of the vertical line
            cursor_line.set_visible(True)         # Make the line visible
            pm.get_fig().canvas.draw_idle()
            line = lines[selected_fund]
            if line.get_visible():  # Is the line visible?
                date, index = plm.get_index_and_date_at_cursor(line, event.xdata)
                all_fund_data = fdm.get_all_fund_data()
                start_date = fdm.get_start_date()
                end_date = fdm.get_end_date()
                extracted_data = fdm.extract_fund_data( \
                                    all_fund_data, start_date, \
                                    end_date)
                indexed_ydata = extracted_data[labels[selected_fund]]
                all_indexed_ydata = all_fund_data[labels[selected_fund]].iloc
                pm.post_log_message( \
                    f"Fund: {labels[selected_fund]}, Date: {date}, NAV: {indexed_ydata[index]:.2f}")

    # Make the legend items clickable for hiding/showing individual plot lines
    def on_legend_click(self, event):
        global pm, legline_to_origline
        legline = event.artist
        origline = legline_to_origline[legline]
        vis = not origline.get_visible()
        origline.set_visible(vis)
        legline.set_alpha(1.0 if vis else 0.2)
        pm.get_fig().canvas.draw_idle()  # FIXME: Try to use `execute_draw_idle(fig)`.

    def on_leave(self, event):
        global pm
        cursor_line = pm.get_cursor_line()
        cursor_line.set_visible(False)  # Hide the vertical line
        pm.get_fig().canvas.draw_idle()
# End class PlotManager

class PlotLineManager:
    global pm, lines
    _instance = None

    # This method implements the singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PlotLineManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    
    def draw_plot_lines(self, start_date, end_date, labels, colors, all_fund_data_normalized):
        # Plot the initial normalized NAV data
        # The following `for` loop could be encapsulated as 
        #   lines = [ax.plot(all_fund_data_normalized.index, all_fund_data_normalized[label], color=color, label=label, linewidth=1.5)[0] for label, color in zip(labels, colors)]
        # However, for simpler debugging, it is expressed in a `for` loop instead.
        for label, color in zip(labels, colors):
            line, = pm.get_ax().plot(all_fund_data_normalized.index, \
                                     all_fund_data_normalized[label], \
                                     color=color, label=label, linewidth=1.5)
            lines.append(line)
        for idx, line in enumerate(lines):
            x_data = line.get_xdata()
            y_data = line.get_ydata()

    def get_index_and_date_at_cursor(self, line, mouse_xdata):
        xdata, ydata = line.get_data()
        # Convert xdata to numerical dates
        numerical_xdata = mdates.date2num(xdata)
        # Find the x value closest to the cursor position
        closest_x = min(numerical_xdata, key=lambda x: abs(x - mouse_xdata))
        # Get the closest x value's corresponding date
        date = num2date(closest_x).strftime('%d-%m-%Y')
        # Get the corresponding y value
        index = list(numerical_xdata).index(closest_x)
        return (date, index)

# End class PlotLineManager

class ToggleSwitch:
    global pm
    
    def __init__(self):
        self.state = "linear"
        self.button_ax = pm.get_fig().add_axes([0.89, 0.08, 0.1, 0.04])  # The parameters are left, bottom, width, height
        self.button = Button(self.button_ax, 'Linear Scale')
        self.button.on_clicked(self.toggle)

    def toggle(self, event):
        self.state = "log" if self.state == "linear" else "linear"
        self.button.label.set_text('Log Scale' if self.state == "log" else 'Linear Scale')
        set_log_yaxis_scale(self.state)
        pm.get_fig().canvas.draw()

    def show(self):
        #plt.show()  # FIXME: not sure what this would be good for, if anything
        pass
# End class ToggleSwitch

# ===================================================================================================
#                   FUNCTION DEFINITIONS
# ===================================================================================================

def initialize_loggers(level=logging.INFO):
    global logger, logger_update, logger_on_mouse_move
    
    #logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
    logging.basicConfig(level=level, format='%(levelname)s - %(message)s')
    
    # Turn off excessive logger messages
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Set up a handler for the `update` function
    logger_update = logging.getLogger(f"{__name__}.update")
    logger_update.setLevel(logging.DEBUG)

    # Set up a handler for the `on_mouse_move` function
    logger_on_mouse_move = logging.getLogger(f"{__name__}.on_mouse_move")
    logger_on_mouse_move.setLevel(logging.DEBUG)

    logger = logging.getLogger(__name__)

def set_general_logging_level(level):
    global logger
    logger.info(f"Setting `logger` logging level: {logging.getLevelName(level)}`")
    logger.setLevel(level)

def set_update_logging_level(level):
    global logger_update
    logger.info(f"Setting `logger_update` logging level: {logging.getLevelName(level)}")
    logger_update.setLevel(level)
    
def set_on_mouse_move_logging_level(level):
    global logger_on_mouse_move
    logger.info(f"Setting `logger_on_mouse_move` logging level: {logging.getLevelName(level)}")
    logger_on_mouse_move.setLevel(level)

def get_general_logging_level():
    return logging.getLevelName(logger.getEffectiveLevel())

# FIXME: This function needs to be updated. It might or might work as is. It is not in use.
# Extract data for the unit tests
def extract_data_for_on_move(event, cursor_enabled, selected_fund, labels, \
                             all_fund_data_normalized, start_date):
    # Extract relevant attributes from the event
    event_data = {
        'name': event.name,
        'canvas': None,  # We cannot pickle the canvas, so we'll set it to None
        'x': event.x,
        'y': event.y,
        'xdata': event.xdata,
        'ydata': event.ydata,
        'inaxes': {
            'xlabel': event.inaxes.get_xlabel(),
            'ylabel': event.inaxes.get_ylabel(),
            'title': event.inaxes.get_title(),
            'xlim': event.inaxes.get_xlim(),
            'ylim': event.inaxes.get_ylim(),
            'xticks': event.inaxes.get_xticks(),
            'yticks': event.inaxes.get_yticks()
        } if event.inaxes else None
    }
    data = {
        "event_data": event_data,
        "cursor_enabled": cursor_enabled,
        "selected_fund": selected_fund,
        "labels": labels,
        "all_fund_data_normalized": all_fund_data_normalized,
        "start_data": start_date
    }
    with open('data_for_on_move_tests.pkl', 'wb') as f:
        pickle.dump(data, f)
    
def read_and_validate_config(file_path):
    config = toml.load(file_path)

    constants = config['constants']

    return constants

# FIXME: This function needs to be updated. It might or might work as is. It is not in use.
# Optionally debug the data
def debug_data():
    global all_fund_data_df

    level = get_general_logging_level()
    set_general_logging_level(logging.WARNING)
    
    logger.info("")
    logger.info("Entering `debug_data`")
    logger.info("")

    # Check the type of the index
    index_type = type(all_fund_data_df.index)
    logger.debug(f"Index type: {index_type}")

    # Print the index values to inspect for anomalies
    logger.debug("Index values:")
    logger.debug(all_fund_data_df.index)

    # Check if there are mixed types in the index
    index_types = all_fund_data_df.index.map(type).unique()
    logger.debug(f"Unique index types: {index_types}")

    # Print the first few rows of the DataFrame to inspect the data
    logger.debug("First few rows of all_fund_data_df:")
    logger.debug(all_fund_data_df.head())

    # Print the last few rows of the DataFrame to inspect the data
    logger.debug("Last few rows of all_fund_data_df:")
    logger.debug(all_fund_data_df.tail())

    # Print the dates with `NaN` values
    nan_rows = all_fund_data_df.isna().any(axis=1)  # Check for NaN values in the DataFrame
    dates_with_nan = all_fund_data_df.index[nan_rows]  # Extract dates where NaN values are present
    #logger.debug("Dates with NaN values in all_fund_data_df:")
    #for date in dates_with_nan:
    #    logger.debug(date)
    #logger.debug("")

    # Get the first date, last date, and count of dates with NaN values and print the information
    first_date_with_nan = dates_with_nan.min()
    last_date_with_nan = dates_with_nan.max()
    count_of_nan_dates = dates_with_nan.size
    logger.debug(f"First date with NaN values: {first_date_with_nan}")
    logger.debug(f"Last date with NaN values: {last_date_with_nan}")
    logger.debug(f"Number of dates with NaN values: {count_of_nan_dates}")

    logger.info("")
    logger.info("Exiting `debug_data`")
    logger.info("")

    # Return logging level to what it was before this function was called
    set_general_logging_level(level)

# Set the y-axis scale type to 'linear' or 'log'
def set_log_yaxis_scale(scale_type):
    global pm
    val = pm.get_min_date_slider().val
    
    match scale_type:
        case "linear":
            pm.ax_method_call('set_yscale', 'linear')
            pm.update(val)
        case "log":
            pm.ax_method_call('set_yscale', 'log')
            # Set y-axis formatter for log scale
            pm.get_ax().yaxis.set_major_formatter(ticker.ScalarFormatter())
            # Example ticks, adjust as needed
            pm.ax_method_call('set_yticks', [10, 20, 50, 100, 200, 500, 1000])
            pm.update(val)
        case _:
            logger.debug("failed\n")
            
# ===================================================================================================
#                   MAIN
# ===================================================================================================

def main():
    global fdm, pm, plm, labels, lines, legline_to_origline

    parser = None            # Command-line arguments parser
    args = None              # Command-line arguments
    config_file = None       # The name of the configuration file
    config = None            # URLs, labels, and colors for fetching and plotting NAVs
    urls_length = None       # The number of URLs in the configuration file, for checking the file
    urls = None              # The URLs of the funds' data
    response = None          # The HTTP (web) response to a request for a single fund's data
    toggle_switch = None     # The switch for toggling between a linear y-scale and a log y-scale

    initialize_loggers()
    set_general_logging_level(logging.DEBUG)
    set_update_logging_level(logging.DEBUG)
    set_on_mouse_move_logging_level(logging.DEBUG)
    
    logger.info("")
    logger.info("===== STARTING THE PROGRAM =====")
    logger.info("")

    # ================================================
    #    CHECK AND PARSE THE COMMAND-LINE ARGUMENTS
    # ================================================
    
    parser = argparse.ArgumentParser(description="Read and validate a TOML configuration file.")
    parser.add_argument('-c', '--config', type=str, default='config.toml', \
                        help='Path to the TOML configuration file')
    
    args = parser.parse_args()
    config_file = args.config
    config = read_and_validate_config(config_file)

    # Assign elements to variables
    try:
        # Check if all constants have the same number of elements
        urls_length = len(config['urls'])
        if not (len(config['labels']) == urls_length and len(config['colors']) == urls_length):
            raise ValueError("All constant arrays must have the same number of elements.")
        urls = config['urls']
        labels = config['labels']
        colors = config['colors']
    except KeyError as e:
        logger.critical(f"Missing key in configuration: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.critical(f"Validation error: {e}")
        sys.exit(1)

    # ================================================
    #             SET UP A DataFrame
    # ================================================
    
    logger.info("Initializing a Dataframe for all fund data")

    fdm = FundDataManager()
    pm = PlotManager()
    plm = PlotLineManager()
    
    # Fetch and process data for each fund
    # QUESTION: What does `zip` do? Is `labels` used here?
    for url, label in zip(urls, labels):
        # These 3 variables are local.
        fund_data = None              # A fund's data parsed from the web server's response
        df = None                     # A DataFrame containing a single fund's processed NAV data
        temp_df = None                # A temporary store for a DataFrame
        response = requests.get(url)  # Fetch all the data for one fund from the web service

        if response.status_code == 200:
            fund_data = response.json()  # Parse the web service's response
            df = pandas.DataFrame(fund_data['data'])  # Convert fund_data['data'] to a DataFrame
            df['date'] = pandas.to_datetime(df['date'], format='%d-%m-%Y')
            df.set_index('date', inplace=True)  # Sets the datetime-format dates in the 'date' column as the index of the DataFrame
            
            # FIXME: Convert NAV values to floating point format?
            df['nav'] = df['nav'].astype(float)

            # Assign `df` column to corresponding column in `all_fund_data_df`
            if 'nav' in df:  # Ensure `df` has data for 'nav'
                # Create a DataFrame with the current label
                temp_df = pandas.DataFrame({label: df['nav']})
                # Concatenate along columns (axis=1)
                fdm.concatenate_fund_data(temp_df)

        else:
            logger.debug(f"Failed to fetch data for {label}")

    # ================================================
    #        FILL IN OR INTERPOLATE AND NORMALIZE FUND DATA
    # ================================================

    logger.info("Interpolating the data for each fund")

    # FIXME: Iterate over each column (fund) to apply interpolation only between the first and \
    # last valid NAV
    # Probably this should use the ffill method, not interpolation.
    for label in fdm.get_all_fund_data_columns():
        fdm.interpolate_fund_series_frame(label)

    logger.info("Normalizing all fund data")
    fdm.normalize_all_fund_data()
    
    # ================================================
    #    Create the Figure, a Message Box, a Plot,
    #              and a Line to Show
    #          the NAV-Normalization Date
    # ================================================

    logger.info("Creating figure components")
    pm.create_figure_components(fdm.get_start_date(), fdm.get_end_date())

    all_fund_data_normalized = fdm.get_all_fund_data_normalized()
    plm.draw_plot_lines(fdm.get_start_date(), fdm.get_end_date(), labels, colors, all_fund_data_normalized)

    pm.setup_event_handlers()
    
    # Instantiate and show the toggle switch
    toggle_switch = ToggleSwitch()
    toggle_switch.show()

    # Set plot title, labels, and legend
    pm.get_ax().set_title('Normalized Indian Mutual Fund NAVs')
    pm.get_ax().set_xlabel('Date')
    pm.get_ax().set_ylabel('Normalized NAV')
    legend = pm.get_ax().legend()
    
    # Ensure legend and lines have the same length
    if len(legend.get_lines()) != len(lines):
        logger.critical("The number of legend lines does not match the number of original lines.")
        
    # Map legend lines to original lines
    legline_to_origline = {legline: origline for legline, origline in zip(legend.get_lines(), lines)}
        
    # Iterate over legend lines and set picker properties
    for legline in legend.get_lines():
        legline.set_picker(True)
        legline.set_pickradius(5)

    # Set the width of the legend lines
    for line in legend.get_lines():
        line.set_linewidth(4)

    # ================================================
    #             SHOW THE PLOT
    # ================================================
    
    set_log_yaxis_scale("linear")
    
    logger.info("Showing the plot")
    try:
        # This blocking invocation will not return until the window is closed.
        plt.show()
        # This non-blocking invocation would return, allowing the plot to be shown while the script continues.
        # It can be used to allow debug statements to be printed, for example.
        # plt.show(block=False)
        
        # Not shown before the window is closed if the blocking call is used.
        #logger.debug("plt.show() called successfully.")
    except Exception as e:
        logger.debug(f"Error during plt.show(): {e}")

if __name__ == "__main__":
    main()
