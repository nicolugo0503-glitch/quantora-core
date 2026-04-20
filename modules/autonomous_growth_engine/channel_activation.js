export function rankChannels(channels = []) {
  return [...channels].sort((a, b) => Number(b.sequence_score || 0) - Number(a.sequence_score || 0));
}
