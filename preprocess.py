# pre processing property tax data
# preprocess.py
import pandas as pd
import geopandas as gpd
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




#Creating second data set for the county visual
# Your appraisal DataFrame
df = merged_df_trim_filter01.copy()

#excluding small zips
excluded_zips = [27312, 27515]
df = df[~df["Zip"].isin(excluded_zips)]

# Calculate average appraisal value per ZIP
zip_avg = (
    df.groupby("Zip")[["TotalAppraisedValue","TotalAppraisedValue_2024"]]
    .median()
    .reset_index()
    .rename(columns={"Zip": "ZIP", "TotalAppraisedValue": "AvgAppraisalValue","TotalAppraisedValue_2024":"AvgAppraisalValue_2024"})
)
zip_avg["ZIP"] = zip_avg["ZIP"].astype('int')


# Load NC ZIP GeoJSON (lightweight)
geojson_url = "https://raw.githubusercontent.com/OpenDataDE/State-zip-code-GeoJSON/master/nc_north_carolina_zip_codes_geo.min.json"
zip_shapes = gpd.read_file(geojson_url)
zip_shapes["ZIP"] = zip_shapes["ZCTA5CE10"].astype('int')

# Merge your data with ZIP geometries
zip_map = zip_shapes.merge(zip_avg, on="ZIP", how="right")
zip_map = zip_map.dropna(subset=["geometry", "AvgAppraisalValue","AvgAppraisalValue_2024"])

# Load the county shapefile
county_shapefile = '/Users/isaacdinner/Documents/orange_gis/tl_2023_us_county.shp'
#df_2025 = pd.read_excel('/Users/isaacdinner/Documents/orange_gis/2025 Real Property Data Extract - Detailed - PRELIMINARY - 20250324.xlsx', engine='openpyxl')

counties = gpd.read_file(county_shapefile)

# Filter to Orange County, NC (state FIPS: 37, county FIPS: 135)
orange = counties[(counties["STATEFP"] == "37") & (counties["COUNTYFP"] == "135")]


zip_map.to_parquet('zip_map.parquet', index=False)
orange.to_parquet('orange.parquet', index=False)

