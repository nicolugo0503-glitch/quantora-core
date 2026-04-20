export function generateOperatingAlerts(store){
  return (store.alerts || []).slice();
}