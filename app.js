// static/js/app.js
async function postJSON(url, payload) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Network error: ' + res.statusText);
  return res.json();
}

function createBarHTML(label, percent) {
  // color selection by label (simple)
  const colorMap = {
    happy: '#6c5ce7',
    sad: '#ff6b6b',
    angry: '#ff8a65',
    nervous: '#8b5cf6',
    neutral: '#94a3b8',
    grateful: '#10b981',
    surprised: '#06b6d4'
  };
  const color = colorMap[label] || '#6c5ce7';
  return `
    <div class="barWrap" data-emotion="${label}">
      <div class="barLabel">${label.charAt(0).toUpperCase()+label.slice(1)}</div>
      <div class="bar"><div class="barInner" style="width:${percent}%;background:${color}"></div></div>
      <div class="value">${percent}%</div>
    </div>
  `;
}

function renderAggregate(aggregate) {
  const container = document.getElementById('aggregateBars');
  container.innerHTML = '';
  // sort by value desc
  const sorted = Object.entries(aggregate).sort((a,b)=>b[1]-a[1]);
  sorted.forEach(([k,v]) => {
    const el = createBarHTML(k, v);
    container.insertAdjacentHTML('beforeend', el);
  });
}

function renderSentences(sentences) {
  const container = document.getElementById('sentencesList');
  container.innerHTML = '';
  sentences.forEach(s => {
    const top = s.top;
    const topPct = Math.max(...Object.values(s.scores)) * 100;
    // show main bar with top emotion intensity
    const html = `
      <div class="sentence">
        <div style="font-weight:600;margin-bottom:6px">${s.sentence}</div>
        <div class="barWrap">
          <div class="barLabel">Top: ${top}</div>
          <div class="bar"><div class="barInner" style="width:${(topPct).toFixed(1)}%;background:#6c5ce7"></div></div>
          <div class="value">${(topPct).toFixed(1)}</div>
        </div>
      </div>
    `;
    container.insertAdjacentHTML('beforeend', html);
  });
}

document.getElementById('detectBtn').addEventListener('click', async ()=>{
  const text = document.getElementById('inputText').value.trim();
  if (!text) {
    alert('Please enter some text.');
    return;
  }
  try {
    const res = await postJSON('/api/detect', {text});
    renderAggregate(res.aggregate);
    renderSentences(res.sentences);
    document.getElementById('autoReply').innerText = res.auto_reply;
    // save last result for export/share
    window.__lastEmotionResult = res;
    window.__lastInputText = text;
  } catch (e) {
    console.error(e);
    alert('Error detecting emotions: ' + e.message);
  }
});

// export summary
document.getElementById('exportBtn').addEventListener('click', async ()=>{
  const res = window.__lastEmotionResult;
  const text = window.__lastInputText || document.getElementById('inputText').value;
  if (!res) {
    alert('Please run detection first.');
    return;
  }
  try {
    const resp = await fetch('/api/export', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({text, result: res})
    });
    if (!resp.ok) throw new Error('Export failed');
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'emotion_summary.txt';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert('Export error: ' + e.message);
  }
});

// share result: copy JSON to clipboard
document.getElementById('shareBtn').addEventListener('click', async ()=>{
  const res = window.__lastEmotionResult;
  if (!res) {
    alert('Please run detection first.');
    return;
  }
  try {
    await navigator.clipboard.writeText(JSON.stringify(res, null, 2));
    alert('Result copied to clipboard. Paste anywhere to share.');
  } catch (e) {
    alert('Copy failed: ' + e.message);
  }
});

// run initial detect on load for sample text
window.addEventListener('load', ()=> {
  document.getElementById('detectBtn').click();
});
