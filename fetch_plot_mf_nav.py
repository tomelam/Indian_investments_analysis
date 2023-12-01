#!/opt/homebrew/bin/python3

import requests
import matplotlib.pyplot as plt
import pandas as pd

# The URL of the API
urls = ["https://api.mfapi.in/mf/119100", # HDFC Top 100 Fund, Growth, Direct
       "https://api.mfapi.in/mf/119100" # Bank of India Manu & Infra, Growth, Direct
       ]

url = urls[1]
print(url)

# Send a GET request to the API
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    data = response.json()
    # Assuming 'data' is the key containing the NAV records, similar to the JSON structure you provided
    nav_data = data.get('data', [])
    
    # Convert to a DataFrame
    df = pd.DataFrame(nav_data)
    
    # Convert date strings to datetime objects and nav strings to floats
    df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
    df['nav'] = df['nav'].astype(float)
    
    # Sort by date
    df = df.sort_values('date')

    # Clear any old image.
    plt.clf()

    # Plotting
    plt.figure(figsize=(10, 5))
    # plt.plot(df['date'], df['nav'], marker='o', linewidth=0.5)  # Adjusted line width here
    plt.plot(df['date'], df['nav'], linewidth=0.5)  # Adjusted line width here
    plt.title("NAV Data for HDFC Top 100 Fund - Growth Option - Direct Plan")
    plt.xlabel("Date")
    plt.ylabel("NAV")
    plt.grid(True)
    plt.show()
else:
    print("Failed to fetch data: Status code", response.status_code)
