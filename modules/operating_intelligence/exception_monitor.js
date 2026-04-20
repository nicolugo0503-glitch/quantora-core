export function detectOperatingExceptions(store){
  const exceptions = [];
  (store.exceptions || []).forEach(x => exceptions.push(x));
  return exceptions;
}