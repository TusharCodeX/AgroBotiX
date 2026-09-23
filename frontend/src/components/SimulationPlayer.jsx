import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, RotateCcw, SkipForward, FastForward } from 'lucide-react';

export default function SimulationPlayer({ plan, onPoseUpdate }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [speedMultiplier, setSpeedMultiplier] = useState(1);
  const timerRef = useRef(null);

  const waypoints = plan?.waypoints || [];

  useEffect(() => {
    if (waypoints.length > 0) {
      setCurrentIdx(0);
      const wp = waypoints[0];
      onPoseUpdate({
        x: wp.x,
        y: wp.y,
        heading: wp.heading,
        bladeOn: false,
        bladeDown: false,
      });
    }
  }, [plan]);

  useEffect(() => {
    if (isPlaying) {
      const delay = Math.max(150, 600 / speedMultiplier);
      timerRef.current = setInterval(() => {
        setCurrentIdx((prev) => {
          if (prev >= waypoints.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          const next = prev + 1;
          const wp = waypoints[next];
          const isCutting = wp.action === 'CUT_PASS' || wp.action === 'FORWARD';
          onPoseUpdate({
            x: wp.x,
            y: wp.y,
            heading: wp.heading,
            bladeOn: wp.action === 'CUT_PASS',
            bladeDown: wp.action === 'CUT_PASS',
          });
          return next;
        });
      }, delay);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isPlaying, speedMultiplier, waypoints]);

  if (!waypoints.length) return null;

  const handleReset = () => {
    setIsPlaying(false);
    setCurrentIdx(0);
    const wp = waypoints[0];
    onPoseUpdate({
      x: wp.x,
      y: wp.y,
      heading: wp.heading,
      bladeOn: false,
      bladeDown: false,
    });
  };

  const handleStepForward = () => {
    if (currentIdx < waypoints.length - 1) {
      const next = currentIdx + 1;
      setCurrentIdx(next);
      const wp = waypoints[next];
      onPoseUpdate({
        x: wp.x,
        y: wp.y,
        heading: wp.heading,
        bladeOn: wp.action === 'CUT_PASS',
        bladeDown: wp.action === 'CUT_PASS',
      });
    }
  };

  const currWp = waypoints[currentIdx] || waypoints[0];

  return (
    <div className="card bg-slate-900/90 border border-slate-800 p-3 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-xs text-slate-300">Rover Simulation:</span>
          <span className="text-xs font-mono text-sky-400">
            Waypoint {currentIdx + 1} / {waypoints.length}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <span className="text-[10px] text-slate-400">Speed:</span>
          {[1, 2, 4].map((s) => (
            <button
              key={s}
              onClick={() => setSpeedMultiplier(s)}
              className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold transition ${
                speedMultiplier === s
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Playback Controls */}
      <div className="flex items-center justify-center gap-2 pt-1">
        <button
          onClick={handleReset}
          title="Reset to start pose"
          className="btn btn-secondary p-1.5 rounded-full"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>

        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className={`btn p-2 rounded-full ${
            isPlaying ? 'bg-amber-600 text-white' : 'btn-primary'
          }`}
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
        </button>

        <button
          onClick={handleStepForward}
          disabled={currentIdx >= waypoints.length - 1}
          title="Step to next waypoint"
          className="btn btn-secondary p-1.5 rounded-full disabled:opacity-40"
        >
          <SkipForward className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Rover Live Odometry HUD */}
      <div className="grid grid-cols-4 gap-1 text-[11px] font-mono bg-slate-950/80 p-1.5 rounded border border-slate-800/80 text-center">
        <div>
          <span className="text-slate-500 block text-[9px]">X (cm)</span>
          <span className="font-bold text-slate-200">{currWp.x.toFixed(1)}</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[9px]">Y (cm)</span>
          <span className="font-bold text-slate-200">{currWp.y.toFixed(1)}</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[9px]">HEADING</span>
          <span className="font-bold text-slate-200">{currWp.heading}°</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[9px]">BLADES</span>
          <span className={`font-bold ${currWp.action === 'CUT_PASS' ? 'text-red-400 animate-pulse' : 'text-slate-400'}`}>
            {currWp.action === 'CUT_PASS' ? 'CUTTING' : 'UP/OFF'}
          </span>
        </div>
      </div>
    </div>
  );
}
