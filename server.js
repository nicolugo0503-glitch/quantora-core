const express = require('express');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 3000;

// Base prices for SSE simulation
const BASE = {
  SPX: 5842.91, NDX: 20471.16, RTY: 2043.28, VIX: 13.24,
  BTC: 62841, GOLD: 2318.40, WTI: 78.84, DXY: 104.62,
  'US10Y': 4.318, 'US2Y': 4.891, HYG: 77.42, TLT: 88.14,
  'QTR NAV': 412.4, 'EUR/USD': 1.0731
};
const prices = { ...BASE };

// SSE endpoint — live price feed
app.get('/api/prices', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.flushHeaders();

  const send = () => {
    Object.keys(prices).forEach(k => {
      const vol = k === 'VIX' ? 0.008 : k === 'BTC' ? 0.004 : 0.0008;
      prices[k] = Math.max(0.01, prices[k] * (1 + (Math.random() - 0.5) * vol));
    });
    res.write(`data: ${JSON.stringify(prices)}\n\n`);
  };

  send();
  const iv = setInterval(send, 2000);
  req.on('close', () => clearInterval(iv));
});

app.use(express.static(path.join(__dirname, 'public')));
app.get('*', (req, res) => res.sendFile(path.join(__dirname, 'public', 'index.html')));
app.listen(PORT, () => console.log(`Quantora running on port ${PORT}`));
