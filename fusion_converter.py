import streamlit as st
import pandas as pd
import os
import json
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime
import pytz
from matplotlib.dates import DateFormatter

def process_tx_json(file_path):
    """Processes a JSON file and converts it to a DataFrame."""
    with open(file_path, 'r') as file:
        data = file.readlines()

    processed_data = []

    for line in data:
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
                            "ReceiveTimestampUtc": update.get("ReceiveTimestampUtc"),
                            "Bookmaker": update.get("Bookmaker"),
                            "PeriodType": update.get("PeriodType"),
                            "PeriodNumber": update.get("PeriodNumber"),
                            "Type": update.get("Type"),
                            "PlayerParticipantId": update.get("PlayerParticipantId"),
                            "TeamParticipantId": update.get("TeamParticipantId"),
                        })
                        for field in fields:
                            record[field] = update.get(field)

                        processed_data.append(record)

    df = pd.DataFrame(processed_data)

    def convert_timezone(utc_time_str, timezone):
        if pd.isnull(utc_time_str):
            return None
        utc_time_str = utc_time_str.rstrip('Z')  
        utc_time = datetime.fromisoformat(utc_time_str)
        utc_time = pytz.utc.localize(utc_time)  
        return utc_time.astimezone(pytz.timezone(timezone))

    df['ReceiveTimestampEastern'] = df['ReceiveTimestampUtc'].apply(lambda x: convert_timezone(x, "US/Eastern"))
    df['ReceiveTimestampCentral'] = df['ReceiveTimestampUtc'].apply(lambda x: convert_timezone(x, "US/Central"))
    df['ReceiveTimestampPacific'] = df['ReceiveTimestampUtc'].apply(lambda x: convert_timezone(x, "US/Pacific"))

    # Avoid division by zero errors
    df['HomeTrueProb'] = df.apply(lambda row: (1 / row['HomePrice']) if 'HomePrice' in row and row['HomePrice'] not in [0, None, ""] else None, axis=1)
    df['OverTrueProb'] = df.apply(lambda row: (1 / row['OverPrice']) if 'OverPrice' in row and row['OverPrice'] not in [0, None, ""] else None, axis=1)

    # Keep only specified columns
    columns_to_return = [
        'FixtureId', 'market_type', 'PeriodType', 'PeriodNumber', 'Bookmaker', 'Type', 'Line', 
        'PlayerParticipantId', 'TeamParticipantId', 'HomeTrueProb', 'OverTrueProb', 
        'ReceiveTimestampEastern', 'ReceiveTimestampCentral', 'ReceiveTimestampPacific'
    ]
    df = df[[col for col in columns_to_return if col in df.columns]]

    return df

def main():
    st.title("TXOdds Fusion Converter")

    st.write("""
    Upload a TXOdds Fusion JSON file to analyze bookmaker data over time (Pre-Live or Live). 
    Filter results, generate a graph, and download a CSV table.
    """)

    st.markdown("""
    ### How to Use:
    1. **Download a TXOdds Fusion JSON file**  
    - The file should follow this format:  
        **all-archive-production-3055810275-Feeds.TxOdds.Fusion.CollegeBasketball.InPlay.Events**  
    - If the file name is different, it is NOT the correct file.  
    
    2. **Upload the JSON file below.**

    3. **Apply filters** (optional)  
    - Select relevant **markets, players, lines, etc.** to refine the data/graph.  
    """)

    uploaded_file = st.file_uploader("Upload JSON file", type=["json"])

    if uploaded_file is not None:
        with st.spinner("Processing..."):
            try:
                temp_path = "temp_uploaded.json"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                df = process_tx_json(temp_path)

                if df.empty:
                    st.warning("No data found in the uploaded file.")
                    return

                # Extract unique values for dynamic dropdowns
                market_types = ["Select Market Type"] + sorted(df["market_type"].dropna().unique().tolist())
                period_types = ["Select PeriodType"]
                period_numbers = ["Select PeriodNumber"]
                types = ["Select Type"]
                player_participants = ["Select PlayerParticipantId"]
                line_options = ["Select Line"]

                # Initialize filters
                period_type = None
                period_number = None
                type_filter = None
                player_participant_id = None
                line = None

                # Create dropdowns for filters
                market_type = st.selectbox("Market Type", options=market_types)

                if market_type != "Select Market Type":
                    period_types += sorted(df[df["market_type"] == market_type]["PeriodType"].dropna().astype(str).unique().tolist())
                    period_type = st.selectbox("Period Type", options=period_types)

                    if period_type != "Select PeriodType":
                        period_numbers += sorted(df[(df["market_type"] == market_type) & (df["PeriodType"] == period_type)]["PeriodNumber"].dropna().unique().tolist())
                        period_number = st.selectbox("Period Number", options=period_numbers)

                        if period_number != "Select PeriodNumber":
                            if market_type in ["TotalsUpdates", "SpreadUpdates"]:
                                line_options += sorted(df[(df["market_type"] == market_type) & (df["PeriodType"] == period_type) & (df["PeriodNumber"] == period_number)]["Line"].dropna().unique().tolist())
                                line = st.selectbox("Line", options=line_options)

                            elif market_type == "PlayerOverUnderUpdates":
                                types += sorted(df[(df["market_type"] == market_type) & (df["PeriodType"] == period_type) & (df["PeriodNumber"] == period_number)]["Type"].dropna().unique().tolist())
                                type_filter = st.selectbox("Type", options=types)

                                if type_filter != "Select Type":
                                    player_participants += sorted(df[(df["market_type"] == market_type) & (df["PeriodType"] == period_type) & (df["PeriodNumber"] == period_number) & (df["Type"] == type_filter)]["PlayerParticipantId"].dropna().unique().tolist())
                                    player_participant_id = st.selectbox("Player Participant ID", options=player_participants)

                                    if player_participant_id != "Select PlayerParticipantId":
                                        line_options += sorted(df[(df["market_type"] == market_type) & (df["PeriodType"] == period_type) & (df["PeriodNumber"] == period_number) & (df["Type"] == type_filter) & (df["PlayerParticipantId"] == player_participant_id)]["Line"].dropna().unique().tolist())
                                        line = st.selectbox("Line", options=line_options)

                # Apply filters
                filters = {}
                for col, value in [("market_type", market_type), ("PeriodType", period_type),
                                ("PeriodNumber", period_number), ("Type", type_filter), ("PlayerParticipantId", player_participant_id), ("Line", line)]:
                    if value and value != f"Select {col.replace('_', ' ')}":
                        filters[col] = value

                filtered_df = df.copy()
                for column, value in filters.items():
                    if column in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df[column] == value]

                if not filtered_df.empty:
                    st.write("### Processed Data Preview:")
                    st.dataframe(filtered_df)

                    # Add multi-select for bookmakers
                    available_bookmakers = filtered_df["Bookmaker"].unique().tolist()
                    selected_bookmakers = st.multiselect("Select Bookmakers to Display", options=available_bookmakers, default=available_bookmakers)

                    # Filter the dataframe based on selected bookmakers
                    filtered_df = filtered_df[filtered_df["Bookmaker"].isin(selected_bookmakers)]

                    # Graph Conditions
                    make_graph = (
                        (market_type == "MoneylineUpdates" and period_type != "Select PeriodType") or
                        (market_type in ["TotalsUpdates", "SpreadUpdates"] and line != "Select Line" and period_type != "Select PeriodType" and period_number != "Select PeriodNumber") or
                        (market_type in ["PlayerYesNoUpdates", "PlayerOverUnderUpdates", "PlayerNthUpdates", "PlayerOverUpdates"] and player_participant_id != "Select PlayerParticipantId" and line != "Select Line")
                    )

                    if make_graph:
                        y_axis = "HomeTrueProb" if market_type == "MoneylineUpdates" else "OverTrueProb"

                        # Generate dynamic title (excluding unselected filters)
                        title_parts = [market_type] + [
                            f"{label}: {value}" for label, value in [
                                ("Line", line), ("Period Type", period_type), ("Period Number", period_number),
                                ("Player ID", player_participant_id), ("Type", type_filter)
                            ] if value and value not in ["Select Line", "Select PeriodType", "Select PeriodNumber", "Select PlayerParticipantId", "Select Type"]
                        ]

                        title = " | ".join(title_parts)
                        fixture_id = filtered_df["FixtureId"].iloc[0] if "FixtureId" in filtered_df.columns else "Unknown Fixture"

                        plt.figure(figsize=(10, 6))
                        sns.scatterplot(data=filtered_df, x="ReceiveTimestampPacific", y=y_axis, hue="Bookmaker")
                        plt.xticks(rotation=45)
                        plt.suptitle(title, fontsize=14, fontweight='bold')
                        plt.title(f"Fixture ID: {fixture_id}", fontsize=10)
                        plt.xlabel("Timestamp (Pacific Time)")
                        plt.ylabel("True Probability (%)")
                        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x * 100:.0f}%'))

                        # Format x-axis to show only the time
                        time_formatter = DateFormatter("%H:%M:%S", tz=pytz.timezone("US/Pacific"))
                        plt.gca().xaxis.set_major_formatter(time_formatter)

                        # Move the legend outside the plot
                        plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left')

                        st.pyplot(plt)
                        
                    csv = filtered_df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download CSV", csv, "processed_betting_data.csv", "text/csv")

            except Exception as e:
                st.error(f"Error processing file: {e}")

if __name__ == "__main__":
    main()