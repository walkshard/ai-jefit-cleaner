import os
import glob
import json
import pandas as pd
import google.generativeai as genai

print("Starting AI Jefit Data Cleaner...")

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY environment variable not set.")
    exit(1)

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# Catch lowercase and uppercase extensions
input_files = []
for ext in ('*.csv', '*.CSV', '*.txt', '*.TXT'):
    input_files.extend(glob.glob(f"input/{ext}"))

if not input_files:
    print("Error: No files found in the 'input' folder. Did you upload it to the main directory by mistake?")
    exit(1)

all_records = []

def process_chunk_with_ai(text_chunk):
    prompt = """
    Extract workout data from this Jefit export.
    Output MUST be a valid JSON array of objects. 
    Keys must be exactly: "Date" (YYYY-MM-DD), "Exercise", "Weight", "Reps".
    Create a separate object for every single set.
    """
    try:
        response = model.generate_content(
            f"{prompt}\n\nData:\n{text_chunk}",
            generation_config=genai.GenerationConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"AI chunk failed: {e}")
        return []

for file_path in input_files:
    print(f"Processing {file_path}...")
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    for i in range(0, len(lines), 150):
        chunk = "".join(lines[i:i + 150])
        if chunk.strip():
            all_records.extend(process_chunk_with_ai(chunk))

if not all_records:
    print("Error: AI could not extract any valid records.")
    exit(1)

df = pd.DataFrame(all_records)
df.columns = df.columns.str.title()

for col in ['Date', 'Exercise', 'Weight', 'Reps']:
    if col not in df.columns:
        df[col] = '0'

df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
df = df.dropna(subset=['Date', 'Exercise'])
df = df.sort_values(by=['Date', 'Exercise'])
df['Set'] = df.groupby(['Date', 'Exercise']).cumcount() + 1

df = df[['Date', 'Exercise', 'Set', 'Weight', 'Reps']]

os.makedirs('output', exist_ok=True)

# Save the massive archive file
df.to_csv('output/Cleaned_Jefit_Data.csv', index=False)

# Save a lightweight file for the dashboard (Last 500 sets, Newest to Oldest)
df_recent = df.copy()
df_recent = df_recent.sort_values(by=['Date', 'Exercise'], ascending=[False, True])
df_recent = df_recent.head(500)
df_recent.to_csv('output/Dashboard_Data.csv', index=False)

print("Success! Both archive and dashboard files generated.")
