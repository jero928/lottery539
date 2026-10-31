// Regularized logistic regression. All training is local; no API keys.
(()=>{
function theory(t) { let miss = 1; const k = t === 0 ? 3 : 4; for (let i = 0; i < 5; i++)
    miss *= (39 - k - i) / (39 - i); return 1 - miss; }
function pairTheory(tails) { const k = [...new Set(tails)].reduce((n, t) => n + (t === 0 ? 3 : 4), 0); let miss = 1; for (let i = 0; i < 5; i++)
    miss *= (39 - k - i) / (39 - i); return 1 - miss; }
function wilson(hits, total) { if (!total)
    return { low: 0, high: 1 }; const z = 1.959963984540054, p = hits / total, d = 1 + z * z / total, center = (p + z * z / (2 * total)) / d, half = z * Math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d; return { low: Math.max(0, center - half), high: Math.min(1, center + half) }; }
const topTwo = (predictions) => [...predictions].sort((a, b) => b.probability - a.probability || a.tail - b.tail).slice(0, 2).map(p => p.tail);
function analyze(draws, days, today) {
    const end = new Date(today + 'T00:00:00+08:00').getTime(), start = end - (days - 1) * 86400000;
    const rows = draws.filter(d => { const t = new Date(d.date + 'T00:00:00+08:00').getTime(); return t >= start && t <= end; }).sort((a, b) => b.date.localeCompare(a.date));
    const stats = Array.from({ length: 10 }, (_, tail) => { const hits = rows.filter(d => d.numbers.some(n => n % 10 === tail)).length; const balls = rows.reduce((v, d) => v + d.numbers.filter(n => n % 10 === tail).length, 0); const gap = rows.findIndex(d => d.numbers.some(n => n % 10 === tail)); return { tail, hits, balls, gap: gap < 0 ? rows.length : gap, frequency: rows.length ? hits / rows.length : 0, theory: theory(tail) }; });
    return { rows, stats };
}
function taipeiDate(now) { return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit' }).format(now); }
function schedule(now, latest) {
    const today = taipeiDate(now);
    let target = new Date(today + 'T20:30:00+08:00');
    const close = new Date(today + 'T21:30:00+08:00');
    const weekday = new Date(today + 'T12:00:00+08:00').getUTCDay();
    if (weekday !== 0 && now >= target && now < close && latest !== today)
        return { waiting: true, target };
    if (now >= target)
        target = new Date(target.getTime() + 86400000);
    while (new Date(target.getTime() + 8 * 3600000).getUTCDay() === 0)
        target = new Date(target.getTime() + 86400000);
    return { waiting: false, target };
}
// Regularized logistic regression, sharing two coefficients across tails.
// Each feature uses only draws strictly before its target draw.
function modelAnalysis(draws) {
    const seq = [...draws].sort((a, b) => a.date.localeCompare(b.date));
    const feature = (index, t) => { const p = theory(t), past = seq.slice(Math.max(0, index - 20), index); const f = past.filter(d => d.numbers.some(n => n % 10 === t)).length / past.length; let gap = 0; for (let j = index - 1; j >= 0 && !seq[j].numbers.some(n => n % 10 === t); j--)
        gap++; return [f - p, (Math.min(gap, 10) - (1 - p) / p) / 10]; };
    const sigmoid = (v) => 1 / (1 + Math.exp(-v));
    const samples = seq.flatMap((d, i) => i < 20 ? [] : Array.from({ length: 10 }, (_, t) => ({ i, t, x: feature(i, t), y: d.numbers.some(n => n % 10 === t) ? 1 : 0 })));
    const fit = (limit) => { const train = samples.filter(s => s.i < limit); let w = [0, 0]; for (let epoch = 0; epoch < 250; epoch++) {
        const g = w.map(v => .06 * v);
        for (const s of train) {
            const p = theory(s.t), pred = sigmoid(Math.log(p / (1 - p)) + w[0] * s.x[0] + w[1] * s.x[1]);
            g[0] += (pred - s.y) * s.x[0] / Math.max(train.length, 1);
            g[1] += (pred - s.y) * s.x[1] / Math.max(train.length, 1);
        }
        w = w.map((v, j) => v - .8 * g[j]);
    } return w; };
    const predict = (w, i, t) => { const p = theory(t), x = feature(i, t); return sigmoid(Math.log(p / (1 - p)) + w[0] * x[0] + w[1] * x[1]); };
    if (seq.length < 45)
        return null;
    let error = 0, baseError = 0, count = 0;
    const start = Math.max(40, seq.length - 20);
    const records = [];
    for (let i = start; i < seq.length; i++) {
        const w = fit(i);
        const predictions = Array.from({ length: 10 }, (_, tail) => ({ tail, probability: predict(w, i, tail) }));
        const tails = topTwo(predictions);
        records.push({ period: seq[i].period, date: seq[i].date, tails, numbers: seq[i].numbers, hit: seq[i].numbers.some(n => tails.includes(n % 10)), baseline: pairTheory(tails) });
        for (let t = 0; t < 10; t++) {
            const y = seq[i].numbers.some(n => n % 10 === t) ? 1 : 0;
            error += (predictions[t].probability - y) ** 2;
            baseError += (theory(t) - y) ** 2;
            count++;
        }
    }
    const w = fit(seq.length);
    const predictions = Array.from({ length: 10 }, (_, tail) => ({ tail, probability: predict(w, seq.length, tail) }));
    const hits = records.filter(r => r.hit).length;
    const pairBaseline = records.reduce((s, r) => s + r.baseline, 0) / records.length;
    return { predictions, brier: error / count, baseline: baseError / count, testDraws: seq.length - start, trainDraws: seq.length - 20, pair: { tails: topTwo(predictions), records, hits, rate: hits / records.length, baseline: pairBaseline, interval: wilson(hits, records.length) } };
}

window.TailAI={modelAnalysis,analyze,theory,pairTheory};
})();
