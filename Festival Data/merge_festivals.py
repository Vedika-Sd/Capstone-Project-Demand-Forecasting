<<<<<<< HEAD
import pandas as pd
import os

# folder where excel files exist
folder_path = r"G:\Sem - 6\CAPSTONE\Project\Raw data working\Festival Calenders"

all_data = []

# read every excel file
for file in os.listdir(folder_path):
    if file.endswith(".xlsx") or file.endswith(".xls"):
        
        file_path = os.path.join(folder_path, file)
        print(f"Reading: {file}")

        # read excel
        df = pd.read_excel(file_path)

        # ensure column names are clean
        df.columns = df.columns.str.strip()

        # convert Date column to only date (remove time part)
        df['date'] = pd.to_datetime(df['date']).dt.date

        # replace 'null' text with empty value
        df['festival'] = df['festival'].replace("null", "")

        # optional: remove completely empty rows
        df = df.dropna(how='all')

        all_data.append(df)

# merge all dataframes
merged_df = pd.concat(all_data, ignore_index=True)

# sort by date (important for forecasting later)
merged_df = merged_df.sort_values(by="date")

# save as CSV
output_path = r"G:\Sem - 6\CAPSTONE\Project\Raw data working\all_festivals.csv"
merged_df.to_csv(output_path, index=False)

print("Merged CSV created successfully")
=======
import pandas as pd
import os

# folder where excel files exist
folder_path = r"G:\Sem - 6\CAPSTONE\Project\Raw data working\Festival Calenders"

all_data = []

# read every excel file
for file in os.listdir(folder_path):
    if file.endswith(".xlsx") or file.endswith(".xls"):
        
        file_path = os.path.join(folder_path, file)
        print(f"Reading: {file}")

        # read excel
        df = pd.read_excel(file_path)

        # ensure column names are clean
        df.columns = df.columns.str.strip()

        # convert Date column to only date (remove time part)
        df['date'] = pd.to_datetime(df['date']).dt.date

        # replace 'null' text with empty value
        df['festival'] = df['festival'].replace("null", "")

        # optional: remove completely empty rows
        df = df.dropna(how='all')

        all_data.append(df)

# merge all dataframes
merged_df = pd.concat(all_data, ignore_index=True)

# sort by date (important for forecasting later)
merged_df = merged_df.sort_values(by="date")

# save as CSV
output_path = r"G:\Sem - 6\CAPSTONE\Project\Raw data working\all_festivals.csv"
merged_df.to_csv(output_path, index=False)

print("Merged CSV created successfully")
>>>>>>> f175916680c6f8974abba9ea46a29ce5cc4263de
print(f"Saved at: {output_path}")