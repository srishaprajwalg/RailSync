import { useState } from 'react';
import { formatDuration } from '../utils/formatters';
import { CheckCircle2, PlayCircle, Clock, Brain, FileCheck, Layers, Sliders, AlertCircle, HelpCircle } from 'lucide-react';
import PriorityExplanationModal from './PriorityExplanationModal';
import OutcomeLoggingModal from './OutcomeLoggingModal';
import PriorityOverrideModal from './PriorityOverrideModal';

export default function TaskTable({ tasks, blocks, taskStatuses, onUpdateStatus, onReloadTasks }) {
  const [filterState, setFilterState] = useState('Active'); // Active or Completed
  const [selectedTaskForExplain, setSelectedTaskForExplain] = useState(null);
  const [selectedTaskForOutcome, setSelectedTaskForOutcome] = useState(null);
  const [selectedTaskForOverride, setSelectedTaskForOverride] = useState(null);

  // Map tasks to their assigned block status
  const getTaskInfo = (task) => {
    const block = blocks ? blocks.find(b => b.assigned_tasks && b.assigned_tasks.includes(task.id)) : null;
    let status = taskStatuses && taskStatuses[task.id] ? taskStatuses[task.id] : (block ? 'Planned' : 'Pending');
    if (status === 'Pending') {
      if (task.lifecycle_status === 'Infeasible' || task.status === 'Infeasible') {
        status = 'Infeasible';
      } else if (task.lifecycle_status === 'Deferred' || task.status === 'Deferred') {
        status = 'Deferred';
      }
    }
    return { status, blockId: block ? block.id : null, isConsolidated: block && block.assigned_tasks && block.assigned_tasks.length > 1 };
  };

  const getSeverityBadge = (severity) => {
    if (severity >= 5) return <span className="bg-red-100 text-red-800 text-[10px] px-1.5 py-0.5 rounded font-bold uppercase">Critical</span>;
    if (severity >= 3) return <span className="bg-yellow-100 text-yellow-800 text-[10px] px-1.5 py-0.5 rounded font-bold uppercase">Medium</span>;
    return <span className="bg-gray-100 text-gray-800 text-[10px] px-1.5 py-0.5 rounded font-bold uppercase">Low</span>;
  };

  const filteredTasks = tasks.filter(task => {
    const stateMatch = filterState === 'Completed' ? (task.lifecycle_status === 'Completed' || task.lifecycle_status === 'COMPLETED') : (task.lifecycle_status !== 'Completed' && task.lifecycle_status !== 'COMPLETED');
    return stateMatch;
  });

  return (
    <div className="bg-white border border-rail-border rounded-lg shadow-sm overflow-hidden">
      {/* Explainability Modal */}
      <PriorityExplanationModal
        taskId={selectedTaskForExplain}
        isOpen={Boolean(selectedTaskForExplain)}
        onClose={() => setSelectedTaskForExplain(null)}
      />

      {/* Outcome Logging Modal */}
      <OutcomeLoggingModal
        task={selectedTaskForOutcome}
        isOpen={Boolean(selectedTaskForOutcome)}
        onClose={() => setSelectedTaskForOutcome(null)}
        onOutcomeRecorded={() => {
          if (onReloadTasks) onReloadTasks();
        }}
      />

      {/* Priority Override Modal */}
      <PriorityOverrideModal
        task={selectedTaskForOverride}
        isOpen={Boolean(selectedTaskForOverride)}
        onClose={() => setSelectedTaskForOverride(null)}
        onPriorityOverridden={() => {
          if (onReloadTasks) onReloadTasks();
        }}
      />

      <div className="p-4 border-b border-rail-border flex flex-col sm:flex-row justify-between items-start sm:items-center bg-rail-bg/50 gap-4">
        <div>
          <h3 className="text-lg font-semibold text-rail-text-dark">Maintenance Requests & Assets (System of Record)</h3>
          <p className="text-xs text-rail-text-muted">PostgreSQL backed request lifecycle, ML recurrence predictions, and execution outcomes</p>
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
              History & Outcomes
            </button>
          </div>
        </div>
      </div>
      
      <div className="overflow-x-auto max-h-[520px]">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-rail-text-muted bg-gray-50 sticky top-0 border-b border-gray-200 z-10">
            <tr>
              <th className="px-4 py-3 font-semibold">Activity & Department</th>
              <th className="px-4 py-3 font-semibold">Location & Asset</th>
              <th className="px-4 py-3 font-semibold">AI Priority & ML Risk</th>
              <th className="px-4 py-3 font-semibold">CP-SAT Status</th>
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
              const { status, isConsolidated } = getTaskInfo(task);
              
              return (
                <tr key={task.id} className="hover:bg-blue-50/30 transition-colors">
                  <td className="px-4 py-3.5">
                    <div className="flex flex-col gap-1 items-start">
                      <span className="text-sm font-medium text-gray-800">{task.task_type}</span>
                      <span className="text-xs text-rail-blue font-medium">{task.department}</span>
                      <div className="flex gap-1 items-center">
                        <span className="text-[10px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                          {task.origin === 'Defect' ? 'Unplanned Defect' : 'Routine Maintenance'}
                        </span>
                        <span className="text-[9px] font-mono text-gray-400">
                          {task.source_type || 'SYNTHETIC'}
                        </span>
                      </div>
                    </div>
                  </td>

                  <td className="px-4 py-3.5">
                    <div className="flex flex-col">
                      <span className="text-sm text-gray-700">
                        {task.line_direction === 'Up' ? 'Toward Jolarpettai' : task.line_direction === 'Down' ? 'Toward Bengaluru' : 'Both Directions'}
                      </span>
                      <span className="text-xs text-gray-500">
                        Km {task.start_km.toFixed(1)} to {task.end_km.toFixed(1)}
                      </span>
                      <span className="text-xs text-gray-500 mt-0.5">
                        Est: {formatDuration(task.duration_mins)}
                      </span>
                    </div>
                  </td>

                  <td className="px-4 py-3.5">
                    <div className="flex flex-col items-start gap-1.5">
                      <div className="flex items-center gap-2">
                        {getSeverityBadge(task.severity)}
                        <button
                          onClick={() => setSelectedTaskForExplain(task.id)}
                          className="text-[10px] font-bold text-white px-2 py-0.5 rounded uppercase flex items-center gap-1 hover:opacity-90 shadow-sm transition-opacity"
                          style={{
                            backgroundColor: task.priority_details?.category === 'Critical' ? '#dc2626' : task.priority_details?.category === 'High' ? '#ea580c' : task.priority_details?.category === 'Medium' ? '#ca8a04' : '#16a34a'
                          }}
                          title="Click to view explainable scoring factor breakdown"
                        >
                          <Brain className="w-3 h-3" />
                          {task.priority_details?.category || 'Low'} ({task.priority_details?.score || 0})
                        </button>
                      </div>
                      {task.overdue_days > 0 && (
                        <span className="text-[10px] text-red-600 font-medium bg-red-50 px-1.5 py-0.5 rounded">
                          {task.overdue_days} Days Overdue
                        </span>
                      )}
                    </div>
                  </td>

                  <td className="px-4 py-3.5">
                    {filterState === 'Completed' ? (
                       <span className="text-green-700 font-medium text-xs flex items-center gap-1">
                         <CheckCircle2 className="w-3.5 h-3.5 text-green-600" /> Outcome Logged
                       </span>
                    ) : (
                      <>
                        {status === 'Planned' && (
                          <div className="flex flex-col">
                            <span className="text-green-700 font-semibold flex items-center gap-1.5 text-sm">
                              <span className="w-2 h-2 rounded-full bg-green-500 inline-block shadow-sm"></span>
                              Scheduled
                            </span>
                            <div className="text-[11px] text-gray-500 mt-0.5">
                              {isConsolidated ? 'Consolidated Block' : 'Standalone Block'}
                            </div>
                          </div>
                        )}
                        {status === 'Deferred' && (
                          <div className="flex flex-col items-start">
                            <span className="text-amber-600 font-semibold flex items-center gap-1.5 text-sm">
                              <span className="w-2 h-2 rounded-full bg-amber-500 inline-block shadow-sm"></span>
                              Deferred
                            </span>
                            <span 
                              className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200/70 rounded px-1.5 py-0.5 mt-1 max-w-[190px] truncate cursor-help"
                              title={task.rejection_reason || task.description || "Deferred by CP-SAT to avoid capacity bottleneck."}
                            >
                              {task.rejection_reason || task.description || "Deferred by CP-SAT"}
                            </span>
                          </div>
                        )}
                        {status === 'Infeasible' && (
                          <div className="flex flex-col items-start">
                            <span className="text-red-600 font-semibold flex items-center gap-1.5 text-sm">
                              <span className="w-2 h-2 rounded-full bg-red-500 inline-block shadow-sm"></span>
                              Cannot Schedule
                            </span>
                            <span 
                              className="text-[10px] text-red-700 bg-red-50 border border-red-200/70 rounded px-1.5 py-0.5 mt-1 max-w-[210px] cursor-help font-medium"
                              title={task.rejection_reason || task.description || "Train headways leave no clear maintenance gap before deadline."}
                            >
                              {(task.rejection_reason || task.description) 
                                ? (task.rejection_reason || task.description).substring(0, 36) + '...' 
                                : "Tight train headway conflict"}
                            </span>
                          </div>
                        )}
                        {status === 'Pending' && (
                          <span className="text-gray-500 font-medium flex items-center gap-1.5 text-sm">
                            <span className="w-2 h-2 rounded-full bg-gray-300 inline-block"></span>
                            Awaiting Solver
                          </span>
                        )}
                      </>
                    )}
                  </td>

                  <td className="px-4 py-3.5 text-right">
                    <div className="flex flex-col items-end gap-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] uppercase tracking-wider font-semibold text-gray-500">State:</span>
                        <span className="text-xs font-bold text-rail-blue bg-blue-50 px-2 py-0.5 rounded">
                          {task.lifecycle_status}
                        </span>
                      </div>
                      
                      {filterState === 'Active' && (
                        <div className="flex flex-wrap justify-end gap-1.5 mt-1">
                          <button 
                            onClick={() => setSelectedTaskForOverride(task)}
                            className="text-xs flex items-center gap-1 bg-purple-50 hover:bg-purple-100 text-purple-700 px-2 py-1 rounded font-medium transition-colors"
                            title="Manually override AI priority score with operational justification"
                          >
                            <Sliders className="w-3 h-3" /> Override
                          </button>
                          {task.lifecycle_status !== 'In Progress' && onUpdateStatus && (
                            <button 
                              onClick={() => onUpdateStatus(task.id, 'In Progress')}
                              className="text-xs flex items-center gap-1 bg-amber-50 hover:bg-amber-100 text-amber-700 px-2 py-1 rounded transition-colors"
                              title="Mark as currently in execution"
                            >
                              <PlayCircle className="w-3 h-3" /> Start
                            </button>
                          )}
                          <button 
                            onClick={() => setSelectedTaskForOutcome(task)}
                            className="text-xs flex items-center gap-1 bg-green-50 hover:bg-green-100 text-green-700 px-2 py-1 rounded font-medium transition-colors"
                            title="Log actual execution outcome (Planned vs Actual)"
                          >
                            <FileCheck className="w-3 h-3" /> Log Outcome
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
