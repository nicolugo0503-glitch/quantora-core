export function detectCrossSystemDependencies(store){
  return (store.dependencies || []).slice();
}