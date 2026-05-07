function buildHeatmap() {
  const wrap = document.getElementById('hm-wrap');
  if (!wrap) return;
  let html = `<table class="hm-table"><thead><tr><th class="yr">Yr</th>`;
  Q.MONTHS.forEach(m => html += `<th>${m}</th>`);
  html += `<th>YTD</th></tr></thead><tbody>`;
  Object.entries(Q.HM).forEach(([yr, vals]) => {
    let tot = 1; vals.forEach(v => { if (v !== null) tot *= (1 + v / 100); });
    const tp = (tot - 1) * 100;
    html += `<tr><td class="yr-l">${yr}</td>`;
    vals.forEach((v, mi) => {
      if (v === null) { html += `<td class="null-cell">—</td>`; return; }
      const it = Math.min(Math.abs(v)/5,1);
      const pos = v >= 0;
      const rr = pos ? Math.round(24+it*18) : Math.round(184-it*38);
      const gg = pos ? Math.round(150+it*65) : Math.round(52-it*18);
      const bb = pos ? Math.round(90-it*28) : Math.round(40-it*10);
      const tc = it>0.36 ? 'rgba(240,248,255,0.93)' : 'rgba(120,152,190,0.88)';
      const lbl = `${v>0?'+':''}${v.toFixed(1)}%`;
      html += `<td style="background:rgba(${rr},${gg},${bb},${0.13+it*0.52});color:${tc}" data-tip="${Q.MONTHS[mi]} ${yr}: ${lbl}" class="hm-cell">${lbl}</td>`;
    });
    const tc2 = tp >= 0 ? '#1FBC6E' : '#E04535';
    html += `<td class="tot" style="color:${tc2}">${tp>0?'+':''}${tp.toFixed(1)}%</td></tr>`;
  });
  html += `</tbody></table>`;
  wrap.innerHTML = html;
  wrap.querySelectorAll('.hm-cell').forEach(cell => {
    cell.addEventListener('mouseenter', e => { const tip=document.getElementById('hm-tooltip'); if(tip){tip.textContent=cell.dataset.tip;tip.style.opacity='1';} });
    cell.addEventListener('mouseleave', () => { const tip=document.getElementById('hm-tooltip'); if(tip)tip.style.opacity='0'; });
  });
}
