import { useState, useEffect } from 'react';
import { addTask, previewPriority, fetchTaskDefaults } from '../services/api';
import { AlertCircle, Clock, Calendar, Activity } from 'lucide-react';

export default function TaskForm({ onTaskAdded, corridorId }) {
  const [taskDefaults, setTaskDefaults] = useState({});
  const [formData, setFormData] = useState({
    department: 'TMS',
    task_type: 'Track Tamping',
    start_km: '',
    end_km: '',
    duration_mins: 120,
    origin: 'Routine Maintenance',
    severity: 1,
    asset_criticality: 3,
    overdue_days: 0,
    deadline_mins: 1440, // default 24h
    line_direction: 'Up',
  });
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Priority Preview State
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Fetch Defaults
  useEffect(() => {
    fetchTaskDefaults().then(defaults => {
      setTaskDefaults(defaults);
      if (Object.keys(defaults).length > 0) {
        const firstKey = Object.keys(defaults)[0];
        setFormData(prev => ({
          ...prev,
          task_type: firstKey,
          department: defaults[firstKey].department,
          duration_mins: defaults[firstKey].duration_mins,
          required_resource: defaults[firstKey].required_resource
        }));
      }
    }).catch(err => console.error("Failed to load task defaults", err));
  }, []);

  // Debounced Priority Fetch
  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        setPreviewLoading(true);
        const payload = {
          ...formData,
          start_km: Number(formData.start_km) || 0,
          end_km: Number(formData.end_km) || 0,
          duration_mins: Number(formData.duration_mins) || 60,
          severity: Number(formData.severity),
          asset_criticality: Number(formData.asset_criticality),
          overdue_days: Number(formData.overdue_days) || 0,
          deadline_mins: Number(formData.deadline_mins),
          corridor_id: corridorId,
        };
        const result = await previewPriority(payload);
        setPreview(result);
      } catch (err) {
        console.error("Failed to fetch priority preview:", err);
      } finally {
        setPreviewLoading(false);
      }
    }, 500); // 500ms debounce
    return () => clearTimeout(timer);
  }, [formData]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    
    setFormData((prev) => {
      const updates = { [name]: value };
      
      // Auto-update duration and department if task type changes
      if (name === 'task_type' && taskDefaults[value]) {
        updates.duration_mins = taskDefaults[value].duration_mins;
        updates.department = taskDefaults[value].department;
        updates.required_resource = taskDefaults[value].required_resource;
      }
      
      return { ...prev, ...updates };
    });
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
        asset_criticality: Number(formData.asset_criticality),
        overdue_days: Number(formData.overdue_days),
        deadline_mins: Number(formData.deadline_mins),
        corridor_id: corridorId,
      };
      const updatedTasks = await addTask(payload);
      onTaskAdded(updatedTasks);
      // Reset form slightly
      setFormData(prev => ({
        ...prev,
        start_km: '',
        end_km: '',
        overdue_days: 0,
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-rail-border mb-6">
      <div className="flex flex-col lg:flex-row gap-8">
        
        {/* Form Area */}
        <div className="flex-1">
          <h3 className="text-xl font-bold text-rail-text-dark mb-1">Add New Maintenance Request</h3>
          <p className="text-sm text-gray-500 mb-6">RailVyuha will calculate priority automatically based on the details below.</p>
          
          {error && <div className="text-red-500 text-sm mb-4 bg-red-50 p-2 rounded">{error}</div>}
          
          <form onSubmit={handleSubmit} className="space-y-6">
            
            {/* Section A: What Needs Maintenance */}
            <div className="border border-gray-100 rounded-lg p-4 bg-gray-50/50">
              <h4 className="font-semibold text-rail-text-dark flex items-center gap-2 mb-4">
                <Activity className="w-4 h-4 text-rail-blue" />
                A. What Needs Maintenance?
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Maintenance Activity</label>
                  <select name="task_type" value={formData.task_type} onChange={handleChange} className="w-full border border-gray-300 rounded p-2 text-sm bg-white">
                    {Object.keys(taskDefaults).map(task => (
                      <option key={task} value={task}>{task}</option>
                    ))}
                  </select>
                  <div className="flex flex-col gap-1 mt-2">
                    <p className="text-xs text-rail-blue font-medium bg-blue-50 inline-block px-2 py-1 rounded w-fit">
                      Routed to: {formData.department || (taskDefaults[formData.task_type]?.department)}
                    </p>
                    <p className="text-xs text-purple-700 font-medium bg-purple-50 inline-block px-2 py-1 rounded w-fit">
                      Required resource: {formData.required_resource || (taskDefaults[formData.task_type]?.required_resource)}
                    </p>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Line Direction</label>
                  <select name="line_direction" value={formData.line_direction} onChange={handleChange} className="w-full border border-gray-300 rounded p-2 text-sm bg-white">
                    <option value="Up">Toward Jolarpettai (Up Line)</option>
                    <option value="Down">Toward Bengaluru (Down Line)</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Start Location (Km)</label>
                  <input type="number" name="start_km" value={formData.start_km} onChange={handleChange} step="0.1" required placeholder="e.g. 10.5" className="w-full border border-gray-300 rounded p-2 text-sm bg-white" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">End Location (Km)</label>
                  <input type="number" name="end_km" value={formData.end_km} onChange={handleChange} step="0.1" required placeholder="e.g. 12.0" className="w-full border border-gray-300 rounded p-2 text-sm bg-white" />
                </div>
              </div>
            </div>

            {/* Section B: How Urgent Is It? */}
            <div className="border border-gray-100 rounded-lg p-4 bg-gray-50/50">
              <h4 className="font-semibold text-rail-text-dark flex items-center gap-2 mb-4">
                <AlertCircle className="w-4 h-4 text-rail-saffron" />
                B. How Urgent Is It?
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nature of Work</label>
                  <select name="origin" value={formData.origin} onChange={handleChange} className="w-full border border-gray-300 rounded p-2 text-sm bg-white">
                    <option value="Routine Maintenance">Planned Routine Maintenance</option>
                    <option value="Defect">Unplanned Defect / Failure</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Severity / Condition</label>
                  <select name="severity" value={formData.severity} onChange={handleChange} className="w-full border border-gray-300 rounded p-2 text-sm bg-white">
                    <option value="1">Low (Minor attention needed)</option>
                    <option value="3">Medium (Degraded performance)</option>
                    <option value="5">Critical (Safety hazard)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Asset Importance</label>
                  <select name="asset_criticality" value={formData.asset_criticality} onChange={handleChange} className="w-full border border-gray-300 rounded p-2 text-sm bg-white">
                    <option value="1">Normal Track Section</option>
                    <option value="3">Important Route / Junction</option>
                    <option value="5">Highly Critical Asset</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Days Overdue</label>
                  <input type="number" name="overdue_days" value={formData.overdue_days} onChange={handleChange} min="0" className="w-full border border-gray-300 rounded p-2 text-sm bg-white" />
                </div>
              </div>
            </div>

            {/* Section C & D: Time & Deadline */}
            <div className="border border-gray-100 rounded-lg p-4 bg-gray-50/50 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="font-semibold text-rail-text-dark flex items-center gap-2 mb-2">
                  <Clock className="w-4 h-4 text-gray-500" />
                  C. Expected Work Time
                </h4>
                <label className="block text-sm text-gray-600 mb-1">Duration (minutes)</label>
                <input type="number" name="duration_mins" value={formData.duration_mins} onChange={handleChange} required className="w-full border border-gray-300 rounded p-2 text-sm bg-white" />
                <p className="text-xs text-gray-500 mt-1">Standard estimate based on selected activity. Adjust if needed.</p>
              </div>
              <div>
                <h4 className="font-semibold text-rail-text-dark flex items-center gap-2 mb-2">
                  <Calendar className="w-4 h-4 text-gray-500" />
                  D. Operational Deadline
                </h4>
                <label className="block text-sm text-gray-600 mb-1">Must be completed within</label>
                <select name="deadline_mins" value={formData.deadline_mins} onChange={handleChange} className="w-full border border-gray-300 rounded p-2 text-sm bg-white">
                  <option value="1440">24 Hours (1 Day)</option>
                  <option value="4320">72 Hours (3 Days)</option>
                  <option value="10080">1 Week (7 Days)</option>
                  <option value="43200">1 Month (30 Days)</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-rail-blue text-white py-3 px-4 rounded font-medium hover:bg-rail-blue/90 disabled:opacity-50 transition-colors shadow-sm"
            >
              {loading ? 'Adding Request to System...' : 'Submit Maintenance Request'}
            </button>
          </form>
        </div>

        {/* Priority Preview Panel */}
        <div className="lg:w-80 shrink-0">
          <div className="bg-rail-bg border border-rail-border rounded-lg p-6 sticky top-6">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4">RailVyuha Priority Preview</h3>
            
            {previewLoading ? (
              <div className="animate-pulse flex space-x-4">
                <div className="flex-1 space-y-4 py-1">
                  <div className="h-10 bg-gray-200 rounded w-3/4"></div>
                  <div className="space-y-2">
                    <div className="h-4 bg-gray-200 rounded"></div>
                    <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                  </div>
                </div>
              </div>
            ) : preview ? (
              <div>
                <div className="flex items-end gap-2 mb-2">
                  <span className={`text-4xl font-extrabold ${preview.score >= 80 ? 'text-red-600' : preview.score >= 60 ? 'text-orange-500' : preview.score >= 40 ? 'text-yellow-600' : 'text-green-600'}`}>
                    {preview.score}
                  </span>
                  <span className="text-gray-500 font-medium mb-1">/ 100</span>
                </div>
                <div className="inline-block px-3 py-1 rounded text-xs font-bold uppercase tracking-wide mb-6" style={{
                  backgroundColor: preview.category === 'Critical' ? '#fee2e2' : preview.category === 'High' ? '#ffedd5' : preview.category === 'Medium' ? '#fef9c3' : '#dcfce7',
                  color: preview.category === 'Critical' ? '#991b1b' : preview.category === 'High' ? '#9a3412' : preview.category === 'Medium' ? '#854d0e' : '#166534'
                }}>
                  {preview.category} PRIORITY
                </div>
                
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Why?</h4>
                <p className="text-sm text-gray-600 mb-6 bg-white p-3 rounded border border-gray-100">
                  {preview.explanation}
                </p>

                <h4 className="text-sm font-semibold text-gray-700 mb-2">Recommendation:</h4>
                <p className="text-sm text-gray-600 bg-white p-3 rounded border border-gray-100">
                  {preview.category === 'Critical' || preview.category === 'High' 
                    ? 'Schedule at the earliest suitable maintenance opportunity.' 
                    : 'Defer if capacity is constrained by higher priority blocks.'}
                </p>
              </div>
            ) : (
              <div className="text-sm text-gray-500 italic">Fill out the form to see AI priority preview.</div>
            )}
          </div>
        </div>
        
      </div>
    </div>
  );
}
