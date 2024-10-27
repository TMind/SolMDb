import pandas as pd

# Sample data
data = {
    "Name": ["Alice", "Bob", "Charlie"],
    "Age": [25, 30, 35],
    "City": ["New York", "Los Angeles", "Chicago"]
}

# Create DataFrame
df = pd.DataFrame(data)

# Save DataFrame to a Parquet file
df.to_parquet("sample_table.parquet", engine="pyarrow")

print("Parquet file created successfully.")

