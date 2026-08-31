import { formatDuration } from '../utils/formatters';

export default function TaskTable({ tasks, blocks, taskStatuses }) {
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

  return (
    <div className="bg-white border border-rail-border rounded-lg shadow-sm overflow-hidden">
      <div className="p-4 border-b border-rail-border flex justify-between items-center bg-rail-bg/50">
        <div>
          <h3 className="text-lg font-semibold text-rail-text-dark">Maintenance Requests Pool</h3>
          <p className="text-xs text-rail-text-muted">Prioritized work list for the corridor</p>
        </div>
      </div>
      
      <div className="overflow-x-auto max-h-96">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-rail-text-muted bg-gray-50 sticky top-0 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 font-semibold">Activity</th>
              <th className="px-4 py-3 font-semibold">Location</th>
              <th className="px-4 py-3 font-semibold">Condition / Severity</th>
              <th className="px-4 py-3 font-semibold">Priority</th>
              <th className="px-4 py-3 font-semibold">Estimated Time</th>
              <th className="px-4 py-3 font-semibold">AI Decision Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {tasks.map((task) => {
              const { status, blockId, isConsolidated } = getTaskInfo(task.id);
              
              return (
                <tr key={task.id} className="hover:bg-blue-50/30 transition-colors">
                  <td className="px-4 py-4">
                    <div className="flex flex-col gap-1 items-start">
                      <span className="text-sm font-medium text-gray-800">{task.task_type}</span>
                      <span className="text-[10px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded" title={`Department: ${task.department}`}>
                        {task.origin === 'Defect' ? 'Unplanned Defect' : 'Routine Maintenance'}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex flex-col">
                      <span className="text-sm text-gray-700">
                        {task.line_direction === 'Up' ? 'Toward Jolarpettai' : task.line_direction === 'Down' ? 'Toward Bengaluru' : 'Both Directions'}
                      </span>
                      <span className="text-xs text-gray-500" title={`Start Km: ${task.start_km}, End Km: ${task.end_km}`}>
                        Between Km {task.start_km.toFixed(1)} and {task.end_km.toFixed(1)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex flex-col items-start gap-1">
                      {getSeverityBadge(task.severity)}
                      {task.overdue_days > 0 && (
                        <span className="text-[10px] text-red-600 font-medium">
                          {task.overdue_days} Days Overdue
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-4 min-w-[220px]">
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-bold text-white px-1.5 py-0.5 rounded uppercase" style={{
                          backgroundColor: task.priority_details?.category === 'Critical' ? '#dc2626' : task.priority_details?.category === 'High' ? '#ea580c' : task.priority_details?.category === 'Medium' ? '#ca8a04' : '#16a34a'
                        }}>
                          {task.priority_details?.category || 'Low'} Priority
                        </span>
                        <span className="text-xs font-semibold text-gray-500" title="Calculated Priority Score">
                          ({task.priority_details?.score || 0}/100)
                        </span>
                      </div>
                      <p className="text-[11px] text-gray-500 leading-tight">
                        {task.priority_details?.explanation || 'Standard maintenance.'}
                      </p>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-sm text-gray-700">
                    <div className="flex flex-col">
                      <span>{formatDuration(task.duration_mins)}</span>
                      <span className="text-[10px] text-gray-400 mt-0.5" title={`Deadline in ${task.deadline_mins} mins`}>
                        Must finish in {Math.round(task.deadline_mins / 60)}h
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    {status === 'Planned' && (
                      <div className="flex flex-col">
                        <span className="text-green-700 font-semibold flex items-center gap-1.5 text-sm">
                          <span className="w-2 h-2 rounded-full bg-green-500 inline-block shadow-sm"></span>
                          Scheduled
                        </span>
                        <div className="text-[11px] text-gray-500 mt-1">
                          {isConsolidated ? 'Grouped with other tasks.' : 'Safe standalone window.'}
                        </div>
                      </div>
                    )}
                    {status === 'Deferred' && (
                      <div className="flex flex-col">
                        <span className="text-amber-600 font-semibold flex items-center gap-1.5 text-sm">
                          <span className="w-2 h-2 rounded-full bg-amber-500 inline-block shadow-sm"></span>
                          Deferred
                        </span>
                        <div className="text-[11px] text-gray-500 mt-1">Track busy / low priority.</div>
                      </div>
                    )}
                    {status === 'Infeasible' && (
                      <div className="flex flex-col">
                        <span className="text-red-600 font-semibold flex items-center gap-1.5 text-sm">
                          <span className="w-2 h-2 rounded-full bg-red-500 inline-block shadow-sm"></span>
                          Cannot Schedule
                        </span>
                        <div className="text-[11px] text-gray-500 mt-1">No safe window before deadline.</div>
                      </div>
                    )}
                    {status === 'Pending' && (
                      <span className="text-gray-500 font-medium flex items-center gap-1.5 text-sm">
                        <span className="w-2 h-2 rounded-full bg-gray-300 inline-block"></span>
                        Awaiting Optimization
                      </span>
                    )}
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
