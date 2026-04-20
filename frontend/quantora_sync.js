(function(){
  const KEY = 'q_balance';
  const DEFAULT_BALANCE = 100000;
  let cache = null;

  function readLocal(){
    const raw = localStorage.getItem(KEY);
    const num = Number(raw);
    return Number.isFinite(num) && num >= 0 ? num : DEFAULT_BALANCE;
  }

  function writeLocal(v){
    const n = Math.max(0, Number(v) || 0);
    localStorage.setItem(KEY, String(n));
    cache = n;
    try{
      window.dispatchEvent(new CustomEvent('quantora:balance-updated', { detail: { balance: n } }));
    }catch(e){}
    return n;
  }

  async function fetchCapital(){
    try{
      const r = await fetch('/api/capital', { cache: 'no-store' });
      if(!r.ok) throw new Error('capital fetch failed');
      const data = await r.json();
      if(Number.isFinite(Number(data.balance))){
        writeLocal(Number(data.balance));
        return data;
      }
    }catch(e){}
    return { balance: readLocal(), available: readLocal(), allocated: 0, source: 'local' };
  }

  function getBalance(){
    return cache ?? readLocal();
  }

  async function setBalance(v){
    const n = Math.max(0, Number(v) || 0);
    writeLocal(n);
    return n;
  }

  async function deposit(amount){
    const r = await fetch('/api/capital/deposit', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ amount: Number(amount || 0) })
    });
    const data = await r.json();
    if(!r.ok) throw new Error(data.detail || 'deposit failed');
    writeLocal(Number(data.balance || 0));
    return data;
  }

  async function withdraw(amount){
    const r = await fetch('/api/capital/withdraw', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ amount: Number(amount || 0) })
    });
    const data = await r.json();
    if(!r.ok) throw new Error(data.detail || 'withdraw failed');
    writeLocal(Number(data.balance || 0));
    return data;
  }

  async function ledger(){
    const r = await fetch('/api/capital/ledger', { cache:'no-store' });
    if(!r.ok) throw new Error('ledger fetch failed');
    const data = await r.json();
    writeLocal(Number(data.balance || 0));
    return data;
  }

  function subscribe(cb){
    window.addEventListener('storage', function(e){
      if(e.key === KEY){ cb(readLocal()); }
    });
    window.addEventListener('quantora:balance-updated', function(e){
      cb((e.detail && e.detail.balance) || readLocal());
    });
  }

  window.QuantoraSync = {
    getBalance,
    setBalance,
    fetchCapital,
    deposit,
    withdraw,
    ledger,
    subscribe
  };
})();
