# pre processing property tax data
# preprocess.py
import pandas as pd
import numpy as np


#loading key data from 2024 and 2025
df_2024 = pd.read_excel('/Users/isaacdinner/Documents/orange_gis/2024 Real Property Data Extract - Detailed - 20240828.xlsx', engine='openpyxl')
df_2025 = pd.read_excel('/Users/isaacdinner/Documents/orange_gis/2025 Real Property Data Extract - Detailed - PRELIMINARY - 20250324.xlsx', engine='openpyxl')

#trimming down the data to only include the key columns
df_2024_trim=df_2024[['ParcelID', 'TotalAppraisedValue', 'TotalAppraisedLandValue', 'TotalAppraisedBuildingValue','TotalFinishedArea','LandArea']]
df_2024_thin = df_2024_trim.rename(columns={
    'TotalAppraisedValue': 'TotalAppraisedValue_2024',
    'TotalAppraisedLandValue': 'TotalAppraisedLandValue_2024',
    'TotalAppraisedBuildingValue': 'TotalAppraisedBuildingValue_2024',
    'TotalFinishedArea':'TotalFinishedArea_2024',
    'LandArea':'LandArea_2024'
})

# Removing duplicate rows based on 'col1', keeping the last occurrence
df_2024_trim = df_2024_thin.drop_duplicates(subset=['ParcelID'], keep='first')

# Remove duplicate rows based on 'col1', keeping the last occurrence
df_2025_trim00 = df_2025.drop_duplicates(subset=['ParcelID'], keep='first')

# Removes tax exempt locations
df_2025_trim = df_2025_trim00[(df_2025_trim00['TotalValueExemption'] == 0)]

# Merging the two dataframes
merged_df = pd.merge(df_2024_trim, df_2025_trim, on='ParcelID', how='left')

# Filtering out further invalid values or locations with no buildings
merged_df_trim_filter01 = merged_df[(merged_df['LandArea_2024'] == merged_df['LandArea']) &
    (merged_df['TotalFinishedArea_2024'] == merged_df['TotalFinishedArea']) &
    (merged_df['TotalAppraisedValue_2024'] > 1) & 
    (merged_df['TotalAppraisedLandValue_2024'] > 1) & 
    (merged_df['TotalAppraisedBuildingValue_2024'] > 1)]


merged_df_trim_filter01 = merged_df_trim_filter01.copy() 

merged_df_trim_filter01['TotalAppraisedValue_percent'] = np.where(
    merged_df_trim_filter01['TotalAppraisedValue_2024'] > 1,
    merged_df_trim_filter01['TotalAppraisedValue'] / merged_df_trim_filter01['TotalAppraisedValue_2024'],
    np.nan
)

merged_df_trim_filter01['TotalAppraisedLandValue_percent'] = np.where(
    merged_df_trim_filter01['TotalAppraisedLandValue_2024'] > 1,
    merged_df_trim_filter01['TotalAppraisedLandValue'] / merged_df_trim_filter01['TotalAppraisedLandValue_2024'],
    np.nan
)

merged_df_trim_filter01['TotalAppraisedBuildingValue_percent'] = np.where(
    merged_df_trim_filter01['TotalAppraisedBuildingValue_2024'] > 1,
    merged_df_trim_filter01['TotalAppraisedBuildingValue'] / merged_df_trim_filter01['TotalAppraisedBuildingValue_2024'],
    np.nan
)

merged_df_trim_filter01['Percent_TotalAppraisedValue_from_building'] = np.where(
    merged_df_trim_filter01['TotalAppraisedBuildingValue_2024'] > 1,
    merged_df_trim_filter01['TotalAppraisedBuildingValue'] / merged_df_trim_filter01['TotalAppraisedValue'],
    np.nan
)


merged_df_trim_filter01

# Save to compressed, fast format
merged_df_trim_filter01.to_parquet('processed_data.parquet')  