import os
import glob
import pandas as pd
import re
import csv

print("Starting Vertical Jefit Parser...")

input_files = []
for ext in ('*.csv', '*.CSV', '*.txt', '*.TXT'):
    input_files.extend(glob.glob(f"input/{ext}"))

if not input_files:
    print("No input file found.")
    exit(1)

all_records = []
date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}')

for file_path in input_files:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        
        current_date = "Unknown Date"
        current_exercise = "Unknown Exercise"
        
        for row in reader:
            cleaned = [str(x).strip() for x in row if str(x).strip()]
            if not cleaned: continue
            
            # 1. Date
            if len(cleaned) == 1 and date_pattern.search(cleaned[0]):
                current_date = date_pattern.search(cleaned[0]).group()
                continue
                
            # 2. Skip Headers
            text_lower = " ".join(cleaned).lower()
            if "weight" in text_lower and "reps" in text_lower:
                continue
                
            # 3. Exercise Name (Text string, no numbers)
            if len(cleaned) == 1 and not date_pattern.search(cleaned[0]):
                current_exercise = cleaned[0]
                continue
                
            # 4. Sets (Starts with a number)
            if len(cleaned) >= 3 and cleaned[0].isdigit():
                all_records.append({
                    "Date": current_date,
                    "Exercise": current_exercise,
                    "Weight": cleaned[1],
                    "Reps": cleaned[2]
                })
            elif len(cleaned) == 2 and cleaned[0].replace('.', '').isdigit():
                 all_records.append({
                    "Date": current_date,
                    "Exercise": current_exercise,
                    "Weight": cleaned[0],
                    "Reps": cleaned[1]
                })

if not all_records:
    print("Failed to parse sets.")
    exit(1)

df = pd.DataFrame(all_records)
df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
df = df.dropna(subset=['Date', 'Exercise'])
df = df.sort_values(by=['Date', 'Exercise'])
df['Set'] = df.groupby(['Date', 'Exercise']).cumcount() + 1
df = df[['Date', 'Exercise', 'Set', 'Weight', 'Reps']]

os.makedirs('output', exist_ok=True)
df.to_csv('output/Cleaned_Jefit_Data.csv', index=False)

df_recent = df.copy()
df_recent = df_recent.sort_values(by=['Date', 'Exercise'], ascending=[False, True])
df_recent = df_recent.head(500)
df_recent.to_csv('output/Dashboard_Data.csv', index=False)

print(f"Success! {len(df)} sets processed.")
