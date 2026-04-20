export function growthPosture({ growthCapacity = 0, critical = false, releaseFloor = 76 } = {}) {
  if (critical) return 'governed-autonomy';
  if (growthCapacity >= releaseFloor) return 'autonomous-expansion';
  if (growthCapacity >= 60) return 'sequenced-growth';
  return 'growth-watch';
}
