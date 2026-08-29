import { formatDuration } from '../utils/formatters';

export default function TaskTable({ tasks, blocks, taskStatuses }) {
  // Map tasks to their assigned block status
  const getTaskInfo = (taskId) => {
    const block = blocks.find(b => b.assigned_tasks.includes(taskId));
    const status = taskStatuses && taskStatuses[taskId] ? taskStatuses[taskId] : (block ? 'Planned' : 'Pending');
    return { status, blockId: block ? block.id : null, isConsolidated: block && block.assigned_tasks.length > 1 };
  };

  return (
    <div className="bg-white border border-rail-border rounded-lg shadow-sm overflow-hidden">
      <div className="p-4 border-b border-rail-border flex justify-between items-center bg-rail-bg/50">
        <div>
          <h3 className="text-lg font-semibold text-rail-text-dark">Maintenance Requests Pool</h3>
          <p className="text-xs text-rail-text-muted">All incoming tasks from TMS, SMMS, TDMS</p>
        </div>
      </div>
      
      <div className="overflow-x-auto max-h-96">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-rail-text-muted bg-rail-bg sticky top-0">
            <tr>
              <th className="px-4 py-3 font-semibold">ID</th>
              <th className="px-4 py-3 font-semibold">Dept & Type</th>
              <th className="px-4 py-3 font-semibold">Location</th>
              <th className="px-4 py-3 font-semibold">Duration</th>
              <th className="px-4 py-3 font-semibold min-w-[200px]">Priority & AI Explanation</th>
              <th className="px-4 py-3 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rail-border">
            {tasks.map((task) => {
              const { status, blockId, isConsolidated } = getTaskInfo(task.id);
              
              return (
                <tr key={task.id} className="hover:bg-rail-bg/50">
                  <td className="px-4 py-3 font-mono text-xs">{task.id}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1 items-start">
                      <span className="text-xs font-semibold bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                        {task.department}
                      </span>
                      <span className="text-xs text-rail-text-dark">{task.task_type}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-rail-text-muted text-xs">
                    <div>{task.line_direction} Line</div>
                    <div>Km {task.start_km.toFixed(1)} - {task.end_km.toFixed(1)}</div>
                  </td>
                  <td className="px-4 py-3 text-xs">{formatDuration(task.duration_mins)}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-bold ${task.priority_details?.score >= 60 ? 'text-rail-error' : task.priority_details?.score >= 30 ? 'text-rail-saffron' : 'text-rail-green'}`}>
                          Score: {task.priority_details?.score || 0}
                        </span>
                        <span className="text-xs text-rail-text-muted bg-gray-100 px-1.5 py-0.5 rounded">
                          {task.priority_details?.category || 'Routine'}
                        </span>
                      </div>
                      <p className="text-[10px] text-rail-text-muted mt-1 leading-tight line-clamp-2" title={task.priority_details?.explanation}>
                        {task.priority_details?.explanation || 'Standard maintenance.'}
                      </p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {status === 'Planned' && (
                      <div className="flex flex-col">
                        <span className="text-rail-green font-medium flex items-center gap-1 text-xs">
                          <span className="w-1.5 h-1.5 rounded-full bg-rail-green inline-block"></span>
                          Planned (BLK-{blockId?.substring(0,4)})
                        </span>
                        {isConsolidated && <span className="text-[10px] text-rail-saffron mt-0.5">Consolidated</span>}
                      </div>
                    )}
                    {status === 'Deferred' && (
                      <span className="text-rail-saffron font-medium flex items-center gap-1 text-xs">
                        <span className="w-1.5 h-1.5 rounded-full bg-rail-saffron inline-block"></span>
                        Deferred
                      </span>
                    )}
                    {status === 'Infeasible' && (
                      <span className="text-rail-error font-medium flex items-center gap-1 text-xs">
                        <span className="w-1.5 h-1.5 rounded-full bg-rail-error inline-block"></span>
                        Infeasible
                      </span>
                    )}
                    {status === 'Pending' && (
                      <span className="text-rail-text-muted font-medium flex items-center gap-1 text-xs">
                        <span className="w-1.5 h-1.5 rounded-full bg-gray-300 inline-block"></span>
                        Pending
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
