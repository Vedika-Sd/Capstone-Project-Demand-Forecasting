import pandas as pd

sales = pd.read_csv("all_years_sales.csv")
festivals = pd.read_csv("all_festivals.csv")

# 2. Keep only useful columns
sales = sales[["DC_DATE", "PRODDESC", "DC_QTY_IN_UOM"]]

sales = sales.rename(columns={
    "DC_DATE": "Date",
    "PRODDESC": "Product",
    "DC_QTY_IN_UOM": "Quantity"
})

# Convert date format
sales["Date"] = pd.to_datetime(sales["Date"])
festivals["Date"] = pd.to_datetime(festivals["Date"])

# 4. Verify total quantity before aggregation
original_total = sales["Quantity"].sum()
print("Original quantity total:", original_total) 

# 5. Create daily time-series table per product
sales_daily = sales.groupby(
    ["Date", "Product"],
    as_index=False
)["Quantity"].sum()

# 6. Verify total quantity after aggregation
aggregated_total = sales_daily["Quantity"].sum()
print("Aggregated quantity total:", aggregated_total)

# 7. Merge with festival calendar Using Left join
final_data = pd.merge(
    sales_daily,
    festivals,
    on="Date",
    how="left"
)

# 8. Clean empty festival values
final_data["Festival"] = final_data["Festival"].fillna("")

# Sort for proper time-series order
final_data = final_data.sort_values(["Product", "Date"])

# 9. Save the final time-series data
final_data.to_csv("final_sales_with_festivals.csv", index=False)

print("Final dataset created successfully.")