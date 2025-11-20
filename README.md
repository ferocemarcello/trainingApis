# Fitness Data Aggregator

This project is a Python application that aggregates fitness data from various sources like Garmin Connect, Polar, and Strava and consolidates it into a single Google Sheet.

## Features

-   **Data Aggregation**: Connects to Garmin Connect, Polar, and Strava APIs to download your fitness data.
-   **Google Sheets Integration**: Uploads the aggregated data to a Google Sheet for easy analysis and visualization.
-   **Data Analysis**: Provides basic statistical analysis of your fitness data.
-   **Configurable**: Easily configurable through Python script to add new data sources or modify existing ones.

## How it Works

The application uses a combination of official and unofficial APIs to connect to the fitness data providers. It then processes the data and uploads it to a Google Sheet that you specify in the configuration.

## Getting Started

### Prerequisites

-   Python 3.x
-   Google Cloud Platform project with the Google Sheets API enabled.
-   API credentials for Garmin Connect, Polar, and Strava.

### Installation

1.  Clone this repository:
    ```bash
    git clone https://github.com/your-username/fitness-data-aggregator.git
    ```
2.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configure the application by editing the `config.py` file with your API keys and Google Sheet ID.

### Usage

Run the main application to start the data aggregation process:

```bash
python main.py
```

## Disclaimer

This application uses unofficial APIs for some of the data sources. The APIs may change or break at any time. Use at your own risk.