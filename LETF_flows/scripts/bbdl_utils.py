from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import json
import pandas as pd
import matplotlib.pyplot as plt

# — mappings from data_type to human-friendly y‐axis label (including units) —
_METRIC_LABELS = {
    "CUR_MKT_CAP":    "Market Cap (MM USD)",
    "DVD_SH_12M":     "Dividends per Share (USD)",
    "EQY_SH_OUT":     "Shares Outstanding (MM)",
    "OPEN_INT_TOTAL_CALL": "Call Open Interest (contracts)",
    "OPEN_INT_TOTAL_PUT":  "Put Open Interest (contracts)",
    "PX_HIGH":        "High Price (USD)",
    "PX_LAST":        "Close Price (USD)",
    "PX_LOW":         "Low Price (USD)",
    "PX_VOLUME":      "Equity Volume",
    "SHORT_INT":      "Short Interest",
    "TOT_OPT_VOLUME_CUR_DAY": "Total Option Volume (contracts)",
    "TOT_RETURN_INDEX_GROSS_DVDS": "Total Return Index (USD)",
    "VOLUME_TOTAL_CALL":      "Call Volume (contracts)",
    "VOLUME_TOTAL_PUT":       "Put Volume (contracts)",
}

def get_figi_for_ticker(service: BlobServiceClient, ticker: str, container_name: str = "mapping", mapping_blob: str = "bloomberg_figi_mapping.json") -> str:
    """
    Fetches the FIGI corresponding to a ticker from the mapping JSON.
    """
    container = service.get_container_client(container_name)
    blob = container.get_blob_client(mapping_blob)
    raw = blob.download_blob().readall()
    mapping = json.loads(raw)
    if ticker not in mapping:
        raise ValueError(f"Ticker '{ticker}' not found in mapping.")
    return mapping[ticker]

def fetch_and_convert(service: BlobServiceClient, data_type: str, ticker: str, mapping_container: str = "mapping", processed_container: str = "processed") -> pd.Series:
    """
    Downloads <data_type>.json for the FIGI mapped from `ticker`,
    and returns a sorted time-indexed pandas Series.
    """
    figi = get_figi_for_ticker(service, ticker, mapping_container)
    container_client = service.get_container_client(processed_container)
    
    # Check if the FIGI subdirectory exists
    prefix = f"historical/{figi}/"
    matching = list(container_client.list_blobs(name_starts_with=prefix))
    if not matching:
        raise FileNotFoundError(
            f"Historical time series data not yet pulled for {ticker}"
        )
    blob_path = f"historical/{figi}/{data_type}.json"
    blob = service.get_container_client(processed_container).get_blob_client(blob_path)
    raw = blob.download_blob().readall()
    obj = json.loads(raw)
    data = obj["data"]

    series = pd.Series(data)
    series.index = pd.to_datetime(series.index)
    series.sort_index(inplace=True)
    series.name = _METRIC_LABELS.get(data_type, data_type)
    return series

def plot_series(series: pd.Series, ticker: str, tick_step: int = 250):
    """
    Plots the given time‐series with inferred labels/title based on ticker.
    """
    tick_step = len(series) // 12
    plt.figure(figsize=(12, 6))
    plt.plot(series.index, series.values, label=series.name)
    subset = series.index[::tick_step]
    plt.xticks(subset, rotation=45)
    plt.xlabel("Date")
    plt.ylabel(series.name)
    plt.title(f"{ticker}: {series.name}")
    plt.legend()
    plt.tight_layout()
    plt.show()

def plot_two_series(series1: pd.Series, series2: pd.Series, labels: tuple[str, str], tick_step: int = 250):
    """
    Overlays two time series on a shared x-axis with separate y-axes.

    Args:
        series1: First time series (e.g. underlying shares), with its name as y-label.
        series2: Second time series (e.g. NAV), with its name as y-label.
        labels: Tuple of two strings for the plot title (e.g. ("ETF", "Underlying")).
        tick_step: Number of points between x-ticks; if None, defaults to len(series1)//12.
    """
    # Ensure both series share the same datetime index
    df = pd.DataFrame({
        "s1": series1,
        "s2": series2
    }).dropna()

    # Determine tick spacing
    tick_step = 100

    # Create figure and primary axis
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Plot first series on ax1
    ax1.plot(df.index, df["s1"], label=series1.name, color="tab:blue")
    ax1.set_xlabel("Date")
    ax1.set_ylabel(series1.name, color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")

    # Create secondary y-axis sharing the same x-axis
    ax2 = ax1.twinx()
    ax2.plot(df.index, df["s2"], label=series2.name, color="tab:orange")
    ax2.set_ylabel(series2.name, color="tab:orange")
    ax2.tick_params(axis="y", labelcolor="tab:orange")

    # Title and x-ticks
    title = f"{labels[0]} & {labels[1]}"
    plt.title(title)
    xticks = df.index[::tick_step]
    plt.xticks(xticks, rotation=45)

    # Combine legends
    lines_1, labs_1 = ax1.get_legend_handles_labels()
    lines_2, labs_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labs_1 + labs_2, loc="best")

    fig.tight_layout()
    plt.show()