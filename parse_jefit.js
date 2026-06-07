const fs = require('fs');
const path = require('path');
const Papa = require('papaparse');

console.log("Starting Jefit Cloud Parser...");

const inputDir = 'input';
const outputDir = 'output';

if (!fs.existsSync(inputDir)) {
    console.log("No input directory found.");
    process.exit(1);
}

const files = fs.readdirSync(inputDir).filter(f => f.toLowerCase().endsWith('.csv') || f.toLowerCase().endsWith('.txt'));

if (files.length === 0) {
    console.log("No file found in input folder.");
    process.exit(1);
}

let allSets = [];

files.forEach(file => {
    const text = fs.readFileSync(path.join(inputDir, file), 'utf-8');
    const lines = text.split(/\r?\n/);
    
    let sections = [];
    let currentSection = [];
    
    // Split the file into separate tables based on blank lines or '#' dividers
    for (let line of lines) {
        if (line.trim() === '' || line.startsWith('#')) {
            if (currentSection.length > 0) {
                sections.push(currentSection.join('\n'));
                currentSection = [];
            }
        } else {
            currentSection.push(line);
        }
    }
    if (currentSection.length > 0) sections.push(currentSection.join('\n'));

    let sessionsMap = {}; 
    let exercisesMap = {}; 

    sections.forEach(section => {
        const parsed = Papa.parse(section, { header: true, skipEmptyLines: true });
        if (!parsed.data.length) return;

        const headers = Object.keys(parsed.data[0]).map(h => h.toLowerCase().trim());
        
        const isLogTable = headers.includes('logs') || (headers.includes('weight') && headers.includes('rep')) || headers.includes('belongsession');
        const isSessionTable = !isLogTable && (headers.includes('date') || headers.includes('createdate'));
        const isExerciseTable = !isLogTable && !isSessionTable && (headers.includes('name') || headers.includes('ename'));

        parsed.data.forEach(row => {
            const getVal = (possibleKeys) => {
                const matchedKey = Object.keys(row).find(k => possibleKeys.includes(k.toLowerCase().trim()));
                return matchedKey ? row[matchedKey] : null;
            };

            const id = getVal(['_id', 'sessionid', 'exerciseid', 'id']);

            if (isSessionTable) {
                const date = getVal(['date', 'createdate', 'belongdate']);
                if (id && date) sessionsMap[id] = date.split(' ')[0].split('T')[0];
            } 
            else if (isExerciseTable) {
                const name = getVal(['name', 'ename', 'exercisename']);
                if (id && name) exercisesMap[id] = name;
            } 
            else if (isLogTable) {
                const date = getVal(['date', 'belongdate']);
                const belongSession = getVal(['belongsession', 'sessionid']);
                const exerciseId = getVal(['exerciseid']);
                const name = getVal(['name', 'ename']);
                const logs = getVal(['logs', 'log']);
                const weight = getVal(['weight']);
                const reps = getVal(['rep', 'reps']);

                let finalDate = 'Unknown Date';
                if (belongSession && sessionsMap[belongSession]) finalDate = sessionsMap[belongSession];
                else if (date) finalDate = date.split(' ')[0].split('T')[0];

                let finalEx = 'Unknown Exercise';
                if (exerciseId && exercisesMap[exerciseId]) finalEx = exercisesMap[exerciseId];
                else if (name) finalEx = name;

                if (logs) {
                    logs.split(',').forEach(s => {
                        const parts = s.toLowerCase().split('x');
                        if (parts.length >= 2) {
                            allSets.push({ Date: finalDate, Exercise: finalEx, Weight: parts[0].trim(), Reps: parts[1].trim() });
                        }
                    });
                } else if (weight && reps) {
                    allSets.push({ Date: finalDate, Exercise: finalEx, Weight: weight, Reps: reps });
                }
            }
        });
    });
});

if (allSets.length === 0) {
    console.log("No data could be extracted.");
    process.exit(1);
}

// Clean and sort chronologically
allSets.sort((a, b) => {
    if (a.Date !== b.Date) return new Date(b.Date) - new Date(a.Date);
    return a.Exercise.localeCompare(b.Exercise);
});

let currentGroup = '';
let setNum = 1;
allSets.forEach(r => {
    const group = r.Date + r.Exercise;
    if (group !== currentGroup) {
        currentGroup = group;
        setNum = 1;
    }
    r.Set = setNum++;
});

if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir);

let finalCsv = "Date,Exercise,Set,Weight,Reps\n";
allSets.forEach(r => {
    const safeEx = `"${r.Exercise.replace(/"/g, '""')}"`;
    finalCsv += `${r.Date},${safeEx},${r.Set},${r.Weight},${r.Reps}\n`;
});

fs.writeFileSync(path.join(outputDir, 'Cleaned_Jefit_Data.csv'), finalCsv);
console.log(`Success! Parsed ${allSets.length} sets.`);
