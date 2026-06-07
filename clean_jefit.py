import os
import glob
import json
import time
import pandas as pd
import google.generativeai as genai

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("API Key missing.")
    exit(1)

genai.configure(api_key=api_key)
# Using gemini-1.5-flash because it has a 1-million token memory to read the whole file at once
model = genai.GenerativeModel('gemini-1.5-flash')

input_files = []
for ext in ('*.csv', '*.CSV', '*.txt', '*.TXT'):
    input_files.extend(glob.glob(f"input/{ext}"))

if not input_files:
    print("No input file found.")
    exit(1)

with open(input_files[0], 'r', encoding='utf-8', errors='ignore') as f:
    full_text = f.read()

print("Phase 1: Scanning the entire file to crack the '#' cipher...")

cipher_prompt = """
You are a data decoder. This Jefit export is a relational database divided into sections by rows of '#' characters.
- One section defines Sessions/Programs (mapping a session ID to a Date).
- One section defines Exercises (mapping an exercise ID to an Exercise Name).

Scan the entire text to find these mapping sections. 
Return ONLY a JSON object matching this exact schema:
{
  "sessions": {"id": "YYYY-MM-DD"},
  "exercises": {"id": "Exercise Name"}
}
"""

try:
    cipher_response = model.generate_content(
        f"{cipher_prompt}\n\nFile Content:\n{full_text}",
        generation_config=genai.GenerationConfig(response_mime_type="application/json")
    )
    cipher = json.loads(cipher_response.text)
    print(f"Cipher cracked! Found {len(cipher.get('sessions', {}))} dates and {len(cipher.get('exercises', {}))} exercises.")
except Exception as e:
    print(f"Failed to crack cipher: {e}")
    cipher = {"sessions": {}, "exercises": {}}

print("Phase 2: Translating workout logs using the cipher...")

all_sets = []
lines = full_text.split('\n')
chunk_size = 200 

schema = {
    "type": "OBJECT",
    "properties": {
        "sets": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "Date": {"type": "STRING"},
                    "Exercise": {"type": "STRING"},
                    "Weight": {"type": "STRING"},
                    "Reps": {"type": "STRING"}
                },
                "required": ["Date", "Exercise", "Weight", "Reps"]
            }
        }
    }
}

# Process the file chunk-by-chunk to stay under output limits
for i in range(0, len(lines), chunk_size):
    chunk = "\n".join(lines[i:i + chunk_size])
    if not chunk.strip(): continue

    prompt = f"""
    Extract workout logs from this Jefit chunk.
    
    Here is the decoded cipher ring to translate IDs:
    Sessions (Dates): {json.dumps(cipher.get('sessions', {}))}
    Exercises (Names): {json.dumps(cipher.get('exercises', {}))}
    
    Rules:
    1. Only extract actual workout sets. Ignore '#' dividers or mapping definitions.
    2. If the row uses an ID, use the cipher ring to find the real Date and Exercise.
    3. Split compacted sets (e.g., '135x10, 135x8') into individual set objects.
    4. If no sets are in this chunk, return an empty array.
    
    Data Chunk:
    {chunk}
    """

    success = False
    for attempt in range(6):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=schema
                )
            )
            data = json.loads(response.text)
            if data.get("sets"):
                all_sets.extend(data["sets"])
            success = True
            break
        except Exception as e:
            # If we hit Google's free-tier rate limits, back off and try again
            time.sleep(4 * (attempt + 1)) 
    
    if success:
        # Pause briefly to respect the 15 requests-per-minute API limit
        time.sleep(4)

if not all_sets:
    print("No data extracted.")
    exit(1)

# Format into the final clean layout
df = pd.DataFrame(all_sets)
df['Date'] = df['Date'].str.split('T').str[0]
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

print(f"Success! {len(df)} sets processed.")
