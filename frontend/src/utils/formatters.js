export const formatTime = (totalMinutes, showDay = true) => {
  const day = Math.floor(totalMinutes / 1440) + 1;
  const remainder = totalMinutes % 1440;
  const hrs = Math.floor(remainder / 60);
  const mins = remainder % 60;
  
  const timeStr = `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
  return showDay ? `Day ${day} — ${timeStr}` : timeStr;
};

export const formatDuration = (minutes) => {
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hrs > 0) return `${hrs}h ${mins > 0 ? mins + 'm' : ''}`;
  return `${mins}m`;
};
