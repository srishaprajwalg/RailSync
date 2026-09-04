import React, { useMemo } from 'react';
import { formatTime } from '../utils/formatters';
import { Info } from 'lucide-react';

export default function SimpleGanttView({ corridor, timetables, forecasts, blocks, timeWindow }) {
  const [selectedDirection, setSelectedDirection] = React.useState('Up');

  const filteredSchedules = useMemo(() => timetables.filter(t => t.direction === selectedDirection), [timetables, selectedDirection]);
  const filteredBlocks = useMemo(() => blocks.filter(b => b.line_direction === selectedDirection), [blocks, selectedDirection]);

  // Derive the actual planning start date (Day 0 at midnight) dynamically
  const baseDate = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  const formatDateTime = (mins) => {
    const d = new Date(baseDate.getTime() + mins * 60000);
    return d.toLocaleString('en-US', { 
      month: 'short', day: 'numeric', 
      hour: '2-digit', minute: '2-digit', hour12: false 
    }).replace(',', '');
  };

  const windowDuration = timeWindow.end - timeWindow.start;

  // Calculate dynamic ticks and interval based on window duration
  const { ticks, tickInterval } = useMemo(() => {
    let interval = 240; // 4 hours for Day view
    if (windowDuration >= 20 * 1440) {
      interval = 7 * 1440; // Weekly for Month view
    } else if (windowDuration > 1440) {
      interval = 1440; // Daily for Week view
    }

    const newTicks = [];
    const firstTick = Math.ceil(timeWindow.start / interval) * interval;
    
    for (let t = firstTick; t <= timeWindow.end; t += interval) {
      const pct = ((t - timeWindow.start) / windowDuration) * 100;
      if (pct >= 0 && pct <= 100) {
        newTicks.push({ mins: t, pct });
      }
    }
    return { ticks: newTicks, tickInterval: interval };
  }, [timeWindow, windowDuration]);

  const formatTick = (mins, interval) => {
    const d = new Date(baseDate.getTime() + mins * 60000);
    if (interval < 1440) {
      return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
    } else {
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  };

  // For the Gantt, let's sort items by their start time
  const allEvents = useMemo(() => {
    const events = [];
    filteredSchedules.forEach(t => {
      const startMins = t.stops[0].arrival_mins;
      const endMins = t.stops[t.stops.length - 1].departure_mins;
      events.push({
        id: t.train_id,
        type: 'train',
        label: `${t.type} Train`,
        startMins,
        endMins,
        duration: endMins - startMins,
      });
    });
    filteredBlocks.forEach(b => {
      events.push({
        id: b.id,
        type: 'block',
        label: `Maintenance Block (${(b.end_km - b.start_km).toFixed(1)} km)`,
        startMins: b.start_time_mins,
        endMins: b.end_time_mins,
        duration: b.end_time_mins - b.start_time_mins,
      });
    });
    
    return events.sort((a, b) => a.startMins - b.startMins);
  }, [filteredSchedules, filteredBlocks]);

  // Pack events into lanes (rows) to prevent massive vertical scrolling
  const unifiedLanes = useMemo(() => {
    const lanes = [];
    allEvents.forEach(item => {
      let placed = false;
      for (let i = 0; i < lanes.length; i++) {
        const lastItem = lanes[i][lanes[i].length - 1];
        // add a small 5 min visual buffer between items in the same lane
        if (lastItem.endMins + 5 <= item.startMins) {
          lanes[i].push(item);
          placed = true;
          break;
        }
      }
      if (!placed) lanes.push([item]);
    });
    return lanes;
  }, [allEvents]);
  
  // Helper to render a lane
  const renderLane = (lane, index) => (
    <div key={`unified-lane-${index}`} className="flex items-center hover:bg-gray-50 group border-b border-gray-100/50 min-h-[36px]">
      <div className="w-32 shrink-0 text-xs font-medium text-gray-500 truncate pr-2 border-r border-gray-100 flex items-center h-full">
        {`Lane ${index + 1}`}
      </div>
      <div className="flex-1 relative h-full">
        {lane.map(evt => {
          const startPct = Math.max(0, ((evt.startMins - timeWindow.start) / windowDuration) * 100);
          const endPct = Math.min(100, ((evt.endMins - timeWindow.start) / windowDuration) * 100);
          const widthPct = endPct - startPct;
          const isBlock = evt.type === 'block';
          
          if (widthPct <= 0) return null;
          
          return (
            <div 
              key={evt.id}
              className={`absolute top-1 bottom-1 rounded shadow-sm flex items-center justify-center overflow-hidden transition-all group/item cursor-pointer ${
                isBlock ? 'bg-orange-500/90 border border-orange-600 hover:bg-orange-500 text-white z-10' : 'bg-slate-700/80 border border-slate-700 hover:bg-slate-800 text-white z-0'
              }`}
              style={{ left: `${startPct}%`, width: `${widthPct}%` }}
              title={`${evt.label} (${formatDateTime(evt.startMins)} - ${formatDateTime(evt.endMins)})`}
            >
              {widthPct > 3 && (
                <span className="text-[10px] font-medium px-1 truncate opacity-90 group-hover/item:opacity-100">
                  {evt.label.replace('Train', '').replace('Maintenance Block', 'Block')}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );

  return (
    <div className="bg-white border border-rail-border rounded-lg shadow-sm">
      <div className="p-4 border-b border-gray-100 bg-gray-50 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h3 className="text-lg font-bold text-gray-800">Simple View (Gantt)</h3>
          <p className="text-xs text-gray-500 max-w-md mt-1">
            Simplified visualization of train operations and scheduled maintenance.
          </p>
        </div>
        <div className="flex bg-gray-200 rounded p-1 shrink-0">
          <button 
            className={`px-3 py-1.5 text-xs font-semibold rounded transition-colors ${selectedDirection === 'Up' ? 'bg-white shadow text-indigo-700' : 'text-gray-600 hover:text-gray-800'}`}
            onClick={() => setSelectedDirection('Up')}
          >
            Up Line
          </button>
          <button 
            className={`px-3 py-1.5 text-xs font-semibold rounded transition-colors ${selectedDirection === 'Down' ? 'bg-white shadow text-fuchsia-700' : 'text-gray-600 hover:text-gray-800'}`}
            onClick={() => setSelectedDirection('Down')}
          >
            Down Line
          </button>
        </div>
      </div>
      
      <div className="px-5 py-3 border-b border-gray-100 flex items-start gap-2 bg-blue-50/30">
        <Info className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
        <p className="text-[10px] text-gray-600">
          <strong>How to read this chart:</strong> Shows the exact overlapping timeline of trains and maintenance. Blocks are scheduled between train movements.
        </p>
      </div>

      <div className="p-4 overflow-x-auto relative">
        {allEvents.length === 0 ? (
          <div className="text-center text-gray-500 py-10">No activities in this time window.</div>
        ) : (
          <div className="relative w-full min-w-[800px] border border-gray-200 rounded-md bg-white">
            {/* Grid lines background */}
            <div className="absolute top-10 bottom-0 left-32 right-0 pointer-events-none z-0">
               {ticks.map(tick => (
                  <div key={`grid-${tick.mins}`} className="absolute top-0 bottom-0 border-l border-gray-200" style={{ left: `${tick.pct}%` }} />
               ))}
            </div>
            
            {/* Timeline header */}
            <div className="flex border-b border-gray-200 bg-gray-50 sticky top-0 z-20 h-10">
              <div className="w-32 shrink-0 border-r border-gray-200 flex items-center px-3 font-semibold text-xs text-gray-600 uppercase tracking-wider">
                Lane
              </div>
              <div className="flex-1 relative flex items-center">
                {ticks.map(tick => (
                  <div key={`tick-${tick.mins}`} className="absolute top-0 bottom-0 border-l border-gray-300 flex items-end pb-1" style={{ left: `${tick.pct}%` }}>
                    <span className="text-[10px] font-medium text-gray-500 -translate-x-1/2 px-1 bg-gray-50 whitespace-nowrap">
                      {formatTick(tick.mins, tickInterval)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Lanes content */}
            <div className="relative z-10 flex flex-col">
              {unifiedLanes.map((lane, i) => renderLane(lane, i))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
