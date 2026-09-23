import React from 'react';
import { 
  Bot, 
  Settings, 
  BarChart2, 
  Sun, 
  Moon, 
  Compass, 
  AlertTriangle, 
  CheckCircle2 
} from 'lucide-react';

export default function Navbar({ 
  health, 
  currentTab, 
  setCurrentTab, 
  theme, 
  toggleTheme, 
  onOpenSettings, 
  onOpenCalibration 
}) {
  const isDemo = health?.demo_mode;
  const isCalibrated = health?.calibration?.status === 'calibrated';

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40 px-4 py-3">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
        {/* Logo & App Title */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-tr from-emerald-600 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-emerald-500/20">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-xl tracking-tight text-white">AgriPath</h1>
              <span className="text-xs px-2 py-0.5 rounded font-mono font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                6-Wheel Rover
              </span>
            </div>
            <p className="text-xs text-slate-400">Autonomous Weed Targeting & Dual-Blade Path Planner</p>
          </div>
        </div>

        {/* Status Indicators & Demo Banner */}
        <div className="flex items-center gap-3">
          {health?.detector_model ? (
            <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${
              isDemo 
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' 
                : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
            }`}>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>{health.detector_model}</span>
            </div>
          ) : (
            <div 
              onClick={onOpenSettings} 
              title="Click to connect a custom backend URL in Settings"
              className="flex items-center gap-1.5 bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 px-3 py-1 rounded-full text-xs font-semibold cursor-pointer hover:bg-indigo-500/30 transition"
            >
              <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping" />
              <span>Vercel Cloud Demo</span>
            </div>
          )}

          <button
            onClick={onOpenCalibration}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border transition ${
              isCalibrated 
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/30 hover:bg-rose-500/20 animate-bounce'
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>{isCalibrated ? `Scale: ${health?.calibration?.cm_per_pixel} cm/px` : 'Uncalibrated'}</span>
          </button>
        </div>

        {/* Navigation & Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentTab('perception')}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition ${
              currentTab === 'perception'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            Mission Field
          </button>

          <button
            onClick={() => setCurrentTab('evaluation')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition ${
              currentTab === 'evaluation'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            <BarChart2 className="w-4 h-4" />
            Evaluation
          </button>

          <button
            onClick={onOpenSettings}
            title="Rover & Vision Settings"
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition"
          >
            <Settings className="w-5 h-5" />
          </button>

          <button
            onClick={toggleTheme}
            title="Toggle Theme"
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition"
          >
            {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </header>
  );
}
