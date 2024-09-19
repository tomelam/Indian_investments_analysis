# A program to fetch a set of NAVs for some Indian mutual fund schemes, normalize them, and plot them.

## Overview

This Python program fetches mutual fund NAV (Net Asset Value) data from a specified URL and plots it over a given date range. The user can configure some plotting parameters, such as the URLs, fund names, and colors of lines, through a `config.toml` file.

This project is a work in progress. See CHANGELOG.

## Installation

Install Python and the modules that the program imports.

## Configuration

Edit `config.toml`. Be sure the number of URLs, labels, and colors match. A scheme number
can be obtained by typing some part of the mutual fund name into the textbox at
https://www.mfapi.in/ . Sometimes it seems a scheme's number can only be found be searching
https://api.mfapi.in/mf .

## Usage

### Running the Script

```
python plot_mutual_funds.py
```

### Interactive Plot Controls

- **Date-Range Sliders and Entry Boxes**

    Adust the sliders or enter the dates directly in the entry boxes to set the earliest and latest dates for the plot.

- **Normalize-Date Slider and Entry Box**

    Enter the date in the box to set the date where all funds are normalized to 100.

- **Y-Scale Toggle Button**

    Toggle the button labelled 'Linear' to switch between linear and logarithmic scales for the Y-axis. The label toggles between 'Linear' and 'Log'.

- **Legend Click for Hiding/Showing Plots**

    Click on a fund's name in the legend to hide or show its plot on the graph.

## Notes

See the ChatGPT conversation that helped write the initial code:
[Fund NAV Data Plot](https://chat.openai.com/share/9849382e-0b4a-4051-9e40-03214602d751).
I could not share the other ChatGPT conversation that helped me write later versions of the program.
(When I tried to share it, I got the error message "Sharing conversations with images is not yet supported".)
However, I have tried to reconstruct the conversation in Markdown format as the file `ChatGPT.md`.
I have rendered it as a web page, `ChatGPT.html`.
I probably made some formatting mistakes in reconstructing the conversation because I did not scope the job
before beginning it, and I didn't automate it.

-Tom Elam
github.com/tomelam
