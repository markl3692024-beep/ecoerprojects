import pandas as pd
import sys

file_path = r"C:\Users\Mark\.qclaw\media\inbound\Ecoer_Northeast_Regular_Customer_List_Price---f2a84aeb-94ad-43ef-9351-6e621c91b516.xlsx"

# 读取所有sheet
xl = pd.ExcelFile(file_path)
print("Sheets:", xl.sheet_names)

# 读取第一个sheet
df = pd.read_excel(file_path, sheet_name=0)
print("\n=== 数据预览 ===")
print(f"行数: {len(df)}")
print(f"列名: {list(df.columns)}")
print("\n前10行:")
print(df.head(10).to_string())
print("\n数据类型:")
print(df.dtypes)
