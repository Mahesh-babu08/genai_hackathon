function displayQualityScores(scores) {
    if (!scores) return;

    const container = document.getElementById('quality-score-container');
    container.classList.remove('hidden');

    // Animate Overall Score Gauge
    const circle = document.getElementById('score-circle');
    const radius = circle.r.baseVal.value;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (scores.overall / 100) * circumference;

    // Set color based on score
    const color = getGradeColor(scores.grade);
    circle.style.stroke = color;
    circle.style.strokeDashoffset = offset;

    document.getElementById('grade-letter').textContent = scores.grade;
    document.getElementById('grade-letter').style.color = color;
    document.getElementById('score-number').textContent = `${scores.overall}/100`;

    // Animate Category Bars
    animateBar('bar-security', 'score-security-val', scores.categories.security);
    animateBar('bar-performance', 'score-performance-val', scores.categories.performance);
    animateBar('bar-maintainability', 'score-maintainability-val', scores.categories.maintainability);
    animateBar('bar-readability', 'score-readability-val', scores.categories.readability);
}

function animateBar(barId, valId, score) {
    const bar = document.getElementById(barId);
    const val = document.getElementById(valId);

    // Set width
    setTimeout(() => {
        bar.style.width = `${score}%`;

        // Color coding
        if (score >= 90) bar.className = `h-1.5 rounded-full transition-all duration-1000 bg-emerald-500`;
        else if (score >= 70) bar.className = `h-1.5 rounded-full transition-all duration-1000 bg-blue-500`;
        else if (score >= 50) bar.className = `h-1.5 rounded-full transition-all duration-1000 bg-yellow-500`;
        else bar.className = `h-1.5 rounded-full transition-all duration-1000 bg-red-500`;
    }, 100);

    // Animate number
    animateValue(val, 0, score, 1000);
}

function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

function getGradeColor(grade) {
    switch (grade) {
        case 'A': return '#10b981'; // emerald-500
        case 'B': return '#3b82f6'; // blue-500
        case 'C': return '#eab308'; // yellow-500
        case 'D': return '#f97316'; // orange-500
        case 'F': return '#ef4444'; // red-500
        default: return '#cbd5e1'; // slate-300
    }
}
