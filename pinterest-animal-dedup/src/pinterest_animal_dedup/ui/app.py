from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from pinterest_animal_dedup.db.repository import list_candidates

app = FastAPI(title="Pinterest Animal Dedup UI")


@app.get("/api/candidates")
def api_candidates():
    records = list_candidates(200)
    return [
        {
            "pin_id": r.pin.pin_id,
            "url": r.pin.url,
            "title": r.pin.title,
            "media_type": r.pin.media_type.value,
            "aggregate_dedup": r.aggregate_dedup_status.value,
            "score": r.score.total if r.score else None,
            "adaptation_mode": r.adaptation_mode,
            "adaptation_notes": r.adaptation_notes,
            "animals": r.analysis.animal_labels if r.analysis else [],
        }
        for r in records
    ]


@app.get("/", response_class=HTMLResponse)
def index():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Pinterest Animal Dedup</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; background: #0f1419; color: #e7ecf3; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #2a3544; padding: 0.5rem 0.75rem; text-align: left; }
    th { background: #1a2332; }
    tr:nth-child(even) { background: #121a24; }
    a { color: #7cb6ff; }
    .score { font-weight: 600; }
  </style>
</head>
<body>
  <h1>动物短视频选题 · 国内查重</h1>
  <p>数据来自本地数据库（discover → analyze → dedup → score）。</p>
  <table id="tbl">
    <thead>
      <tr>
        <th>评分</th><th>链接</th><th>标题</th><th>查重</th><th>动物</th><th>改编</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>
  <script>
    fetch('/api/candidates').then(r => r.json()).then(rows => {
      const tb = document.querySelector('#tbl tbody');
      rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="score">${row.score ?? '-'}</td>
          <td><a href="${row.url}" target="_blank" rel="noopener">${row.pin_id}</a></td>
          <td>${(row.title || '').slice(0, 80)}</td>
          <td>${row.aggregate_dedup}</td>
          <td>${(row.animals || []).join(', ')}</td>
          <td>${row.adaptation_mode}: ${(row.adaptation_notes || '').slice(0, 100)}</td>`;
        tb.appendChild(tr);
      });
    });
  </script>
</body>
</html>"""
