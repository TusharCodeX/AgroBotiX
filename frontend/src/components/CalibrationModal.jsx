import React, { useState } from 'react';
import { X, Check, Compass, Crosshair, QrCode } from 'lucide-react';

export default function CalibrationModal({
  isOpen,
  onClose,
  currentScale,
  onSaveManual,
  onStartTwoPoint,
}) {
  const [mode, setMode] = useState('manual');
  const [scaleVal, setScaleVal] = useState(currentScale || 0.15);
  const [twoPointDistance, setTwoPointDistance] = useState(20.0);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="card w-full max-w-md bg-slate-900 border border-slate-700 shadow-2xl flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5 text-blue-400" />
            <h3 className="font-semibold text-slate-100 text-base">Camera Ground Calibration</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode Selector */}
        <div className="grid grid-cols-3 gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-medium">
          <button
            onClick={() => setMode('manual')}
            className={`py-1.5 rounded transition ${
              mode === 'manual' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Manual Scale
          </button>
          <button
            onClick={() => setMode('two_point')}
            className={`py-1.5 rounded transition ${
              mode === 'two_point' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            2-Point Click
          </button>
          <button
            onClick={() => setMode('aruco')}
            className={`py-1.5 rounded transition ${
              mode === 'aruco' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            ArUco Marker
          </button>
        </div>

        {/* Option 1: Manual */}
        {mode === 'manual' && (
          <div className="flex flex-col gap-3 text-xs">
            <p className="text-slate-400">
              Enter known real-world scale factor (centimetres per image pixel):
            </p>
            <div>
              <label className="text-slate-300 font-medium block mb-1">Scale (cm / pixel):</label>
              <input
                type="number"
                step="0.01"
                min="0.001"
                value={scaleVal}
                onChange={(e) => setScaleVal(parseFloat(e.target.value) || 0.15)}
                className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-white font-mono text-sm"
              />
            </div>
            <button
              onClick={() => {
                onSaveManual(scaleVal);
                onClose();
              }}
              className="btn btn-primary text-xs py-2 mt-2"
            >
              <Check className="w-4 h-4" /> Save Manual Scale
            </button>
          </div>
        )}

        {/* Option 2: 2-Point Click */}
        {mode === 'two_point' && (
          <div className="flex flex-col gap-3 text-xs">
            <p className="text-slate-400">
              Specify known distance between 2 points, then click on two distinct features on the image.
            </p>
            <div>
              <label className="text-slate-300 font-medium block mb-1">Known Real Distance (cm):</label>
              <input
                type="number"
                step="0.5"
                min="1.0"
                value={twoPointDistance}
                onChange={(e) => setTwoPointDistance(parseFloat(e.target.value) || 20.0)}
                className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-white font-mono text-sm"
              />
            </div>
            <button
              onClick={() => {
                onStartTwoPoint(twoPointDistance);
                onClose();
              }}
              className="btn bg-amber-600 hover:bg-amber-700 text-white text-xs py-2 mt-2"
            >
              <Crosshair className="w-4 h-4" /> Start 2-Point Selection on Image
            </button>
          </div>
        )}

        {/* Option 3: ArUco Marker */}
        {mode === 'aruco' && (
          <div className="flex flex-col gap-3 text-xs">
            <p className="text-slate-400">
              Place a printed ArUco marker (DICT_4X4_50) of known size on the ground ahead of the rover.
            </p>
            <div className="p-3 bg-slate-950 rounded border border-slate-800 flex items-center gap-3">
              <QrCode className="w-8 h-8 text-sky-400 shrink-0" />
              <div className="text-slate-300">
                <span className="font-semibold block">Automatic Ground Homography</span>
                <span className="text-[11px] text-slate-400">
                  Detects markers and automatically recovers camera tilt & perspective warping.
                </span>
              </div>
            </div>
            <button
              onClick={() => {
                alert('Place ArUco marker in the camera view; auto-detection triggers on image capture.');
                onClose();
              }}
              className="btn btn-secondary text-xs py-2 mt-2"
            >
              Enable ArUco Detection
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
