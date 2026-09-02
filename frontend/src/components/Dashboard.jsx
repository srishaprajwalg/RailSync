import { useState, useEffect, useMemo } from 'react';
import { fetchCorridor, fetchTimetables, fetchTasks, fetchGoodsForecasts, optimizeBlocks, updateTaskStatus } from '../services/api';
import KPICards from './KPICards';
import BlockPlan from './BlockPlan';
import CorridorTimeline from './CorridorTimeline';
import TaskTable from './TaskTable';
import TaskForm from './TaskForm';
import AnalyticsDashboard from './AnalyticsDashboard';
import SimpleGanttView from './SimpleGanttView';
import { Train, Activity, AlertTriangle, Settings, Sliders, LayoutList, TrendingUp, CalendarDays, BarChart2 } from 'lucide-react';

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [viewMode, setViewMode] = useState('Month'); // Month, Week, Day
  const [selectedWeek, setSelectedWeek] = useState(1);
  const [selectedDay, setSelectedDay] = useState(1);
  const [viewType, setViewType] = useState('technical'); // technical, simple
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
      const result = await optimizeBlocks(30); // Hardcoded to 30 days backend optimization
      setData(prev => ({
        ...prev,
        blocks: result.blocks,
        metrics: result.metrics, // baseline from backend
        task_statuses: result.task_statuses || {},
      }));
      setOptimizing(false);
    } catch (err) {
      setError(err.message);
      setOptimizing(false);
    }
  };

  // Compute time window
  const getWindowMins = () => {
    if (viewMode === 'Month') return { start: 0, end: 30 * 1440 };
    if (viewMode === 'Week') return { start: (selectedWeek - 1) * 7 * 1440, end: selectedWeek * 7 * 1440 };
    if (viewMode === 'Day') return { start: (selectedDay - 1) * 1440, end: selectedDay * 1440 };
    return { start: 0, end: 30 * 1440 };
  };
  const timeWindow = getWindowMins();

  // Filter items
  const filterByTimeWindow = (items, type) => {
    if (!items) return [];
    return items.filter(item => {
      let itemStart, itemEnd;
      if (type === 'block') {
         itemStart = item.start_time_mins;
         itemEnd = item.end_time_mins;
      } else if (type === 'timetable') {
         if (!item.stops || item.stops.length === 0) return false;
         itemStart = item.stops[0].arrival_mins;
         itemEnd = item.stops[item.stops.length - 1].departure_mins;
      } else if (type === 'forecast') {
         itemStart = item.earliest_entry_mins;
         itemEnd = item.latest_exit_mins;
      }
      return itemStart < timeWindow.end && itemEnd > timeWindow.start;
    });
  };

  const filteredBlocks = filterByTimeWindow(data.blocks, 'block');
  const filteredTimetables = filterByTimeWindow(data.timetables, 'timetable');
  const filteredForecasts = filterByTimeWindow(data.forecasts, 'forecast');

  // Dynamically calculate metrics based on filtered blocks
  const dynamicMetrics = useMemo(() => {
    if (!data.metrics) return null;
    const blocks_created = filteredBlocks.length;
    let total_block_minutes = 0;
    const windowTasks = new Set();
    
    filteredBlocks.forEach(b => {
      total_block_minutes += (b.end_time_mins - b.start_time_mins);
      b.assigned_tasks.forEach(t => windowTasks.add(t));
    });
    
    const planned_tasks = windowTasks.size;
    let total_requested_mins = 0;
    
    windowTasks.forEach(tId => {
      const t = data.tasks.find(tsk => tsk.id === tId);
      if (t) total_requested_mins += t.duration_mins;
    });
    
    let downtime_reduction_pct = 0;
    if (total_requested_mins > 0) {
      downtime_reduction_pct = ((total_requested_mins - total_block_minutes) / total_requested_mins) * 100;
    }
    
    return {
      ...data.metrics,
      planned_tasks,
      blocks_created,
      total_block_minutes,
      downtime_reduction_pct,
    };
  }, [filteredBlocks, data.metrics, data.tasks]);
  
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
              blocks={filteredBlocks} 
              taskStatuses={data.task_statuses} 
              metrics={dynamicMetrics}
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
            {dynamicMetrics && <KPICards metrics={dynamicMetrics} />}
            <TaskForm onTaskAdded={(updatedTasks) => setData((prev) => ({ ...prev, tasks: updatedTasks }))} />
            <div className="mt-8">
              <TaskTable tasks={data.tasks} blocks={filteredBlocks} taskStatuses={data.task_statuses} onUpdateStatus={handleStatusUpdate} />
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
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                <div className="flex items-center gap-2 bg-white rounded shadow-sm border border-rail-border p-1">
                  <button onClick={() => setViewMode('Month')} className={`px-3 py-1.5 text-xs font-semibold rounded ${viewMode === 'Month' ? 'bg-rail-blue text-white' : 'text-gray-600 hover:bg-gray-100'}`}>Month</button>
                  <button onClick={() => setViewMode('Week')} className={`px-3 py-1.5 text-xs font-semibold rounded ${viewMode === 'Week' ? 'bg-rail-blue text-white' : 'text-gray-600 hover:bg-gray-100'}`}>Week</button>
                  <button onClick={() => setViewMode('Day')} className={`px-3 py-1.5 text-xs font-semibold rounded ${viewMode === 'Day' ? 'bg-rail-blue text-white' : 'text-gray-600 hover:bg-gray-100'}`}>Day</button>
                </div>

                {viewMode === 'Week' && (
                  <select
                    value={selectedWeek}
                    onChange={(e) => setSelectedWeek(Number(e.target.value))}
                    className="px-3 py-1.5 border border-rail-border rounded shadow-sm text-sm focus:outline-none focus:ring-2 focus:ring-rail-blue/50"
                  >
                    {[1, 2, 3, 4, 5].map(w => <option key={w} value={w}>Week {w}</option>)}
                  </select>
                )}

                {viewMode === 'Day' && (
                  <select
                    value={selectedDay}
                    onChange={(e) => setSelectedDay(Number(e.target.value))}
                    className="px-3 py-1.5 border border-rail-border rounded shadow-sm text-sm focus:outline-none focus:ring-2 focus:ring-rail-blue/50"
                  >
                    {Array.from({ length: 30 }, (_, i) => i + 1).map(d => <option key={d} value={d}>Day {d}</option>)}
                  </select>
                )}

                <button 
                  onClick={handleOptimize}
                  disabled={optimizing}
                  className={`px-6 py-2 rounded shadow-sm text-white font-medium flex items-center gap-2 transition-colors ${
                    optimizing ? 'bg-rail-blue/70 cursor-not-allowed' : 'bg-rail-blue hover:bg-rail-blue/90'
                  }`}
                >
                  <Activity className="w-4 h-4" />
                  {optimizing ? 'Running CP-SAT Solver...' : 'Generate 30-Day Optimal Plan'}
                </button>
              </div>
            </div>

            {/* View Type Toggle */}
            {data.blocks.length > 0 && (
              <div className="flex justify-end mb-4">
                <div className="flex bg-gray-200 rounded p-1">
                  <button 
                    className={`flex items-center gap-2 px-4 py-1.5 text-xs font-semibold rounded transition-colors ${viewType === 'simple' ? 'bg-white shadow text-gray-800' : 'text-gray-500 hover:text-gray-700'}`}
                    onClick={() => setViewType('simple')}
                  >
                    <CalendarDays className="w-4 h-4" /> Simple View
                  </button>
                  <button 
                    className={`flex items-center gap-2 px-4 py-1.5 text-xs font-semibold rounded transition-colors ${viewType === 'technical' ? 'bg-white shadow text-gray-800' : 'text-gray-500 hover:text-gray-700'}`}
                    onClick={() => setViewType('technical')}
                  >
                    <BarChart2 className="w-4 h-4" /> Technical View
                  </button>
                </div>
              </div>
            )}

            {data.blocks.length > 0 ? (
              viewType === 'technical' ? (
                <CorridorTimeline corridor={data.corridor} timetables={filteredTimetables} forecasts={filteredForecasts} blocks={filteredBlocks} timeWindow={timeWindow} />
              ) : (
                <SimpleGanttView corridor={data.corridor} timetables={filteredTimetables} forecasts={filteredForecasts} blocks={filteredBlocks} timeWindow={timeWindow} />
              )
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
              <div className="w-full">
                <BlockPlan blocks={filteredBlocks} tasks={data.tasks} timeWindow={timeWindow} />
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
