import { formatDuration } from '../utils/formatters';

export default function TaskTable({ tasks, blocks }) {
  // Map tasks to their assigned block status
  const getTaskStatus = (taskId) => {
    const block = blocks.find(b => b.assigned_tasks.includes(taskId));
    return block ? { status: 'Planned', blockId: block.id, isConsolidated: block.assigned_tasks.length > 1 } : { status: 'Pending', blockId: null };
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
              <th className="px-4 py-3 font-semibold">Dept</th>
              <th className="px-4 py-3 font-semibold">Task Type</th>
              <th className="px-4 py-3 font-semibold">Location</th>
              <th className="px-4 py-3 font-semibold">Line</th>
              <th className="px-4 py-3 font-semibold">Duration</th>
              <th className="px-4 py-3 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rail-border">
            {tasks.map((task) => {
              const { status, blockId, isConsolidated } = getTaskStatus(task.id);
              
              return (
                <tr key={task.id} className="hover:bg-rail-bg/50">
                  <td className="px-4 py-3 font-mono text-xs">{task.id}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-semibold bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                      {task.department}
                    </span>
                  </td>
                  <td className="px-4 py-3">{task.task_type}</td>
                  <td className="px-4 py-3 text-rail-text-muted">Km {task.start_km.toFixed(1)} - {task.end_km.toFixed(1)}</td>
                  <td className="px-4 py-3">{task.line_direction}</td>
                  <td className="px-4 py-3">{formatDuration(task.duration_mins)}</td>
                  <td className="px-4 py-3">
                    {status === 'Planned' ? (
                      <div className="flex flex-col">
                        <span className="text-rail-green font-medium flex items-center gap-1 text-xs">
                          <span className="w-1.5 h-1.5 rounded-full bg-rail-green inline-block"></span>
                          Planned in BLK-{blockId.substring(0,4)}
                        </span>
                        {isConsolidated && <span className="text-[10px] text-rail-saffron mt-0.5">Consolidated</span>}
                      </div>
                    ) : (
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
