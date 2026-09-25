import React from 'react';
import { 
  Bot, 
  Settings, 
  Sun, 
  Moon, 
  Compass, 
  AlertTriangle, 
  CheckCircle2,
  Sprout,
  XCircle
} from 'lucide-react';

export default function Navbar({ 
  health, 
  theme, 
  toggleTheme, 
  onOpenSettings, 
  onOpenCalibration,
  selectedCropContext,
  onCropContextChange,
  availableCrops
}) {
  const isModelAvailable = health?.model_available ?? true;
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
              <h1 className="font-bold text-xl tracking-tight text-white">AgroBotix</h1>
              <span className="text-xs px-2 py-0.5 rounded font-mono font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                Indian Field Vision
              </span>
            </div>
            <p className="text-xs text-slate-400">Autonomous Weed Targeting & Dual-Blade Skid-Steer Planner</p>
          </div>
        </div>

        {/* Indian Crop Context Selector */}
        <div className="flex items-center gap-2 bg-slate-800/90 border border-slate-700/80 rounded-lg px-3 py-1.5 shadow-inner">
          <Sprout className="w-4 h-4 text-emerald-400 shrink-0" />
          <span className="text-[11px] text-slate-400 font-medium">Crop Context:</span>
          <select
            value={selectedCropContext || 'wheat'}
            onChange={(e) => onCropContextChange(e.target.value)}
            className="bg-transparent border-none text-emerald-300 font-semibold text-xs focus:outline-none cursor-pointer pr-1"
          >
            <option value="wheat" className="bg-slate-900 text-white">🌾 Wheat</option>
            <option value="rice" className="bg-slate-900 text-white">🌾 Rice / Paddy</option>
            <option value="mustard" className="bg-slate-900 text-white">🌼 Mustard</option>
            <option value="maize" className="bg-slate-900 text-white">🌽 Maize</option>
            <option value="sugarcane" className="bg-slate-900 text-white">🎋 Sugarcane</option>
            <option value="vegetables" className="bg-slate-900 text-white">🍅 Vegetables</option>
            <option value="sorghum_millets" className="bg-slate-900 text-white">🌾 Sorghum & Millets</option>
            <option value="pulses_oilseeds" className="bg-slate-900 text-white">🫘 Pulses & Oilseeds</option>
            <option value="cotton" className="bg-slate-900 text-white">🌿 Cotton</option>
            <option value="orchard" className="bg-slate-900 text-white">🍎 Fruit Orchards</option>
          </select>
        </div>

        {/* Status Indicators */}
        <div className="flex items-center gap-3">
          {health?.detector_model && health.detector_model !== 'MODEL UNAVAILABLE' ? (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border bg-emerald-500/20 text-emerald-300 border-emerald-500/40">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>{health.detector_model}</span>
            </div>
          ) : (
            <div 
              onClick={onOpenSettings} 
              title="Model unavailable. Click to connect backend or check models/best.onnx"
              className="flex items-center gap-1.5 bg-rose-500/20 text-rose-300 border border-rose-500/40 px-3 py-1 rounded-full text-xs font-semibold cursor-pointer hover:bg-rose-500/30 transition animate-pulse"
            >
              <XCircle className="w-3.5 h-3.5 text-rose-400" />
              <span>MODEL UNAVAILABLE</span>
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
