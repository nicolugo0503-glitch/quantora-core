function initTicker() {
  const track=document.getElementById('ticker-track');
  const prices={};
  const BASE={SPX:5842.91,NDX:20471.16,RTY:2043.28,VIX:13.24,BTC:62841,GOLD:2318.40,WTI:78.84,DXY:104.62,'US10Y':4.318,'US2Y':4.891,HYG:77.42,TLT:88.14,'QTR NAV':412.4,'EUR/USD':1.0731};
  Object.assign(prices,BASE);
  function fmt(v,dp,sfx){return v.toFixed(dp)+sfx;}
  function buildItem(t,price){const base=price||0,prev=prices[t.key]||base,up=base>=prev,pct=prev?((base-prev)/prev*100):0;return `<div class="ti" data-key="${t.key}"><span class="ti-s">${t.s}</span><span class="ti-v">${fmt(base,t.dp,t.suffix)}</span><span class="ti-c ${up?'u':'d'}">${up?'▲':'▼'} ${Math.abs(pct).toFixed(2)}%</span></div>`;}
  function render(){const html=Q.TICKS.map(t=>buildItem(t,prices[t.key])).join('');track.innerHTML=html+html;}
  render();
  try{const src=new EventSource('/api/prices');src.onmessage=e=>{const data=JSON.parse(e.data);let ch=false;Q.TICKS.forEach(t=>{if(data[t.key]!==undefined&&Math.abs(data[t.key]-prices[t.key])>0.0001){ch=true;const el=track.querySelectorAll(`[data-key="${t.key}"]`);el.forEach(i=>i.classList.add('flash'));setTimeout(()=>el.forEach(i=>i.classList.remove('flash')),400);}});Object.assign(prices,data);if(ch)render();};src.onerror=()=>src.close();}catch(e){}
}
