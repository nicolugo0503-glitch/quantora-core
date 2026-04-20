export function rankLaunchQueue(rows = [], floor = 70) {
  return rows
    .filter((row) => Number(row.product_score || 0) >= floor || row.action === 'SCALE')
    .sort((a, b) => Number(b.product_score || 0) - Number(a.product_score || 0));
}
