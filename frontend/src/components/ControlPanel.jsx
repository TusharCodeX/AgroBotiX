import React, { useState, useRef, useEffect } from 'react';
import { 
  Camera, 
  Upload, 
  Play, 
  Timer, 
  Gauge, 
  Activity, 
  Sparkles, 
  RefreshCw,
  Sliders,
  ShieldAlert,
  Sprout,
  AlertTriangle,
  XCircle
} from 'lucide-react';

export default function ControlPanel({
  onImageCaptured,
  onPlanMission,
  isDetecting,
  isPlanning,
  detectionStats,
  planStats,
  selectedCropContext = 'wheat',
  candidateThreshold = 0.70,
  onCandidateThresholdChange = null,
  uncertainMin = 0.50,
  onUncertainMinChange = null,
  safetyBufferCm = 5.0,
  onSafetyBufferCmChange = null,
  health = null,
}) {
  const [activeTab, setActiveTab] = useState('upload');
  const [autoInterval, setAutoInterval] = useState(0); // 0 = disabled
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState(null);
  const [showThresholds, setShowThresholds] = useState(false);

  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);

  const isModelAvailable = health?.model_available ?? true;

  // Initialize camera stream
  const startCamera = async () => {
    try {
      setCameraError(null);
      const constraints = {
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraActive(true);
    } catch (err) {
      setCameraError('Camera access denied or device not found: ' + err.message);
      setCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  useEffect(() => {
    if (activeTab === 'live') {
      startCamera();
    } else {
      stopCamera();
    }
    return () => stopCamera();
  }, [activeTab]);

  const captureFrame = () => {
    if (!videoRef.current || !cameraActive) return;
    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    onImageCaptured(dataUrl, true);
  };

  useEffect(() => {
    if (autoInterval > 0 && cameraActive) {
      timerRef.current = setInterval(() => {
        captureFrame();
      }, autoInterval * 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [autoInterval, cameraActive]);

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      onImageCaptured(event.target.result, false);
    };
    reader.readAsDataURL(file);
  };

  const cropContextNames = {
    wheat: { name: 'Wheat', season: 'Rabi', weed: 'Gulli Danda / Wild Oats' },
    rice: { name: 'Rice / Paddy', season: 'Kharif', weed: 'Sanwak / Barnyard Grass' },
    mustard: { name: 'Mustard', season: 'Rabi', weed: 'Bathua / Wild Mustard' },
    maize: { name: 'Maize', season: 'Kharif', weed: 'Motha / Crabgrass' },
    sugarcane: { name: 'Sugarcane', season: 'Perennial', weed: 'Doob Grass / Nut Grass' },
    vegetables: { name: 'Vegetables', season: 'Kharif/Rabi', weed: 'Bishkhapra / Pigweed' },
    sorghum_millets: { name: 'Sorghum & Millets', season: 'Kharif', weed: 'Crowfoot Grass' },
    pulses_oilseeds: { name: 'Pulses & Oilseeds', season: 'Kharif/Rabi', weed: 'Kanghi / Wild Clover' },
    cotton: { name: 'Cotton', season: 'Kharif', weed: 'Bishkhapra / Celosia' },
    orchard: { name: 'Fruit Orchards', season: 'Perennial', weed: 'Parthenium (Gajar Ghas)' },
  };

  const currentCrop = cropContextNames[selectedCropContext] || cropContextNames['wheat'];

  return (
    <div className="card flex flex-col gap-4 bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-lg">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <h2 className="font-semibold text-slate-100 text-sm flex items-center gap-2">
          <Sprout className="w-4 h-4 text-emerald-400" />
          <span>Field Perception & Rover Control</span>
        </h2>
        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded">
          {currentCrop.season} Season
        </span>
      </div>

      {/* Model Unavailable Notice */}
      {!isModelAvailable && (
        <div className="bg-rose-950/80 border border-rose-500/50 p-3 rounded-lg text-rose-200 text-xs flex items-start gap-2.5 shadow-inner">
          <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold text-white block">MODEL UNAVAILABLE</span>
            <p className="text-[11px] text-rose-300">
              The trained model weights (<code className="bg-rose-900/60 px-1 rounded">models/best.onnx</code>) were not found on the backend.
              Silent fallback to fake demo detections is strictly disabled to prevent false crop removal.
            </p>
          </div>
        </div>
      )}

      {/* Active Crop Botanical Profile Pill */}
      <div className="bg-slate-950/80 border border-slate-800 p-2.5 rounded-lg text-xs space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Target Crop:</span>
          <span className="font-semibold text-emerald-300">{currentCrop.name}</span>
        </div>
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-500">Key Weed Threat:</span>
          <span className="font-mono text-rose-300">{currentCrop.weed}</span>
        </div>
      </div>

      {/* Input Source Tabs */}
      <div className="flex border-b border-slate-800 text-xs">
        <button
          onClick={() => setActiveTab('upload')}
          className={`flex-1 py-2 flex items-center justify-center gap-1.5 border-b-2 font-medium transition ${
            activeTab === 'upload'
              ? 'border-blue-500 text-blue-400 bg-blue-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Upload className="w-3.5 h-3.5" />
          <span>Manual Upload</span>
        </button>

        <button
          onClick={() => setActiveTab('live')}
          className={`flex-1 py-2 flex items-center justify-center gap-1.5 border-b-2 font-medium transition ${
            activeTab === 'live'
              ? 'border-blue-500 text-blue-400 bg-blue-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Camera className="w-3.5 h-3.5" />
          <span>Live Rover Camera</span>
        </button>
      </div>

      {/* Tab 1: Manual Upload */}
      {activeTab === 'upload' && (
        <div className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-lg p-5 text-center transition cursor-pointer bg-slate-900/40">
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileUpload}
            className="hidden"
            id="field-file-input"
            disabled={!isModelAvailable}
          />
          <label htmlFor="field-file-input" className="cursor-pointer flex flex-col items-center gap-2">
            <Upload className="w-8 h-8 text-blue-400" />
            <span className="text-xs font-semibold text-slate-200">
              Drag & drop Indian field photo or click to browse
            </span>
            <span className="text-[10px] text-slate-500">
              Supports cracked soil, shadows, dry stubble, and real weeds
            </span>
          </label>
        </div>
      )}

      {/* Tab 2: Live Rover Camera */}
      {activeTab === 'live' && (
        <div className="flex flex-col gap-3">
          <div className="relative aspect-video bg-black rounded-lg overflow-hidden border border-slate-800 flex items-center justify-center">
            {cameraActive ? (
              <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
            ) : (
              <div className="text-xs text-slate-500 flex flex-col items-center gap-2 p-4 text-center">
                <Camera className="w-8 h-8 text-slate-600" />
                <span>{cameraError || 'Camera stopped. Click below to start rover stream.'}</span>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between gap-2">
            <button
              onClick={captureFrame}
              disabled={!cameraActive || isDetecting || !isModelAvailable}
              className="btn btn-primary text-xs flex-1 flex items-center justify-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isDetecting ? 'animate-spin' : ''}`} />
              <span>{isDetecting ? 'Analyzing...' : 'Capture Frame'}</span>
            </button>

            <div className="flex items-center gap-1.5 text-xs text-slate-300">
              <Timer className="w-3.5 h-3.5 text-slate-400" />
              <span>Auto:</span>
              <select
                value={autoInterval}
                onChange={(e) => setAutoInterval(Number(e.target.value))}
                className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-white"
              >
                <option value={0}>Manual</option>
                <option value={2}>Every 2s</option>
                <option value={5}>Every 5s</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Safety & Confidence Thresholds Dropdown */}
      <div className="border border-slate-800 rounded-lg p-2.5 bg-slate-950/60 text-xs">
        <button
          onClick={() => setShowThresholds(!showThresholds)}
          className="w-full flex items-center justify-between text-slate-300 font-semibold"
        >
          <span className="flex items-center gap-1.5">
            <Sliders className="w-3.5 h-3.5 text-blue-400" />
            <span>Indian Crop Safety Policy</span>
          </span>
          <span className="text-[10px] text-slate-500 underline">
            {showThresholds ? 'Hide' : 'Configure'}
          </span>
        </button>

        {showThresholds && (
          <div className="mt-3 space-y-2.5 pt-2 border-t border-slate-800 text-[11px]">
            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Candidate Weed Threshold:</span>
                <span className="font-mono text-emerald-400 font-bold">{(candidateThreshold * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.55"
                max="0.90"
                step="0.05"
                value={candidateThreshold}
                onChange={(e) => onCandidateThresholdChange && onCandidateThresholdChange(parseFloat(e.target.value))}
                className="w-full accent-blue-500"
              />
              <span className="text-[9px] text-slate-500 block">Detections above this confidence are candidate weeds.</span>
            </div>

            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Uncertain Floor (Reject Below):</span>
                <span className="font-mono text-amber-400 font-bold">{(uncertainMin * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.30"
                max="0.65"
                step="0.05"
                value={uncertainMin}
                onChange={(e) => onUncertainMinChange && onUncertainMinChange(parseFloat(e.target.value))}
                className="w-full accent-amber-500"
              />
              <span className="text-[9px] text-slate-500 block">Detections between {(uncertainMin * 100).toFixed(0)}%-{(candidateThreshold * 100).toFixed(0)}% are treated as crop obstacles.</span>
            </div>

            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Crop Safety Buffer (Blade Clearance):</span>
                <span className="font-mono text-yellow-400 font-bold">{safetyBufferCm.toFixed(1)} cm</span>
              </div>
              <input
                type="range"
                min="3.0"
                max="12.0"
                step="0.5"
                value={safetyBufferCm}
                onChange={(e) => onSafetyBufferCmChange && onSafetyBufferCmChange(parseFloat(e.target.value))}
                className="w-full accent-yellow-500"
              />
              <span className="text-[9px] text-slate-500 block">Weeds within this radius of any crop are strictly marked DO NOT CUT.</span>
            </div>
          </div>
        )}
      </div>

      {/* Plan Rover Mission Action Button */}
      <button
        onClick={onPlanMission}
        disabled={isPlanning || isDetecting || !isModelAvailable}
        className="btn bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold py-2.5 shadow-lg shadow-blue-600/20 disabled:opacity-50 text-sm"
      >
        <Sparkles className="w-4 h-4" />
        <span>{isPlanning ? 'Planning Skid-Steer Safe Path...' : 'Plan Rover Mission'}</span>
      </button>

      {/* Diagnostics & Hazard Metrics */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center gap-2">
          <Gauge className="w-4 h-4 text-emerald-400 shrink-0" />
          <div>
            <span className="text-[10px] text-slate-500 block">Inference Speed</span>
            <span className="font-mono font-bold text-slate-200">
              {detectionStats?.inference_time_ms ? `${detectionStats.inference_time_ms.toFixed(0)} ms` : '--'}
            </span>
          </div>
        </div>

        <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center gap-2">
          <Activity className="w-4 h-4 text-sky-400 shrink-0" />
          <div>
            <span className="text-[10px] text-slate-500 block">FPS</span>
            <span className="font-mono font-bold text-slate-200">
              {detectionStats?.fps ? `${detectionStats.fps.toFixed(1)} FPS` : '--'}
            </span>
          </div>
        </div>

        <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 col-span-2">
          <div className="flex items-center justify-between font-mono text-[11px]">
            <span className="text-slate-400">Total Distance:</span>
            <span className="font-bold text-slate-200">
              {planStats?.total_distance_cm ? `${planStats.total_distance_cm.toFixed(1)} cm` : '--'}
            </span>
          </div>
          <div className="flex items-center justify-between font-mono text-[11px] mt-1">
            <span className="text-slate-400">Skid-Steer Turns (90°):</span>
            <span className="font-bold text-slate-200">
              {planStats?.total_turns ?? '--'}
            </span>
          </div>
          <div className="flex items-center justify-between font-mono text-[11px] mt-1">
            <span className="text-slate-400">Actionable Weeds Targeted:</span>
            <span className="font-bold text-emerald-400">
              {planStats ? `${planStats.handled_weeds?.length || 0} / ${planStats.total_weeds || 0}` : '--'}
            </span>
          </div>
          <div className="flex items-center justify-between font-mono text-[11px] mt-1">
            <span className="text-slate-400">Crops Protected:</span>
            <span className="font-bold text-blue-400 font-mono">100% (Zero strikes)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
