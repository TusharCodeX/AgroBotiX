import React, { useState } from 'react';
import { X, Save, Sliders, Shield, Zap, Wrench } from 'lucide-react';

export default function SettingsModal({ isOpen, onClose, config, onSaveConfig }) {
  const [cfg, setCfg] = useState(config || {});

  if (!isOpen) return null;

  const handleNestedChange = (section, key, val) => {
    setCfg((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: val,
      },
    }));
  };

  const handleSave = () => {
    onSaveConfig(cfg);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="card w-full max-w-xl max-h-[90vh] overflow-y-auto bg-slate-900 border border-slate-700 shadow-2xl flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-blue-400" />
            <h3 className="font-semibold text-slate-100 text-base">AgroBotix Rover & Planner Settings</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Section 0: Backend Server Endpoint (Vercel / Cloud / Local) */}
        <div className="space-y-3 text-xs">
          <div className="flex items-center gap-2 font-semibold text-slate-200 border-b border-slate-800 pb-1">
            <Wrench className="w-4 h-4 text-blue-400" />
            <span>Backend Server Endpoint (Local or Deployed)</span>
          </div>

          <div>
            <label className="text-slate-400 block mb-1">FastAPI Backend URL:</label>
            <input
              type="text"
              placeholder="e.g. https://agripath-backend.onrender.com or leave blank for local"
              value={cfg?.backend_url ?? (localStorage.getItem('agripath_backend_url') || '')}
              onChange={(e) => {
                const val = e.target.value.trim();
                handleNestedChange('server', 'backend_url', val);
                localStorage.setItem('agripath_backend_url', val);
              }}
              className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-white font-mono text-xs"
            />
            <span className="text-[10px] text-slate-500 block mt-1">
              Leave blank when running locally (`/api`). For Vercel, set your deployed Render/Railway/ngrok URL.
            </span>
          </div>
        </div>

        {/* Section 1: Robot Chassis Dimensions & Speed */}
        <div className="space-y-3 text-xs">
          <div className="flex items-center gap-2 font-semibold text-slate-200 border-b border-slate-800 pb-1">
            <Shield className="w-4 h-4 text-emerald-400" />
            <span>Robot Physical Parameters</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-slate-400 block mb-1">Chassis Length (cm):</label>
              <input
                type="number"
                value={cfg?.robot?.length_cm || 30.0}
                onChange={(e) => handleNestedChange('robot', 'length_cm', parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-white font-mono"
              />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Chassis Width (cm):</label>
              <input
                type="number"
                value={cfg?.robot?.width_cm || 25.0}
                onChange={(e) => handleNestedChange('robot', 'width_cm', parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-white font-mono"
              />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Crop Safety Margin (cm):</label>
              <input
                type="number"
                value={cfg?.robot?.safety_margin_cm || 4.0}
                onChange={(e) => handleNestedChange('robot', 'safety_margin_cm', parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-white font-mono"
              />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Linear Speed (cm/s):</label>
              <input
                type="number"
                value={cfg?.robot?.speed_cm_s || 15.0}
                onChange={(e) => handleNestedChange('robot', 'speed_cm_s', parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-white font-mono"
              />
            </div>
          </div>
        </div>

        {/* Section 2: Dual Front Cutting Blades */}
        <div className="space-y-3 text-xs">
          <div className="flex items-center gap-2 font-semibold text-slate-200 border-b border-slate-800 pb-1">
            <Wrench className="w-4 h-4 text-amber-400" />
            <span>Dual Front Cutting Blades</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-slate-400 block mb-1">Offset Forward from Center (cm):</label>
              <input
                type="number"
                value={cfg?.blade?.offset_forward_cm || 18.0}
                onChange={(e) => handleNestedChange('blade', 'offset_forward_cm', parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-white font-mono"
              />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Combined Cutting Width (cm):</label>
              <input
                type="number"
                value={cfg?.blade?.total_width_cm || 16.0}
                onChange={(e) => handleNestedChange('blade', 'total_width_cm', parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-white font-mono"
              />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Forward Cutting Pass (cm):</label>
              <input
                type="number"
                value={cfg?.blade?.pass_cm || 8.0}
                onChange={(e) => handleNestedChange('blade', 'pass_cm', parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-white font-mono"
              />
            </div>
            <div className="flex items-center gap-4 pt-4">
              <label className="flex items-center gap-2 cursor-pointer text-slate-300">
                <input
                  type="checkbox"
                  checked={cfg?.blade?.dry_run ?? true}
                  onChange={(e) => handleNestedChange('blade', 'dry_run', e.target.checked)}
                  className="rounded border-slate-700"
                />
                <span>Dry Run Mode</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-slate-300">
                <input
                  type="checkbox"
                  checked={cfg?.blade?.enabled ?? false}
                  onChange={(e) => handleNestedChange('blade', 'enabled', e.target.checked)}
                  className="rounded border-slate-700"
                />
                <span>Blade Motor Enabled</span>
              </label>
            </div>
          </div>
        </div>

        {/* Section 3: Skid-Steer Planner & Turn Slip Penalty */}
        <div className="space-y-3 text-xs">
          <div className="flex items-center gap-2 font-semibold text-slate-200 border-b border-slate-800 pb-1">
            <Zap className="w-4 h-4 text-sky-400" />
            <span>Skid-Steer Planner Parameters</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-slate-400 block mb-1">Turn Penalty (equivalent cm):</label>
              <input
                type="number"
                value={cfg?.planner?.turn_penalty_cm || 35.0}
                onChange={(e) => handleNestedChange('planner', 'turn_penalty_cm', parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-white font-mono"
              />
              <span className="text-[10px] text-slate-500">Pivoting on soil slips wheels; higher = straighter routes</span>
            </div>
            <div className="pt-4">
              <label className="flex items-center gap-2 cursor-pointer text-slate-300">
                <input
                  type="checkbox"
                  checked={cfg?.planner?.return_to_start ?? false}
                  onChange={(e) => handleNestedChange('planner', 'return_to_start', e.target.checked)}
                  className="rounded border-slate-700"
                />
                <span>Return to Start Pose (0, 0, 0)</span>
              </label>
            </div>
          </div>
        </div>

        {/* Save Actions */}
        <div className="flex justify-end gap-2 border-t border-slate-800 pt-3">
          <button onClick={onClose} className="btn btn-secondary text-xs">
            Cancel
          </button>
          <button onClick={handleSave} className="btn btn-primary text-xs">
            <Save className="w-4 h-4" /> Save Configuration
          </button>
        </div>
      </div>
    </div>
  );
}
