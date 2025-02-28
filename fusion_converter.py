import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import pytz

def process_tx_json(file_path, start_time=None, end_time=None, **filters):
    """
    Processes a JSON file containing sports betting updates and converts it to a DataFrame with optional filtering.
    
    Args:
        file_path (str): The path to the JSON file to be processed.
        start_time (str, optional): The start time in HH:MM:SS format for filtering ReceiveTimestampPacific.
        end_time (str, optional): The end time in HH:MM:SS format for filtering ReceiveTimestampPacific.
        filters (dict): Key-value pairs for filtering specific columns.
        
    Returns:
        pd.DataFrame: A DataFrame containing the processed betting data.
    """

    # Read JSON file
    with open(file_path, 'r') as file:
        data = file.readlines()

    # Create a list to hold the processed data
    processed_data = []

    for line in data:
        # Strip whitespace and check if the line contains a JSON object
        line = line.strip()
        if line and line.startswith('{') and line.endswith('}'):
            try:
                json_data = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {e}")
                continue 

            common_data = {
                "FixtureId": json_data["FixtureId"]["Id"],
                "ClientId": json_data["FixtureId"]["ClientId"],
                "IsOfferedInPlay": json_data["IsOfferedInPlay"],
            }

            # Process different update types
            market_types = {
                "TotalsUpdates": ["Line", "OverPrice", "UnderPrice"],
                "MoneylineUpdates": ["HomePrice", "AwayPrice"],
                "SpreadUpdates": ["Line", "HomePrice", "AwayPrice"],
                "PlayerYesNoUpdates": ["Line"],
                "PlayerOverUnderUpdates": ["AggregateType", "PlayerParticipantId", "TeamParticipantId", "Line", "OverPrice", "UnderPrice"],
                "PlayerNthUpdates": ["Line"],
                "PlayerOverUpdates": ["Line"],
            }

            for market_type, fields in market_types.items():
                if json_data.get(market_type):
                    for update in json_data[market_type]:
                        record = {**common_data, "market_type": market_type}
                        record.update({
                            "LastUpdateTimestampUtc": update.get("LastUpdateTimestampUtc"),
                            "ReceiveTimestampUtc": update.get("ReceiveTimestampUtc"),
                            "EventId": update.get("EventId"),
                            "PeriodType": update.get("PeriodType"),
                            "PeriodNumber": update.get("PeriodNumber"),
                            "Bookmaker": update.get("Bookmaker"),
                            "Type": update.get("Type"),
                            "IsSuspended": update.get("IsSuspended"),
                            "SourceBookmaker": update.get("SourceBookmaker"),
                        })
                        for field in fields:
                            record[field] = update.get(field)

                        processed_data.append(record)

    # Create a pandas DataFrame
    df = pd.DataFrame(processed_data)

    # Function to convert timestamps
    def convert_timezone(utc_time_str, timezone):
        """Converts a UTC timestamp string to the given timezone."""
        if pd.isnull(utc_time_str):
            return None
        utc_time_str = utc_time_str.rstrip('Z')  
        utc_time = datetime.fromisoformat(utc_time_str)
        utc_time = pytz.utc.localize(utc_time)  
        return utc_time.astimezone(pytz.timezone(timezone))

    # Apply time zone conversion
    df['ReceiveTimestampEastern'] = df['ReceiveTimestampUtc'].apply(lambda x: convert_timezone(x, "America/New_York"))
    df['ReceiveTimestampCentral'] = df['ReceiveTimestampUtc'].apply(lambda x: convert_timezone(x, "US/Central"))
    df['ReceiveTimestampPacific'] = df['ReceiveTimestampUtc'].apply(lambda x: convert_timezone(x, "US/Pacific"))

    # Convert timestamps to H:M:S format
    for tz_col in ['ReceiveTimestampEastern', 'ReceiveTimestampCentral', 'ReceiveTimestampPacific']:
        df[f'{tz_col}_HMS'] = df[tz_col].apply(lambda x: x.strftime('%H:%M:%S') if pd.notnull(x) else None)

    # Convert prices to true probabilities
    df['MarginHome'] = 1 / df['AwayPrice'] + 1 / df['HomePrice']
    df['HomeTrueProb'] = (1 / df['HomePrice']) / df['MarginHome']
    df['HomeTruePrice'] = 1 / df['HomeTrueProb']

    df['MarginUnder'] = 1 / df['UnderPrice'] + 1 / df['OverPrice']
    df['OverTrueProb'] = (1 / df['OverPrice']) / df['MarginUnder']
    df['OverTruePrice'] = 1 / df['OverTrueProb']

    # Remove suspended rows
    df = df[df['IsSuspended'] == False]

    # Apply filtering for specific column values if provided
    if filters:
        for column, value in filters.items():
            if column in df.columns:
                df = df[df[column] == value]

    # Apply time filtering for ReceiveTimestampPacific if provided
    if start_time or end_time:
        df['ReceiveTimestampPacific_HMS'] = pd.to_datetime(df['ReceiveTimestampPacific_HMS'], format='%H:%M:%S')

        if start_time:
            start_time_dt = datetime.strptime(start_time, "%H:%M:%S").time()
            df = df[df['ReceiveTimestampPacific_HMS'].dt.time >= start_time_dt]

        if end_time:
            end_time_dt = datetime.strptime(end_time, "%H:%M:%S").time()
            df = df[df['ReceiveTimestampPacific_HMS'].dt.time <= end_time_dt]

    # Keep only columns that exist in the DataFrame
    columns_to_return = [
        'FixtureId',
        'market_type', 'PeriodType', 'PeriodNumber', 'Bookmaker', 'Type', 'Line', 
        'PlayerParticipantId', 'TeamParticipantId', 'HomeTrueProb', 'OverTrueProb', 
        'ReceiveTimestampEastern', 'ReceiveTimestampCentral', 'ReceiveTimestampPacific'
    ]
    df = df[[col for col in columns_to_return if col in df.columns]]


    return df

def main():
    st.title("TXOdds Fusion Converter")
    st.write("Upload a JSON file and apply optional filters - if you don't provide a filter, all data will be processed.")
    
    uploaded_file = st.file_uploader("Upload JSON file", type=["json"])
    
    if uploaded_file is not None:
        temp_path = os.path.join("temp_uploaded.json")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        market_type = st.text_input("Market Type (e.g., MoneylineUpdates)")
        period_type = st.text_input("Period Type (e.g., Full)")
        bookmaker = st.text_input("Bookmaker (e.g., DraftKingsNJ)")
        start_time = st.text_input("Start Time (HH:MM:SS)")
        end_time = st.text_input("End Time (HH:MM:SS)")
        
        filters = {}
        if market_type:
            filters["market_type"] = market_type
        if period_type:
            filters["PeriodType"] = period_type
        if bookmaker:
            filters["Bookmaker"] = bookmaker
        
        if st.button("Process File"):
            with st.spinner("Processing..."):
                try:
                    df = process_tx_json(temp_path, start_time=start_time or None, end_time=end_time or None, **filters)
                    st.write("### Processed Data Preview:")
                    st.dataframe(df.head())
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="processed_betting_data.csv",
                        mime="text/csv"
                    )
                except Exception as e:
                    st.error(f"Error processing file: {e}")

if __name__ == "__main__":
    main()


#  cd Desktop\Projects\Python
# streamlit run fusion_converter.py