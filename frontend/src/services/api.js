const API_BASE_URL = 'http://127.0.0.1:8000/api';

export const optimizeBlocks = async (horizon_days = 7, corridor_id = 'SBC-JTJ') => {
  const response = await fetch(`${API_BASE_URL}/optimize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ horizon_days, corridor_id }),
  });
  if (!response.ok) {
    throw new Error('Failed to run optimization');
  }
  return response.json();
};

export const fetchCorridor = async (corridor_id = 'SBC-JTJ') => {
  const response = await fetch(`${API_BASE_URL}/corridor?corridor_id=${encodeURIComponent(corridor_id)}`);
  if (!response.ok) throw new Error('Failed to fetch corridor');
  return response.json();
};

export const fetchCorridorsList = async () => {
  const response = await fetch(`${API_BASE_URL}/corridors`);
  if (!response.ok) throw new Error('Failed to fetch corridors list');
  return response.json();
};

export const fetchSections = async (corridor_id = 'SBC-JTJ') => {
  const response = await fetch(`${API_BASE_URL}/sections?corridor_id=${encodeURIComponent(corridor_id)}`);
  if (!response.ok) throw new Error('Failed to fetch sections');
  return response.json();
};

export const fetchAssets = async (department = 'ALL', corridor_id = 'SBC-JTJ') => {
  const params = new URLSearchParams();
  if (corridor_id) params.append('corridor_id', corridor_id);
  if (department && department !== 'ALL') params.append('department', department);
  const queryStr = params.toString() ? `?${params.toString()}` : '';
  const response = await fetch(`${API_BASE_URL}/assets${queryStr}`);
  if (!response.ok) throw new Error('Failed to fetch assets');
  return response.json();
};

export const fetchTimetables = async (corridor_id = 'SBC-JTJ') => {
  const url = corridor_id ? `${API_BASE_URL}/timetables?corridor_id=${encodeURIComponent(corridor_id)}` : `${API_BASE_URL}/timetables`;
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to fetch timetables');
  return response.json();
};

export const fetchGoodsForecasts = async (corridor_id = 'SBC-JTJ') => {
  const url = corridor_id ? `${API_BASE_URL}/goods_forecasts?corridor_id=${encodeURIComponent(corridor_id)}` : `${API_BASE_URL}/goods_forecasts`;
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to fetch goods forecasts');
  return response.json();
};

export const fetchTasks = async (department = 'ALL', corridor_id = 'SBC-JTJ') => {
  const params = new URLSearchParams();
  if (corridor_id) params.append('corridor_id', corridor_id);
  if (department && department !== 'ALL') params.append('department', department);
  const queryStr = params.toString() ? `?${params.toString()}` : '';
  const response = await fetch(`${API_BASE_URL}/tasks${queryStr}`);
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

export const fetchTaskPredictions = async (taskId) => {
  const response = await fetch(`${API_BASE_URL}/predictions/${taskId}`);
  if (!response.ok) throw new Error('Failed to fetch ML predictions');
  return response.json();
};

export const fetchPriorityDecision = async (taskId) => {
  const response = await fetch(`${API_BASE_URL}/priority/${taskId}`);
  if (!response.ok) throw new Error('Failed to fetch priority decision');
  return response.json();
};

export const fetchTaskHistory = async (taskId) => {
  const response = await fetch(`${API_BASE_URL}/maintenance/${taskId}/history`);
  if (!response.ok) throw new Error('Failed to fetch task history');
  return response.json();
};

export const recordOutcome = async (outcomeData) => {
  const response = await fetch(`${API_BASE_URL}/outcomes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(outcomeData),
  });
  if (!response.ok) throw new Error('Failed to record outcome');
  return response.json();
};

export const queryLocation = async (chainage = 76.5, radius_km = 5.0, corridor_id = 'SBC-JTJ') => {
  const response = await fetch(
    `${API_BASE_URL}/location-query?chainage=${chainage}&radius_km=${radius_km}&corridor_id=${encodeURIComponent(corridor_id)}`
  );
  if (!response.ok) throw new Error('Failed to execute location query');
  return response.json();
};

export const fetchBlocks = async (corridor_id = 'SBC-JTJ') => {
  const url = corridor_id ? `${API_BASE_URL}/blocks?corridor_id=${encodeURIComponent(corridor_id)}` : `${API_BASE_URL}/blocks`;
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to fetch planned blocks');
  return response.json();
};

export const fetchBlockDecisions = async (blockId) => {
  const response = await fetch(`${API_BASE_URL}/blocks/${blockId}/decisions`);
  if (!response.ok) throw new Error('Failed to fetch block decisions');
  return response.json();
};

export const fetchLatestOptimizationRun = async (corridor_id = 'SBC-JTJ') => {
  const url = corridor_id ? `${API_BASE_URL}/optimization/runs/latest?corridor_id=${encodeURIComponent(corridor_id)}` : `${API_BASE_URL}/optimization/runs/latest`;
  const response = await fetch(url);
  if (!response.ok) return null;
  return response.json();
};

export const overrideTaskPriority = async (taskId, payload) => {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/override-priority`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to override priority');
  }
  return response.json();
};

