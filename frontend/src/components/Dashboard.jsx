import { useState, useEffect } from 'react';
import { fetchCorridor, fetchTimetables, fetchTasks, fetchGoodsForecasts, optimizeBlocks, updateTaskStatus } from '../services/api';
import KPICards from './KPICards';
import BlockPlan from './BlockPlan';
import CorridorTimeline from './CorridorTimeline';
import TaskTable from './TaskTable';
import TaskForm from './TaskForm';
import AnalyticsDashboard from './AnalyticsDashboard';
import { Train, Activity, AlertTriangle, Settings, Sliders, LayoutList, TrendingUp } from 'lucide-react';

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [horizon, setHorizon] = useState(7);
  const [data, setData] = useState({
    corridor: [],
    timetables: [],
    forecasts: [],
    tasks: [],
    blocks: [],
    metrics: null,
    task_statuses: {},
  });
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('analytics'); // setup, control, action, analytics

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const [corridor, timetables, forecasts, tasks] = await Promise.all([
        fetchCorridor(),
        fetchTimetables(),
        fetchGoodsForecasts(),
        fetchTasks(),
      ]);
      setData(prev => ({ ...prev, corridor, timetables, forecasts, tasks }));
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handleOptimize = async () => {
    try {
      setOptimizing(true);
      const result = await optimizeBlocks(horizon);
      setData(prev => ({
        ...prev,
        blocks: result.blocks,
        metrics: result.metrics,
        task_statuses: result.task_statuses || {},
      }));
      setOptimizing(false);
    } catch (err) {
      setError(err.message);
      setOptimizing(false);
    }
  };
  
  const handleStatusUpdate = async (taskId, newStatus) => {
    try {
      const updatedTasks = await updateTaskStatus(taskId, newStatus);
      setData(prev => ({ ...prev, tasks: updatedTasks }));
    } catch (err) {
      setError("Failed to update status: " + err.message);
    }
  };

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-rail-blue">Loading simulator data...</div>;
  }

  return (
    <div className="min-h-screen bg-rail-bg">
      {/* Header */}
      <header className="bg-rail-blue text-white py-4 px-6 shadow-md">
        <div className="flex justify-between items-center max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <Train className="w-8 h-8 text-rail-saffron" />
            <div>
              <h1 className="text-xl font-bold tracking-tight">RailVyuha</h1>
              <p className="text-xs text-rail-border opacity-80">Automatic Block Planning System</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-semibold">Bengaluru City (SBC) → Jolarpettai (JTJ)</div>
            <div className="text-xs text-rail-saffron bg-white/10 px-2 py-0.5 rounded inline-block mt-1">Prototype Simulation</div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 px-6 space-y-6">
        {error && (
          <div className="bg-rail-error/10 border-l-4 border-rail-error text-rail-error p-4 flex gap-2">
            <AlertTriangle className="w-5 h-5" />
            {error}
          </div>
        )}

        {/* Prototype Disclaimer */}
        <div className="text-xs text-rail-text-muted bg-white px-4 py-2 border border-rail-border rounded-md shadow-sm">
          <strong>Note:</strong> Station and timetable data are derived from public Indian Railways data (approximate chainage). Maintenance tasks and goods-train forecasts are synthetic — no public source exists for either.
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-rail-border mb-6 overflow-x-auto">
          <button
            onClick={() => setActiveTab('analytics')}
            className={`px-6 py-3 font-medium text-sm flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
              activeTab === 'analytics'
                ? 'border-rail-blue text-rail-blue'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            Decision Intelligence
          </button>
          <button
            onClick={() => setActiveTab('setup')}
            className={`px-6 py-3 font-medium text-sm flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
              activeTab === 'setup'
                ? 'border-rail-blue text-rail-blue'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Settings className="w-4 h-4" />
            Data & Setup
          </button>
          <button
            onClick={() => setActiveTab('control')}
            className={`px-6 py-3 font-medium text-sm flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
              activeTab === 'control'
                ? 'border-rail-blue text-rail-blue'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Sliders className="w-4 h-4" />
            Control Room
          </button>
          <button
            onClick={() => setActiveTab('action')}
            className={`px-6 py-3 font-medium text-sm flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
              activeTab === 'action'
                ? 'border-rail-blue text-rail-blue'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <LayoutList className="w-4 h-4" />
            Action Plan
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'analytics' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-rail-text-dark mb-1">Decision Intelligence</h2>
              <p className="text-rail-text-muted text-sm mb-4">Analyze workload distribution, lifecycle progress, and optimization impact.</p>
            </div>
            <AnalyticsDashboard 
              tasks={data.tasks} 
              blocks={data.blocks} 
              taskStatuses={data.task_statuses} 
              metrics={data.metrics}
              corridor={data.corridor}
            />
          </div>
        )}

        {activeTab === 'setup' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-rail-text-dark mb-1">Data & Setup</h2>
              <p className="text-rail-text-muted text-sm mb-4">Manage maintenance requests and view key performance indicators.</p>
            </div>
            {data.metrics && <KPICards metrics={data.metrics} />}
            <TaskForm onTaskAdded={(updatedTasks) => setData((prev) => ({ ...prev, tasks: updatedTasks }))} />
            <div className="mt-8">
              <TaskTable tasks={data.tasks} blocks={data.blocks} taskStatuses={data.task_statuses} onUpdateStatus={handleStatusUpdate} />
            </div>
          </div>
        )}

        {activeTab === 'control' && (
          <div className="space-y-6">
            <div className="flex justify-between items-end mb-4">
              <div>
                <h2 className="text-2xl font-bold text-rail-text-dark">Control Room</h2>
                <p className="text-rail-text-muted text-sm">Coordinate multi-department requests with CP-SAT constraints.</p>
              </div>
              <div className="flex items-center gap-4">
                <select
                  value={horizon}
                  onChange={(e) => setHorizon(Number(e.target.value))}
                  disabled={optimizing}
                  className="px-4 py-2.5 border border-rail-border rounded shadow-sm text-sm focus:outline-none focus:ring-2 focus:ring-rail-blue/50"
                >
                  <option value={1}>Daily (1 Day)</option>
                  <option value={7}>Weekly (7 Days)</option>
                  <option value={30}>Monthly (30 Days)</option>
                </select>
                <button 
                  onClick={handleOptimize}
                  disabled={optimizing}
                  className={`px-6 py-2.5 rounded shadow-sm text-white font-medium flex items-center gap-2 transition-colors ${
                    optimizing ? 'bg-rail-blue/70 cursor-not-allowed' : 'bg-rail-blue hover:bg-rail-blue/90'
                  }`}
                >
                  <Activity className="w-4 h-4" />
                  {optimizing ? 'Running CP-SAT Solver...' : 'Generate Optimal Plan'}
                </button>
              </div>
            </div>
            {data.blocks.length > 0 ? (
              <CorridorTimeline corridor={data.corridor} timetables={data.timetables} forecasts={data.forecasts} blocks={data.blocks} horizonDays={horizon} />
            ) : (
              <div className="bg-white p-10 rounded-lg shadow-sm border border-rail-border text-center text-gray-500">
                Run the CP-SAT solver to view the corridor timeline.
              </div>
            )}
          </div>
        )}

        {activeTab === 'action' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-rail-text-dark mb-1">Action Plan</h2>
              <p className="text-rail-text-muted text-sm mb-4">Detailed view of the generated blocks and task assignments.</p>
            </div>
            {data.blocks.length > 0 ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                  <BlockPlan blocks={data.blocks} tasks={data.tasks} />
                </div>
                <div>
                  <TaskTable tasks={data.tasks} blocks={data.blocks} taskStatuses={data.task_statuses} onUpdateStatus={handleStatusUpdate} />
                </div>
              </div>
            ) : (
              <div className="bg-white p-10 rounded-lg shadow-sm border border-rail-border text-center text-gray-500">
                Run the CP-SAT solver in the Control Room to generate an action plan.
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
