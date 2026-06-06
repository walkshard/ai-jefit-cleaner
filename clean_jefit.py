import os
import glob
import json
import pandas as pd
import google.generativeai as genai

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("API Key missing.")
    exit(1)

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

input_files = []
for ext in ('*.csv', '*.CSV', '*.txt', '*.TXT'):
    input_files.extend(glob.glob(f"input/{ext}"))

if not input_files:
    print("No input file found.")
    exit(1)

all_records = []
last_date = "Unknown Date"
last_exercise = "Unknown Exercise"

for file_path in input_files:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    for i in range(0, len(lines), 150):
        chunk = "".join(lines[i:i + 150])
        if not chunk.strip():
            continue
        
        prompt = f"""
        Parse this vertical Jefit export. 
        Context from previous chunk: last_date="{last_date}", last_exercise="{last_exercise}".
        Extract all workout sets. Use context if date/exercise is missing before a set.
        
        Output MUST be JSON matching this schema:
        {{
          "last_date": "YYYY-MM-DD",
          "last_exercise": "Name",
          "sets": [
            {{"Date": "YYYY-MM-DD", "Exercise": "Name", "Weight": "135", "Reps": "10"}}
          ]
        }}
        
        Data:
        {chunk}
        """
        
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json")
            )
            data = json.loads(response.text)
            
            if "sets" in data and data["sets"]:
                all_records.extend(data["sets"])
            if "last_date" in data:
                last_date = data["last_date"]
            if "last_exercise" in data:
                last_exercise = data["last_exercise"]
                
        except Exception as e:
            print(f"Chunk error: {e}")

if not all_records:
    print("Failed to extract data.")
    exit(1)

df = pd.DataFrame(all_records)
df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
df = df.dropna(subset=['Date', 'Exercise', 'Weight', 'Reps'])
df = df.sort_values(by=['Date', 'Exercise'])
df['Set'] = df.groupby(['Date', 'Exercise']).cumcount() + 1
df = df[['Date', 'Exercise', 'Set', 'Weight', 'Reps']]

os.makedirs('output', exist_ok=True)
df.to_csv('output/Cleaned_Jefit_Data.csv', index=False)

df_recent = df.copy()
df_recent = df_recent.sort_values(by=['Date', 'Exercise'], ascending=[False, True])
df_recent = df_recent.head(500)
df_recent.to_csv('output/Dashboard_Data.csv', index=False)
