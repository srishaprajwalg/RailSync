import { useState } from 'react';
import { addTask } from '../services/api';

export default function TaskForm({ onTaskAdded }) {
  const [formData, setFormData] = useState({
    department: 'TMS',
    start_km: '',
    end_km: '',
    duration_mins: '',
    severity: 1,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'department' ? value : Number(value) || '',
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = {
        ...formData,
        start_km: Number(formData.start_km),
        end_km: Number(formData.end_km),
        duration_mins: Number(formData.duration_mins),
        severity: Number(formData.severity),
      };
      const updatedTasks = await addTask(payload);
      onTaskAdded(updatedTasks);
      setFormData({
        department: 'TMS',
        start_km: '',
        end_km: '',
        duration_mins: '',
        severity: 1,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-rail-border mb-6">
      <h3 className="text-lg font-semibold text-rail-text-dark mb-4">Manual Maintenance Entry</h3>
      {error && <div className="text-red-500 text-sm mb-3">{error}</div>}
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-6 gap-4 items-end">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
          <select
            name="department"
            value={formData.department}
            onChange={handleChange}
            className="w-full border border-gray-300 rounded p-2 text-sm"
          >
            <option value="TMS">TMS</option>
            <option value="SMMS">SMMS</option>
            <option value="TDMS">TDMS</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Start Km</label>
          <input
            type="number"
            name="start_km"
            value={formData.start_km}
            onChange={handleChange}
            step="0.1"
            required
            className="w-full border border-gray-300 rounded p-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">End Km</label>
          <input
            type="number"
            name="end_km"
            value={formData.end_km}
            onChange={handleChange}
            step="0.1"
            required
            className="w-full border border-gray-300 rounded p-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Duration (mins)</label>
          <input
            type="number"
            name="duration_mins"
            value={formData.duration_mins}
            onChange={handleChange}
            required
            className="w-full border border-gray-300 rounded p-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Severity (1-5)</label>
          <input
            type="number"
            name="severity"
            value={formData.severity}
            onChange={handleChange}
            min="1"
            max="5"
            required
            className="w-full border border-gray-300 rounded p-2 text-sm"
          />
        </div>
        <div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-rail-blue text-white py-2 px-4 rounded hover:bg-rail-blue/90 disabled:opacity-50 text-sm font-medium transition-colors"
          >
            {loading ? 'Adding...' : 'Add Task'}
          </button>
        </div>
      </form>
    </div>
  );
}
