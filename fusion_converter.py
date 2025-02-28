# import streamlit as st
# import pandas as pd
# import os
# import json
# from datetime import datetime
# import pytz

# def process_tx_json(file_path, start_time=None, end_time=None, **filters):
#     """
#     Processes a JSON file containing sports betting updates and converts it to a DataFrame with optional filtering.
#     """
#     with open(file_path, 'r') as file:
#         data = file.readlines()

#     processed_data = []

#     for line in data:
#         line = line.strip()
#         if line and line.startswith('{') and line.endswith('}'):
#             try:
#                 json_data = json.loads(line)
#             except json.JSONDecodeError as e:
#                 print(f"Failed to decode JSON: {e}")
#                 continue 

#             common_data = {
#                 "FixtureId": json_data["FixtureId"]["Id"],
#                 "ClientId": json_data["FixtureId"]["ClientId"],
#                 "IsOfferedInPlay": json_data["IsOfferedInPlay"],
#             }

#             market_types = {
#                 "TotalsUpdates": ["Line", "OverPrice", "UnderPrice"],
#                 "MoneylineUpdates": ["HomePrice", "AwayPrice"],
#                 "SpreadUpdates": ["Line", "HomePrice", "AwayPrice"],
#                 "PlayerYesNoUpdates": ["Line"],
#                 "PlayerOverUnderUpdates": ["AggregateType", "PlayerParticipantId", "TeamParticipantId", "Line", "OverPrice", "UnderPrice"],
#                 "PlayerNthUpdates": ["Line"],
#                 "PlayerOverUpdates": ["Line"],
#             }

#             for market_type, fields in market_types.items():
#                 if json_data.get(market_type):
#                     for update in json_data[market_type]:
#                         record = {**common_data, "market_type": market_type}
#                         record.update({
#                             "LastUpdateTimestampUtc": update.get("LastUpdateTimestampUtc"),
#                             "ReceiveTimestampUtc": update.get("ReceiveTimestampUtc"),
#                             "EventId": update.get("EventId"),
#                             "PeriodType": update.get("PeriodType"),
#                             "PeriodNumber": update.get("PeriodNumber"),
#                             "Bookmaker": update.get("Bookmaker"),
#                             "Type": update.get("Type"),
#                             "IsSuspended": update.get("IsSuspended"),
#                             "SourceBookmaker": update.get("SourceBookmaker"),
#                         })
#                         for field in fields:
#                             record[field] = update.get(field)

#                         processed_data.append(record)

#     df = pd.DataFrame(processed_data)

#     def convert_timezone(utc_time_str, timezone):
#         if pd.isnull(utc_time_str):
#             return None
#         utc_time_str = utc_time_str.rstrip('Z')  
#         utc_time = datetime.fromisoformat(utc_time_str)
#         utc_time = pytz.utc.localize(utc_time)  
#         return utc_time.astimezone(pytz.timezone(timezone))

#     df['ReceiveTimestampEastern'] = df['ReceiveTimestampUtc'].apply(lambda x: convert_timezone(x, "America/New_York"))
#     df['ReceiveTimestampCentral'] = df['ReceiveTimestampUtc'].apply(lambda x: convert_timezone(x, "US/Central"))
#     df['ReceiveTimestampPacific'] = df['ReceiveTimestampUtc'].apply(lambda x: convert_timezone(x, "US/Pacific"))

#     for tz_col in ['ReceiveTimestampEastern', 'ReceiveTimestampCentral', 'ReceiveTimestampPacific']:
#         df[f'{tz_col}_HMS'] = df[tz_col].apply(lambda x: x.strftime('%H:%M:%S') if pd.notnull(x) else None)

#     df['MarginHome'] = 1 / df['AwayPrice'] + 1 / df['HomePrice']
#     df['HomeTrueProb'] = (1 / df['HomePrice']) / df['MarginHome']
#     df['HomeTruePrice'] = 1 / df['HomeTrueProb']

#     df['MarginUnder'] = 1 / df['UnderPrice'] + 1 / df['OverPrice']
#     df['OverTrueProb'] = (1 / df['OverPrice']) / df['MarginUnder']
#     df['OverTruePrice'] = 1 / df['OverTrueProb']

#     df = df[df['IsSuspended'] == False]

#     if filters:
#         for column, value in filters.items():
#             if column in df.columns:
#                 df = df[df[column] == value]

#     if start_time or end_time:
#         df['ReceiveTimestampPacific_HMS'] = pd.to_datetime(df['ReceiveTimestampPacific_HMS'], format='%H:%M:%S')

#         if start_time:
#             start_time_dt = datetime.strptime(start_time, "%H:%M:%S").time()
#             df = df[df['ReceiveTimestampPacific_HMS'].dt.time >= start_time_dt]

#         if end_time:
#             end_time_dt = datetime.strptime(end_time, "%H:%M:%S").time()
#             df = df[df['ReceiveTimestampPacific_HMS'].dt.time <= end_time_dt]

#     columns_to_return = [
#         'FixtureId', 'market_type', 'PeriodType', 'PeriodNumber', 'Bookmaker', 'Type', 'Line', 
#         'PlayerParticipantId', 'TeamParticipantId', 'HomeTrueProb', 'OverTrueProb', 
#         'ReceiveTimestampEastern', 'ReceiveTimestampCentral', 'ReceiveTimestampPacific'
#     ]
#     df = df[[col for col in columns_to_return if col in df.columns]]

#     return df

# def main():
#     st.title("TXOdds Fusion Converter")
#     st.write("Upload a JSON file and apply optional filters - if you don't provide a filter, all data will be processed.")
    
#     uploaded_file = st.file_uploader("Upload JSON file", type=["json"])
    
#     market_types = [
#         "MoneylineUpdates", "TotalsUpdates", "SpreadUpdates", 
#         "PlayerYesNoUpdates", "PlayerOverUnderUpdates", "PlayerNthUpdates", "PlayerOverUpdates"
#     ]
    
#     period_types = [
#         "Quarter", "Half", "Full", "Inning", "AfterInning", "Period"
#     ]
    
#     bookmakers = [
#         "DraftKingsNJ", "Bovada", "fonbet", "IBCbet", "BetMGM", "Coral", 
#         "PRIV.918Bet", "WilliamHillNJ", "TopSport", "978Bet", "Fanduel SB", 
#         "ladbrokes", "BetOnline", "willhill", "188bet"
#     ]

#     market_type = st.selectbox("Market Type", options=["Select Market Type"] + market_types)
#     period_type = st.selectbox("Period Type", options=["Select Period Type"] + period_types)
#     bookmaker = st.selectbox("Bookmaker", options=["Select Bookmaker"] + bookmakers)

#     start_time = st.text_input("Start Time (HH:MM:SS) - Pacific Time")
#     end_time = st.text_input("End Time (HH:MM:SS) - Pacific Time")

#     filters = {}
#     if market_type != "Select Market Type":
#         filters["market_type"] = market_type
#     if period_type != "Select Period Type":
#         filters["PeriodType"] = period_type
#     if bookmaker != "Select Bookmaker":
#         filters["Bookmaker"] = bookmaker

#     if uploaded_file is not None and st.button("Process File"):
#         with st.spinner("Processing..."):
#             try:
#                 temp_path = "temp_uploaded.json"
#                 with open(temp_path, "wb") as f:
#                     f.write(uploaded_file.getbuffer())

#                 df = process_tx_json(temp_path, start_time=start_time or None, end_time=end_time or None, **filters)

#                 st.write("### Processed Data Preview:")
#                 st.dataframe(df.head())
                
#                 csv = df.to_csv(index=False).encode('utf-8')
#                 st.download_button(
#                     label="Download CSV",
#                     data=csv,
#                     file_name="processed_betting_data.csv",
#                     mime="text/csv"
#                 )
#             except Exception as e:
#                 st.error(f"Error processing file: {e}")

# if __name__ == "__main__":
#     main()





############################################################################################################################################################################################################################################################

# import streamlit as st
# import pandas as pd
# import os
# import json
# import matplotlib.pyplot as plt
# import seaborn as sns
# from datetime import datetime
# import pytz

# def process_tx_json(file_path, start_time=None, end_time=None, **filters):
#     """
#     Processes a JSON file containing sports betting updates and converts it to a DataFrame with optional filtering.
#     """
#     with open(file_path, 'r') as file:
#         data = file.readlines()

#     processed_data = []

#     for line in data:
#         line = line.strip()
#         if line and line.startswith('{') and line.endswith('}'):
#             try:
#                 json_data = json.loads(line)
#             except json.JSONDecodeError as e:
#                 print(f"Failed to decode JSON: {e}")
#                 continue 

#             common_data = {
#                 "FixtureId": json_data["FixtureId"]["Id"],
#                 "ClientId": json_data["FixtureId"]["ClientId"],
#                 "IsOfferedInPlay": json_data["IsOfferedInPlay"],
#             }

#             market_types = {
#                 "TotalsUpdates": ["Line", "OverPrice", "UnderPrice"],
#                 "MoneylineUpdates": ["HomePrice", "AwayPrice"],
#                 "SpreadUpdates": ["Line", "HomePrice", "AwayPrice"],
#                 "PlayerYesNoUpdates": ["Line"],
#                 "PlayerOverUnderUpdates": ["AggregateType", "PlayerParticipantId", "TeamParticipantId", "Line", "OverPrice", "UnderPrice"],
#                 "PlayerNthUpdates": ["Line"],
#                 "PlayerOverUpdates": ["Line"],
#             }

#             for market_type, fields in market_types.items():
#                 if json_data.get(market_type):
#                     for update in json_data[market_type]:
#                         record = {**common_data, "market_type": market_type}
#                         record.update({
#                             "ReceiveTimestampUtc": update.get("ReceiveTimestampUtc"),
#                             "Bookmaker": update.get("Bookmaker"),
#                             "PeriodType": update.get("PeriodType"),
#                             "PeriodNumber": update.get("PeriodNumber"),
#                             "Type": update.get("Type"),
#                             "PlayerParticipantId": update.get("PlayerParticipantId"),
#                             "TeamParticipantId": update.get("TeamParticipantId"),
#                         })
#                         for field in fields:
#                             record[field] = update.get(field)

#                         processed_data.append(record)

#     df = pd.DataFrame(processed_data)

#     def convert_timezone(utc_time_str, timezone):
#         if pd.isnull(utc_time_str):
#             return None
#         utc_time_str = utc_time_str.rstrip('Z')  
#         utc_time = datetime.fromisoformat(utc_time_str)
#         utc_time = pytz.utc.localize(utc_time)  
#         return utc_time.astimezone(pytz.timezone(timezone))

#     df['ReceiveTimestampPacific'] = df['ReceiveTimestampUtc'].apply(lambda x: convert_timezone(x, "US/Pacific"))

#     # Avoid division by zero errors
#     df['HomeTruePrice'] = df.apply(lambda row: (1 / row['HomePrice']) if 'HomePrice' in row and row['HomePrice'] not in [0, None, ""] else None, axis=1)
#     df['OverTruePrice'] = df.apply(lambda row: (1 / row['OverPrice']) if 'OverPrice' in row and row['OverPrice'] not in [0, None, ""] else None, axis=1)

#     # Ensure filtering is correctly applied
#     for column, value in filters.items():
#         if column in df.columns:
#             df = df[df[column] == value]

#     # Limit the displayed columns
#     columns_to_return = [
#         'FixtureId', 'market_type', 'PeriodType', 'PeriodNumber', 'Bookmaker', 'Type', 'Line',
#         'PlayerParticipantId', 'TeamParticipantId', 'HomeTruePrice', 'OverTruePrice', 
#         'ReceiveTimestampPacific'
#     ]
#     df = df[[col for col in columns_to_return if col in df.columns]]

#     return df

# def main():
#     st.title("TXOdds Fusion Converter")
#     st.write("Upload a JSON file and apply optional filters - if you don't provide a filter, all data will be processed.")
    
#     uploaded_file = st.file_uploader("Upload JSON file", type=["json"])
    
#     market_types = [
#         "MoneylineUpdates", "TotalsUpdates", "SpreadUpdates", 
#         "PlayerYesNoUpdates", "PlayerOverUnderUpdates", "PlayerNthUpdates", "PlayerOverUpdates"
#     ]
    
#     bookmakers = [
#         "DraftKingsNJ", "Bovada", "fonbet", "IBCbet", "BetMGM", "Coral", 
#         "PRIV.918Bet", "WilliamHillNJ", "TopSport", "978Bet", "Fanduel SB", 
#         "ladbrokes", "BetOnline", "willhill", "188bet"
#     ]

#     market_type = st.selectbox("Market Type", options=["Select Market Type"] + market_types)
#     bookmaker = st.selectbox("Bookmaker", options=["Select Bookmaker"] + bookmakers)

#     start_time = st.text_input("Start Time (HH:MM:SS)")
#     end_time = st.text_input("End Time (HH:MM:SS)")

#     filters = {}
#     if market_type != "Select Market Type":
#         filters["market_type"] = market_type
#     if bookmaker != "Select Bookmaker":
#         filters["Bookmaker"] = bookmaker

#     if uploaded_file is not None and st.button("Process File"):
#         with st.spinner("Processing..."):
#             try:
#                 temp_path = "temp_uploaded.json"
#                 with open(temp_path, "wb") as f:
#                     f.write(uploaded_file.getbuffer())

#                 df = process_tx_json(temp_path, start_time=start_time or None, end_time=end_time or None, **filters)

#                 st.write("### Processed Data Preview:")
#                 st.dataframe(df)

#                 csv = df.to_csv(index=False).encode('utf-8')
#                 st.download_button(
#                     label="Download CSV",
#                     data=csv,
#                     file_name="processed_betting_data.csv",
#                     mime="text/csv"
#                 )

#                 # Plot graph ONLY if a market type is selected and valid data exists
#                 if market_type != "Select Market Type" and not df.empty:
#                     st.write("### Price Trends Over Time")

#                     # Determine the Y-axis column based on market type
#                     y_column = "HomeTruePrice" if market_type in ["MoneylineUpdates", "SpreadUpdates"] else "OverTruePrice"

#                     # Filter valid rows
#                     df = df.dropna(subset=['ReceiveTimestampPacific', y_column])

#                     if not df.empty:
#                         # Plot the graph with Bookmaker as hue
#                         fig, ax = plt.subplots(figsize=(10, 5))
#                         sns.lineplot(data=df, x='ReceiveTimestampPacific', y=y_column, hue='Bookmaker', marker="o", ax=ax)
                        
#                         ax.set_title(f"{y_column} Over Time by Bookmaker")
#                         ax.set_xlabel("Receive Timestamp (Pacific Time)")
#                         ax.set_ylabel(y_column)
#                         ax.tick_params(axis='x', rotation=45)
#                         ax.grid()

#                         st.pyplot(fig)
#                     else:
#                         st.warning("No valid data available for the selected market type.")

#             except Exception as e:
#                 st.error(f"Error processing file: {e}")

# if __name__ == "__main__":
#     main()


############################################################################################################################################################################################################################################################


import streamlit as st
import pandas as pd
import os
import json
# import matplotlib.pyplot as plt
# import seaborn as sns
from datetime import datetime
import pytz

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
    st.write("Upload a JSON file and apply optional filters.")

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
                bookmakers = ["Select Bookmaker"] + sorted(df["Bookmaker"].dropna().unique().tolist())
                period_types = ["Select PeriodType"] + sorted(df["PeriodType"].dropna().astype(str).unique().tolist())
                period_numbers = ["Select PeriodNumber"] + sorted(df["PeriodNumber"].dropna().astype(str).unique().tolist())
                player_participants = ["Select PlayerParticipantId"] + sorted(df["PlayerParticipantId"].dropna().astype(str).unique().tolist())
                lines = ["Select Line"] + sorted(df["Line"].dropna().astype(str).unique().tolist())

                # Create dropdowns for filters
                market_type = st.selectbox("Market Type", options=market_types)
                bookmaker = st.selectbox("Bookmaker", options=bookmakers)
                period_type = st.selectbox("Period Type", options=period_types)
                period_number = st.selectbox("Period Number", options=period_numbers)
                player_participant_id = st.selectbox("Player Participant ID", options=player_participants)
                line = st.selectbox("Line", options=lines)

                start_time = st.text_input("Start Time (HH:MM:SS)")
                end_time = st.text_input("End Time (HH:MM:SS)")

                # Apply filters
                filters = {}
                if market_type != "Select Market Type":
                    filters["market_type"] = market_type
                if bookmaker != "Select Bookmaker":
                    filters["Bookmaker"] = bookmaker
                if period_type != "Select PeriodType":
                    filters["PeriodType"] = period_type
                if period_number != "Select PeriodNumber":
                    filters["PeriodNumber"] = period_number
                if player_participant_id != "Select PlayerParticipantId":
                    filters["PlayerParticipantId"] = player_participant_id
                if line != "Select Line":
                    filters["Line"] = line

                filtered_df = df.copy()
                for column, value in filters.items():
                    if column in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df[column] == value]

                st.write("### Processed Data Preview:")
                st.dataframe(filtered_df)

                csv = filtered_df.to_csv(index=False).encode('utf-8')
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
