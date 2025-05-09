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
st.title('🏡 Exploration of the Property Tax Revaluation in Orange County NC')

st.markdown("""
Recently, where I live in Orange County North Carolina, there has been a lot of <a href="https://www.newsobserver.com/news/local/counties/orange-county/article300487814.html" target="_blank">talk about changes in the appraised value of homes that are used for calculating property taxes</a>.

I thought it would be interesting to see how residential property values have evolved from 2024 to 2025, and how they compare to each other in my county (Orange County NC). So, I used the publicly available Orange County GIS data to get the value of each property and compare them to others in the rest of the county.

Below I'll provide some data that I found interesting, and at the bottom you can see how changes in property values compares to general distribution found in Orange County.
""", unsafe_allow_html=True)
st.markdown("---")

st.markdown("""
**First, what is the revaluation process and why does it matter?**

I'm not going to go into the full details, but the Orange County website does a <a href="https://www.orangecountync.gov/878/Revaluation" target="_blank">great job</a> of describing the process and answering a lot of questions (<a href="https://www.orangecountync.gov/FAQ.aspx?TID=40" target="_blank">and here is an additional FAQ</a>). From a simple perspective, it is the following:

*"Revaluation is the process of updating all property tax assessments in Orange County to reflect market value as of a set date. For Orange County, this date is January 1, 2025. During this process, the tax office reassesses all real property, including land, buildings, and improvements. North Carolina law requires counties to revalue properties at least every eight years, Orange County follows a four-year revaluation cycle."*
""", unsafe_allow_html=True)
st.markdown("---")

st.markdown("""
Next up, some basics on the data itself, and what is and is not included in this analysis

**Where is the data sourced?**

Nicely, Orange County Publishes all of this data on their <a href="https://www.orangecountync.gov/2057/Download-GIS-Data" target="_blank">website</a>. Full data for 2024 and previous years is on the site, but they were kind enough to supply preliminary 2025 data by email.

**Does this include all properties in Orange County NC?**

No! For simplicity, and because I wanted to focus on residential housing, I trimmed out a few types of properties:

1. **Non Zero Tax Exemptions** This primarily includes out schools and similar tax exempt locations.
2. **Land only plots** There is a LOT of land in Chapel Hill which doesn't have any buildings. It's been trimmed out.
3. **Duplicates:** I wasn't sure exactly how to handle this, but there are more than a few duplicates Parcels in the data which are mostly similar. It's a relatively small amount, but only one was chosen.

In sum, this leaves us with around 40K property locations in Orange County, down from around 62K. I should note that this data also includes a lot of other quirks which I don't fully understand, nor will likely ever understand. As the 2025 data is also *preliminary*, it is also likely to change and get cleaner over time.

Before we go deeper, we should check if this data makes sense. The following figure shows the median appraised value for each zip code in Orange County. Two zip codes had under 10 properties, so I filtered them out (27312 and 27515). As expected, the locations that are closer to the town center of chapel hill have higher valuations (e.g. 27514):

""", unsafe_allow_html=True)


# Load data
orange = gpd.read_parquet('orange.parquet')
zip_map = gpd.read_parquet('zip_map.parquet')
zip_map["AppraisalValueChange"] = zip_map["AvgAppraisalValue"] / zip_map["AvgAppraisalValue_2024"] - 1


# 1. Ensure ZIP GeoDataFrame has projected CRS
zip_map_proj = zip_map.to_crs(epsg=3857)  # shading layer with value
zip_boundaries = zip_map_proj.copy()
zip_boundaries["geometry"] = zip_boundaries["geometry"].boundary  # outlines only

# 2. Reproject Orange County boundary
orange_proj = orange.to_crs(epsg=3857)

# 3. Plot
fig, ax = plt.subplots(figsize=(7,10))

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
**Next, does the data show that property valuations have increased in the county, and if so, by how much?**

Yes. For this set of properties, appraised values increased by around 58% in 2025. However, there is also a lot of variation (see figures below). While almost no properties had lower value valuations, there were a rather larger number of properties that actually had valuations increase 2X, 5X and a few even by 10X.

The table below shows a quick snapshot of the valuation change from 2024 to 2025.

""")



# Select and summarize
columns_to_summarize = ['TotalAppraisedValue_percent', 'TotalAppraisedValue']
selected_data = merged_df_trim_filter01[columns_to_summarize]

summary_stats = selected_data.agg([
    'mean',
    lambda x: x.quantile(0.25),
    'median',
    lambda x: x.quantile(0.75)
])

# Rename and transpose
summary_stats.index = ['Mean', '25th Percentile', 'Median', '75th Percentile']
summary_stats = summary_stats.transpose()

# Format values
#summary_stats.loc['TotalAppraisedValue_percent'] =(summary_stats.loc['TotalAppraisedValue_percent']-1).round(2)
summary_stats.loc['TotalAppraisedValue_percent'] = summary_stats.loc['TotalAppraisedValue_percent'].apply(
    lambda x: f"{x * 100-100:.1f}%"
)
summary_stats.loc['TotalAppraisedValue'] = summary_stats.loc['TotalAppraisedValue'].apply(lambda x: f"${x:,.0f}")
summary_stats.index = ['% Change in Appraisal Value', '2025 Appraised Value']

# Build HTML table with centered values
html_table = "<table style='width:100%; border-collapse:collapse; text-align:center;'>"

# Header row
html_table += "<thead><tr><th></th>"  # Empty top-left cell
for col in summary_stats.columns:
    html_table += f"<th>{col}</th>"
html_table += "</tr></thead><tbody>"

# Data rows
for row_name, row_vals in summary_stats.iterrows():
    html_table += f"<tr><td><strong>{row_name}</strong></td>"
    for val in row_vals:
        html_table += f"<td>{val}</td>"
    html_table += "</tr>"

html_table += "</tbody></table>"

# Display
st.markdown(html_table, unsafe_allow_html=True)


st.markdown("""
**Do these numbers seem to make sense?**

At a high level, the increase in residential real estate valuation estimated over the past 4 years from both <a href="https://www.redfin.com/city/3059/NC/Chapel-Hill/housing-market" target="_blank">Redfin</a> and <a href="https://www.zillow.com/home-values/17386/chapel-hill-nc/" target="_blank">Zillow</a> seem in line with the increase show in the tax revaluation.

""", unsafe_allow_html=True)





st.markdown("""
**What factors most correlate with the *increase* in value?**

*Do building characteristics such as Age or Square Footage matter?* It turns out, not so much. The correlation in the change of value is rather small to non-existent.

*What about Land and Building Values? Did they change at the same rate?* No. This is where we see big differences. It turns out that mean changes in building values and land values have gone up at extremely different rates. The tax office finds that, for this sample, building values should increase by roughly 43%, while land values are closer to 115% (i.e. more than double). This also means that property owners who have a lot of land are likely to pay a much higher share of property taxes in the future and that home owners on small plots of land will likely pay less, relatively.


""")


# Select and summarize
columns_to_summarize = ['TotalAppraisedLandValue_percent', 'TotalAppraisedBuildingValue_percent']
selected_data = merged_df_trim_filter01[columns_to_summarize]

# Compute summary statistics
summary_stats = selected_data.agg([
    'mean',
    lambda x: x.quantile(0.25),
    'median',
    lambda x: x.quantile(0.75)
])

# Rename index rows for clarity
summary_stats.index = ['Mean', '25th Percentile', 'Median', '75th Percentile']

# Transpose for display (rows = land/building, columns = summary stats)
summary_stats = summary_stats.transpose()

# Format as percent change (e.g., 1.25 → 25.0%)
summary_stats = summary_stats.applymap(lambda x: f"{x * 100 - 100:.1f}%")

# Rename row labels
summary_stats.index = ['% Change in Land Value', '% Change in Building Value']

# Build HTML table with centered values
html_table = "<table style='width:100%; border-collapse:collapse; text-align:center;'>"

# Header row
html_table += "<thead><tr><th></th>"
for col in summary_stats.columns:
    html_table += f"<th>{col}</th>"
html_table += "</tr></thead><tbody>"

# Data rows
for row_name, row_vals in summary_stats.iterrows():
    html_table += f"<tr><td><strong>{row_name}</strong></td>"
    for val in row_vals:
        html_table += f"<td>{val}</td>"
    html_table += "</tr>"

html_table += "</tbody></table>"

# Display
st.markdown(html_table, unsafe_allow_html=True)


st.markdown("""
This also means that if we average change in property values by zip code, we should see larger increases from the outside of town.

This is quite evident as the zip codes with less land (27514 and 27510) show a smaller increase than those farther outside of town."

""")


# 3. Plot
fig2, ax = plt.subplots(figsize=(7,10))

# Fill ZIPs with shading by appraisal value
zip_map_proj.plot(
    column="AppraisalValueChange",
    cmap="OrRd",
    linewidth=0,
    ax=ax,
    legend=False,
    legend_kwds={"label": "Change in Appraised Value", "shrink": 0.6}
)

# ZIP code boundary lines
zip_boundaries.plot(ax=ax, linewidth=1, edgecolor="black")

# County boundary
orange_proj.boundary.plot(ax=ax, linewidth=2, edgecolor="blue")

# ZIP code labels
for idx, row in zip_map_proj.iterrows():
    if pd.notnull(row["AppraisalValueChange"]) and row.geometry.centroid.is_valid:
        centroid = row.geometry.centroid
        label = f"{row['ZIP']}\n{row['AppraisalValueChange']*100:,.1f}%"
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
ax.set_title("Change in Appraised Value by ZIP in Orange County, NC", fontsize=14)
ax.axis("off")
plt.tight_layout()
st.pyplot(fig2)


st.markdown("---")

st.markdown("""
Of course, many individuals care about how changes in property valuation will compare to that of others in the county. If you want to see how any property compares to the distribution of others in Orange County, please go to the <a href="https://gis.orangecountync.gov/orangeNCGIS/default.htm">Orange County GIS website</a> to lookup the associated **PIN**, and then enter then enter that PIN below. This will show the change in that property's Total Valuation, Building Valuation and Land Valuation from 2024 to 2025.
""", unsafe_allow_html=True)

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
plt.title('Trimmed Distribution of the Change in Total Appraised Property Value')
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
plt.title('Trimmed Distribution of the Change in Total Appraised Building Value')
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
plt.title('Trimmed Distribution of the Change in Total Appraised Land Value')
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

st.markdown("""
**Wrap up**

Given the above, there are lots of potentially unanswered questions. One which still stands out to me is the "lumpiness" in the change in Land Valuation. While changes in building valuation seem to have a smooth curve, the changes in Land Valuation have many large jumps, most notably around 50%, 100% and a handful of other values. This suggests a rather coarse modeling.
""", unsafe_allow_html=True)
