const API_BASE_URL = 'http://127.0.0.1:8000/api';

export const optimizeBlocks = async (horizon_days = 7) => {
  const response = await fetch(`${API_BASE_URL}/optimize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ horizon_days }),
  });
  if (!response.ok) {
    throw new Error('Failed to run optimization');
  }
  return response.json();
};

export const fetchCorridor = async () => {
  const response = await fetch(`${API_BASE_URL}/corridor`);
  if (!response.ok) throw new Error('Failed to fetch corridor');
  return response.json();
};

export const fetchTimetables = async () => {
  const response = await fetch(`${API_BASE_URL}/timetables`);
  if (!response.ok) throw new Error('Failed to fetch timetables');
  return response.json();
};

export const fetchGoodsForecasts = async () => {
  const response = await fetch(`${API_BASE_URL}/goods_forecasts`);
  if (!response.ok) throw new Error('Failed to fetch goods forecasts');
  return response.json();
};

export const fetchTasks = async () => {
  const response = await fetch(`${API_BASE_URL}/tasks`);
  if (!response.ok) throw new Error('Failed to fetch tasks');
  return response.json();
};

export const addTask = async (taskData) => {
  const response = await fetch(`${API_BASE_URL}/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(taskData),
  });
  if (!response.ok) throw new Error('Failed to add task');
  return response.json();
};

export const previewPriority = async (taskData) => {
  const response = await fetch(`${API_BASE_URL}/tasks/preview-priority`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(taskData),
  });
  if (!response.ok) throw new Error('Failed to preview priority');
  return response.json();
};

export const fetchTaskDefaults = async () => {
  const response = await fetch(`${API_BASE_URL}/tasks/defaults`);
  if (!response.ok) throw new Error('Failed to fetch task defaults');
  return response.json();
};

export const updateTaskStatus = async (taskId, status) => {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/status`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ lifecycle_status: status }),
  });
  if (!response.ok) throw new Error('Failed to update task status');
  return response.json();
};
