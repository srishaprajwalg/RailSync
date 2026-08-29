export const formatTime = (minutesSinceMidnight) => {
  const hrs = Math.floor(minutesSinceMidnight / 60);
  const mins = minutesSinceMidnight % 60;
  return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
};

export const formatDuration = (minutes) => {
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hrs > 0) return `${hrs}h ${mins > 0 ? mins + 'm' : ''}`;
  return `${mins}m`;
};
