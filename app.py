# app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd
import zipfile
import requests
import io
import os

# Load your dataset
@st.cache_data
def load_data():
    return pd.read_parquet('processed_data.parquet')
      
# Load data
merged_df_trim_filter01 = load_data()


# Title
st.title('🏡 Orange County NC Property Tax Value Distribution Exploration')

st.markdown("""
Recently, where I live in NC, there has been a lot of talk about property taxes. [INSERT LINKS]

I thought it would be interesting to see different property values have evolved from 2024 to 2025, and how they compare to each other in my county (Orange County NC). So, I used the publicly available Orange County GIS data to get the value of my property and compare it to the rest of the county.

Below I'll provide some data that I found interesting, and at the bottom you can see how your property compares to others in Orange County.

""")

st.markdown("---")

st.markdown("""
First, some basics on what data is included and what is not included.

**Where is the data sourced?**

Nicely, Orange County Publishes all of this data on their website (https://www.orangecountync.gov/2057/Download-GIS-Data). Full data for 2024 and previous years is on the site, but they were kind enough to supply preliminary 2025 data by email.

**Does this include all properties in Orange County NC?**

No! For simplicity, and because I wanted to focus on housing, I trimmed out a few types of properties:

1. **Non Zero Tax Exemptions** This primarily includes out schools and other tax exempt locations.
2. **Land only plots** There is a LOT of land in Chapel Hill which doesn't have any buildings. It's been trimmed out.
3. **Duplicates:** I wasn't sure exactly how to handle this, but there are more than a few duplicates Parcels in the data which are mostly similar. It's a relatively small amount, but only one was chosen.

In sum, this leaves us with around 40K property locations in Orange County, down from around 62K. I should note that this data also includes a lot of other quirks which I don't fully understand, nor will likely ever understand. As the 2025 data is also preliminary, it is also likely to change and get cleaner over time.

Before we go deeper, we should check if this data makes sense. The following figure shows the median appraised value for each zip code in Orange County. Two zip codes had under 10 properties, so I filtered them out (27312 and 27515). As expected, the locations that are closer to the town center of chapel hill have higher valuations:

""")


# Load data
orange = gpd.read_parquet('orange.parquet')
zip_map = gpd.read_parquet('zip_map.parquet')


# 1. Ensure ZIP GeoDataFrame has projected CRS
zip_map_proj = zip_map.to_crs(epsg=3857)  # shading layer with value
zip_boundaries = zip_map_proj.copy()
zip_boundaries["geometry"] = zip_boundaries["geometry"].boundary  # outlines only

# 2. Reproject Orange County boundary
orange_proj = orange.to_crs(epsg=3857)

# 3. Plot
fig, ax = plt.subplots(figsize=(10, 10))

# Fill ZIPs with shading by appraisal value
zip_map_proj.plot(
    column="AvgAppraisalValue",
    cmap="OrRd",
    linewidth=0,
    ax=ax,
    legend=False,
    legend_kwds={"label": "Avg Appraised Value", "shrink": 0.6}
)

# ZIP code boundary lines
zip_boundaries.plot(ax=ax, linewidth=1, edgecolor="black")

# County boundary
orange_proj.boundary.plot(ax=ax, linewidth=2, edgecolor="blue")

# ZIP code labels
for idx, row in zip_map_proj.iterrows():
    if pd.notnull(row["AvgAppraisalValue"]) and row.geometry.centroid.is_valid:
        centroid = row.geometry.centroid
        label = f"{row['ZIP']}\n${row['AvgAppraisalValue']:,.0f}"
        ax.text(
            centroid.x,
            centroid.y,
            label,
            fontsize=8,
            ha="center",
            va="center",
            color="black"
        )

# Clean layout
ax.set_title("Median Appraised Value by ZIP in Orange County, NC", fontsize=14)
ax.axis("off")
plt.tight_layout()
st.pyplot(fig)


st.markdown("---")

st.markdown("""
**Next, have property valuations really increased in the county, and if so, by how much?**

There is no question that property values have increased. In sum, property values have increased by around 55% in 2025. However, there is also a lot of variation. While almost no properties had lower value valuations, there were a rather larger number of properties that actually had valuations increase 2X, 5X and a few even by 10X!

The below histogram gives a quick visual of the valuation change from 2024 to 2025. The mode is 55% and the median is XXX, and there is clearly a long tail. Why? that's not clear. Some of these could be data errors, but it's mostly likely changes due to additions and other hyper locale factors.

""")
# Assuming `merged_df_trim_filter01` is already loaded with relevant columns
selected = merged_df_trim_filter01[[
    'TotalAppraisedValue_percent',
    'TotalAppraisedValue',
]]

# Create summary statistics table
summary = selected.agg([
    'mean',
    lambda x: x.quantile(0.25),
    'median',
    lambda x: x.quantile(0.75)
])

# Rename index for clarity
summary.index = ['Mean', '25th Percentile','Median', '75th Percentile']

# Transpose and round for display
summary = summary.transpose().round(3)

st.dataframe(summary)


st.markdown("""
**What factors most correlate with the increase in value?**

It turns out that factors like age or square footage don't seem to have a huge impact on the change in value. However, it is clear that changes in building values and land values have gone up at extremely different rates. The tax office finds that building values should increase by roughly 25%, while land values are closer to 100% (i.e. double). This also means that property owners who have a lot of land are likely to pay a higher share of property taxes in the future and that home owners on relatively small plots of land will likely pay less, relatively.


""")




st.markdown("---")

st.markdown("""
To see how your property compares to the distribution of others in Orange County, enter your **PIN** below:
""")

# Set up PIN lookup
pin_lookup = merged_df_trim_filter01.set_index('ParcelID')

# User input
user_pin = st.text_input('🔎 Enter your PIN:', '')






# Set up plot for Comparing input pin to Total Appraised Value
fig1, ax = plt.subplots(figsize=(10, 6))

# Calculate lower and upper bounds
lower = merged_df_trim_filter01['TotalAppraisedValue_percent'].quantile(0.01)
upper = merged_df_trim_filter01['TotalAppraisedValue_percent'].quantile(0.99)

# If the user entered a valid PIN
if user_pin:
    if user_pin in pin_lookup.index:
        user_value = pin_lookup.loc[user_pin, 'TotalAppraisedValue_percent']
        user_value2 = pin_lookup.loc[user_pin, 'TotalAppraisedValue']
        
        # Only plot if user_value is within bounds
        if lower <= user_value <= upper:
            ax.axvline(user_value, color='red', linestyle='--', linewidth=2, label='🔴 Your Value')
            st.success(f"PIN `{user_pin}` has a change in Total Appraisal Value of **{user_value:.2f}**X, and is currently **${round(user_value2):,}**.")
        else:
            st.warning("Your value is outside the trimmed display range.")
    else:
        st.error("PIN not found. Please check your entry.")


# Filter values within bounds
filtered = merged_df_trim_filter01['TotalAppraisedValue_percent']
filtered = filtered[(filtered >= lower) & (filtered <= upper)]

# Plot
filtered.dropna().hist(bins=100, edgecolor='black')
plt.title('Trimmed Distribution of TotalAppraisedValue_percent')
plt.xlabel('Value')
plt.ylabel('Frequency')
plt.tight_layout()
st.pyplot(fig1)




# Set up plot for Comparing input pin to Total Building Appraised Value
fig2, ax = plt.subplots(figsize=(10, 6))

# Calculate lower and upper bounds
lower = merged_df_trim_filter01['TotalAppraisedBuildingValue_percent'].quantile(0.01)
upper = merged_df_trim_filter01['TotalAppraisedBuildingValue_percent'].quantile(0.99)

# If the user entered a valid PIN
if user_pin:
    if user_pin in pin_lookup.index:
        user_value = pin_lookup.loc[user_pin, 'TotalAppraisedBuildingValue_percent']
        user_value2 = pin_lookup.loc[user_pin, 'TotalAppraisedBuildingValue']
        
        # Only plot if user_value is within bounds
        if lower <= user_value <= upper:
            ax.axvline(user_value, color='red', linestyle='--', linewidth=2, label='🔴 Your Value')
            st.success(f"PIN `{user_pin}` has a change in Building Appraisal Value of: **{user_value:.2f}**X, and is currently **${round(user_value2):,}**.")
        else:
            st.warning("Your value is outside the trimmed display range.")
    else:
        st.error("PIN not found. Please check your entry.")
    
# Filter values within bounds
filtered = merged_df_trim_filter01['TotalAppraisedBuildingValue_percent']
filtered = filtered[(filtered >= lower) & (filtered <= upper)]

# Plot
filtered.dropna().hist(bins=100, edgecolor='black')
plt.title('Trimmed Distribution of TotalAppraisedBuildingValue_percent')
plt.xlabel('Value')
plt.ylabel('Frequency')
plt.tight_layout()
st.pyplot(fig2)



# Set up plot for Comparing input pin to Total Land Appraised Value
fig3, ax = plt.subplots(figsize=(10, 6))

# Calculate lower and upper bounds
lower = merged_df_trim_filter01['TotalAppraisedLandValue_percent'].quantile(0.01)
upper = merged_df_trim_filter01['TotalAppraisedLandValue_percent'].quantile(0.99)

# If the user entered a valid PIN
if user_pin:
    if user_pin in pin_lookup.index:
        user_value = pin_lookup.loc[user_pin, 'TotalAppraisedLandValue_percent']
        user_value2 = pin_lookup.loc[user_pin, 'TotalAppraisedLandValue']
        
        # Only plot if user_value is within bounds
        if lower <= user_value <= upper:
            ax.axvline(user_value, color='red', linestyle='--', linewidth=2, label='🔴 Your Value')
            st.success(f"PIN `{user_pin}` has a change in Building Appraisal Value of: **{user_value:.2f}**X, and is currently **${round(user_value2):,}**.")
        else:
            st.warning("Your value is outside the trimmed display range.")
    else:
        st.error("PIN not found. Please check your entry.")
    
# Filter values within bounds
filtered = merged_df_trim_filter01['TotalAppraisedLandValue_percent']
filtered = filtered[(filtered >= lower) & (filtered <= upper)]

# Plot
filtered.dropna().hist(bins=100, edgecolor='black')
plt.title('Trimmed Distribution of TotalAppraisedLandValue_percent')
plt.xlabel('Value')
plt.ylabel('Frequency')
plt.tight_layout()
st.pyplot(fig3)






















# # Set up plot for Comparing input pin to Total Appraised Value
# fig2, ax = plt.subplots(figsize=(10, 6))

# # Pre-calculate trimmed bounds
# lower = merged_df_trim_filter01['TotalAppraisedBuildingValue_percent'].quantile(0.01)
# upper = merged_df_trim_filter01['TotalAppraisedBuildingValue_percent'].quantile(0.99)

# # Top 3 building types
# top_btypes = merged_df_trim_filter01['BldgTypeDescription'].value_counts().head(3).index

# # Plot normalized histograms
# for btype in top_btypes:
#     subset = merged_df_trim_filter01[
#         (merged_df_trim_filter01['BldgTypeDescription'] == btype) &
#         (merged_df_trim_filter01['TotalAppraisedBuildingValue_percent'] >= lower) &
#         (merged_df_trim_filter01['TotalAppraisedBuildingValue_percent'] <= upper)
#     ]['TotalAppraisedBuildingValue_percent'].dropna()
    
#     ax.hist(subset, bins=100, alpha=0.5, label=btype, edgecolor='black', linewidth=0.5, density=True)

# # If the user entered a valid PIN
# if user_pin:
#     if user_pin in pin_lookup.index:
#         user_value = pin_lookup.loc[user_pin, 'TotalAppraisedBuildingValue_percent']
        
#         # Only plot if user_value is within bounds
#         if lower <= user_value <= upper:
#             ax.axvline(user_value, color='red', linestyle='--', linewidth=2, label='🔴 Your Value')
#             st.success(f"Found PIN `{user_pin}` with Building Value Percent: **{user_value:.2f}**")
#         else:
#             st.warning("Your value is outside the trimmed display range.")
#     else:
#         st.error("PIN not found. Please check your entry.")

# # Final plot settings
# ax.set_title('Normalized Building Value Distribution (Top 3 Building Types)')
# ax.set_xlabel('Building Value Percent')
# ax.set_ylabel('Density')
# ax.legend(title='Building Type')
# plt.tight_layout()

# st.pyplot(fig2)

# Footer
st.markdown("---")