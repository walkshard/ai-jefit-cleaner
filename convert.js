const fs = require('fs');
const { execSync } = require('child_process');

console.log("Running official OpenWeight CLI...");

// 1. Run OpenWeight's official Jefit migrator on your input file
try {
    execSync('npx @openweight/cli migrate jefit input/ --output output.json', { stdio: 'inherit' });
} catch (e) {
    console.error("OpenWeight failed to parse the file. Ensure it is the raw Jefit export.");
    process.exit(1);
}

// 2. Read the clean OpenWeight JSON
const data = JSON.parse(fs.readFileSync('output.json', 'utf8'));
let csvContent = "Date,Exercise,Set,Weight,Reps\n";

// 3. Convert it to a clean CSV
data.workouts.forEach(workout => {
    const date = workout.date ? workout.date.split('T')[0] : 'Unknown Date';
    
    workout.exercises.forEach(exLog => {
        const exerciseName = `"${exLog.exercise.name.replace(/"/g, '""')}"`;
        
        exLog.sets.forEach((set, index) => {
            const weight = set.weight || 0;
            const reps = set.reps || 0;
            const setNum = index + 1;
            
            csvContent += `${date},${exerciseName},${setNum},${weight},${reps}\n`;
        });
    });
});

// 4. Save the final file
if (!fs.existsSync('output')) fs.mkdirSync('output');
fs.writeFileSync('output/Cleaned_Jefit_Data.csv', csvContent);
console.log("Success! Clean CSV generated.");
