import { useState } from 'react';
import { formatDuration } from '../utils/formatters';
import { CheckCircle2, PlayCircle, Clock } from 'lucide-react';

export default function TaskTable({ tasks, blocks, taskStatuses, onUpdateStatus }) {
  const [filterDept, setFilterDept] = useState('All');
  const [filterState, setFilterState] = useState('Active'); // Active or Completed

  // Map tasks to their assigned block status
  const getTaskInfo = (taskId) => {
    const block = blocks.find(b => b.assigned_tasks.includes(taskId));
    const status = taskStatuses && taskStatuses[taskId] ? taskStatuses[taskId] : (block ? 'Planned' : 'Pending');
    return { status, blockId: block ? block.id : null, isConsolidated: block && block.assigned_tasks.length > 1 };
  };

  const getSeverityBadge = (severity) => {
    if (severity >= 5) return <span className="bg-red-100 text-red-800 text-[10px] px-1.5 py-0.5 rounded font-bold uppercase">Critical</span>;
    if (severity >= 3) return <span className="bg-yellow-100 text-yellow-800 text-[10px] px-1.5 py-0.5 rounded font-bold uppercase">Medium</span>;
    return <span className="bg-gray-100 text-gray-800 text-[10px] px-1.5 py-0.5 rounded font-bold uppercase">Low</span>;
  };

  const departments = ['All', ...new Set(tasks.map(t => t.department))];

  const filteredTasks = tasks.filter(task => {
    const deptMatch = filterDept === 'All' || task.department === filterDept;
    const stateMatch = filterState === 'Completed' ? task.lifecycle_status === 'Completed' : task.lifecycle_status !== 'Completed';
    return deptMatch && stateMatch;
  });

  return (
    <div className="bg-white border border-rail-border rounded-lg shadow-sm overflow-hidden">
      <div className="p-4 border-b border-rail-border flex flex-col sm:flex-row justify-between items-start sm:items-center bg-rail-bg/50 gap-4">
        <div>
          <h3 className="text-lg font-semibold text-rail-text-dark">Maintenance Requests</h3>
          <p className="text-xs text-rail-text-muted">Manage workflow and track request history</p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-4 items-center">
          <div className="flex bg-gray-100 p-1 rounded-md">
            <button
              onClick={() => setFilterState('Active')}
              className={`px-4 py-1 text-sm font-medium rounded ${filterState === 'Active' ? 'bg-white shadow-sm text-rail-blue' : 'text-gray-500 hover:text-gray-700'}`}
            >
              Active Tasks
            </button>
            <button
              onClick={() => setFilterState('Completed')}
              className={`px-4 py-1 text-sm font-medium rounded ${filterState === 'Completed' ? 'bg-white shadow-sm text-green-600' : 'text-gray-500 hover:text-gray-700'}`}
            >
              History
            </button>
          </div>
          
          <select 
            value={filterDept} 
            onChange={(e) => setFilterDept(e.target.value)}
            className="border border-gray-300 rounded p-1.5 text-sm bg-white min-w-[150px]"
          >
            {departments.map(dept => (
              <option key={dept} value={dept}>{dept === 'All' ? 'All Departments' : dept}</option>
            ))}
          </select>
        </div>
      </div>
      
      <div className="overflow-x-auto max-h-[500px]">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-rail-text-muted bg-gray-50 sticky top-0 border-b border-gray-200 z-10">
            <tr>
              <th className="px-4 py-3 font-semibold">Activity & Dept</th>
              <th className="px-4 py-3 font-semibold">Location</th>
              <th className="px-4 py-3 font-semibold">Severity / Priority</th>
              <th className="px-4 py-3 font-semibold">AI Planning Status</th>
              <th className="px-4 py-3 font-semibold text-right">Lifecycle Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredTasks.length === 0 ? (
              <tr>
                <td colSpan="5" className="px-4 py-8 text-center text-gray-500 italic">
                  No {filterState.toLowerCase()} tasks found for {filterDept}.
                </td>
              </tr>
            ) : filteredTasks.map((task) => {
              const { status, isConsolidated } = getTaskInfo(task.id);
              
              return (
                <tr key={task.id} className="hover:bg-blue-50/30 transition-colors">
                  <td className="px-4 py-4">
                    <div className="flex flex-col gap-1 items-start">
                      <span className="text-sm font-medium text-gray-800">{task.task_type}</span>
                      <span className="text-xs text-rail-blue font-medium">{task.department}</span>
                      <span className="text-[10px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                        {task.origin === 'Defect' ? 'Unplanned Defect' : 'Routine Maintenance'}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex flex-col">
                      <span className="text-sm text-gray-700">
                        {task.line_direction === 'Up' ? 'Toward Jolarpettai' : task.line_direction === 'Down' ? 'Toward Bengaluru' : 'Both Directions'}
                      </span>
                      <span className="text-xs text-gray-500">
                        Km {task.start_km.toFixed(1)} to {task.end_km.toFixed(1)}
                      </span>
                      <span className="text-xs text-gray-500 mt-1">
                        Est: {formatDuration(task.duration_mins)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex flex-col items-start gap-2">
                      <div className="flex items-center gap-2">
                        {getSeverityBadge(task.severity)}
                        <span className="text-[10px] font-bold text-white px-1.5 py-0.5 rounded uppercase" style={{
                          backgroundColor: task.priority_details?.category === 'Critical' ? '#dc2626' : task.priority_details?.category === 'High' ? '#ea580c' : task.priority_details?.category === 'Medium' ? '#ca8a04' : '#16a34a'
                        }}>
                          {task.priority_details?.category || 'Low'}
                        </span>
                      </div>
                      {task.overdue_days > 0 && (
                        <span className="text-[10px] text-red-600 font-medium bg-red-50 px-1.5 py-0.5 rounded">
                          {task.overdue_days} Days Overdue
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    {filterState === 'Completed' ? (
                       <span className="text-gray-400 italic text-sm">Archived</span>
                    ) : (
                      <>
                        {status === 'Planned' && (
                          <div className="flex flex-col">
                            <span className="text-green-700 font-semibold flex items-center gap-1.5 text-sm">
                              <span className="w-2 h-2 rounded-full bg-green-500 inline-block shadow-sm"></span>
                              Scheduled
                            </span>
                            <div className="text-[11px] text-gray-500 mt-1">
                              {isConsolidated ? 'Grouped Block' : 'Standalone Block'}
                            </div>
                          </div>
                        )}
                        {status === 'Deferred' && (
                          <div className="flex flex-col">
                            <span className="text-amber-600 font-semibold flex items-center gap-1.5 text-sm">
                              <span className="w-2 h-2 rounded-full bg-amber-500 inline-block shadow-sm"></span>
                              Deferred
                            </span>
                          </div>
                        )}
                        {status === 'Infeasible' && (
                          <div className="flex flex-col">
                            <span className="text-red-600 font-semibold flex items-center gap-1.5 text-sm">
                              <span className="w-2 h-2 rounded-full bg-red-500 inline-block shadow-sm"></span>
                              Cannot Schedule
                            </span>
                          </div>
                        )}
                        {status === 'Pending' && (
                          <span className="text-gray-500 font-medium flex items-center gap-1.5 text-sm">
                            <span className="w-2 h-2 rounded-full bg-gray-300 inline-block"></span>
                            Awaiting CP-SAT
                          </span>
                        )}
                      </>
                    )}
                  </td>
                  <td className="px-4 py-4 text-right">
                    <div className="flex flex-col items-end gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] uppercase tracking-wider font-semibold text-gray-500">State:</span>
                        <span className="text-xs font-bold text-rail-blue bg-blue-50 px-2 py-1 rounded">
                          {task.lifecycle_status}
                        </span>
                      </div>
                      
                      {onUpdateStatus && filterState === 'Active' && (
                        <div className="flex gap-2 mt-1">
                          {task.lifecycle_status !== 'In Progress' && (
                            <button 
                              onClick={() => onUpdateStatus(task.id, 'In Progress')}
                              className="text-xs flex items-center gap-1 bg-amber-50 hover:bg-amber-100 text-amber-700 px-2 py-1 rounded transition-colors"
                              title="Mark as currently being worked on"
                            >
                              <PlayCircle className="w-3 h-3" /> Start Work
                            </button>
                          )}
                          <button 
                            onClick={() => onUpdateStatus(task.id, 'Completed')}
                            className="text-xs flex items-center gap-1 bg-green-50 hover:bg-green-100 text-green-700 px-2 py-1 rounded transition-colors"
                            title="Mark as completed and remove from active planning"
                          >
                            <CheckCircle2 className="w-3 h-3" /> Complete
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
