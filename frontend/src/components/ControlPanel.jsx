import React, { useState, useRef, useEffect } from 'react';
import { 
  Camera, 
  Upload, 
  Play, 
  Timer, 
  Gauge, 
  Activity, 
  Sparkles, 
  RefreshCw 
} from 'lucide-react';

export default function ControlPanel({
  onImageCaptured,
  onPlanMission,
  isDetecting,
  isPlanning,
  detectionStats,
  planStats,
}) {
  const [activeTab, setActiveTab] = useState('live');
  const [autoInterval, setAutoInterval] = useState(0); // 0 = disabled
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState(null);

  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);

  // Initialize camera stream
  const startCamera = async () => {
    try {
      setCameraError(null);
      const constraints = {
        video: {
          facingMode: { ideal: 'environment' }, // Prefer rear camera on mobile
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

  // Capture frame from video element
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

  // Auto-capture timer
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

  // File Upload
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      onImageCaptured(event.target.result, false);
    };
    reader.readAsDataURL(file);
  };

  const loadFieldPreset = (type) => {
    const canvas = document.createElement('canvas');
    canvas.width = 1000;
    canvas.height = 600;
    const ctx = canvas.getContext('2d');

    // Soil background
    ctx.fillStyle = '#3a2d1d';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (let i = 0; i < 200; i++) {
      ctx.fillStyle = i % 2 === 0 ? '#2d2215' : '#4d3d28';
      ctx.beginPath();
      ctx.arc(Math.random() * canvas.width, Math.random() * canvas.height, Math.random() * 2.5, 0, Math.PI * 2);
      ctx.fill();
    }

    const drawCrop = (x, y, r = 50) => {
      ctx.fillStyle = '#22c55e';
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#16a34a';
      ctx.beginPath();
      ctx.arc(x, y, r * 0.7, 0, Math.PI * 2);
      ctx.fill();
    };

    const drawWeed = (x, y, r = 22) => {
      ctx.fillStyle = '#4ade80';
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#86efac';
      ctx.beginPath();
      ctx.arc(x, y, r * 0.6, 0, Math.PI * 2);
      ctx.fill();
    };

    if (type === 'open') {
      drawWeed(500, 360, 24);
      drawWeed(500, 480, 22);
    } else if (type === 'detour') {
      drawCrop(500, 380, 55);
      drawWeed(500, 220, 24);
    } else if (type === 'trapped') {
      drawCrop(480, 350, 60);
      drawWeed(510, 350, 18);
    } else if (type === 'multi') {
      drawCrop(250, 250, 50);
      drawCrop(750, 250, 50);
      drawWeed(400, 480, 22);
      drawWeed(600, 480, 22);
      drawWeed(350, 340, 20);
      drawWeed(650, 340, 20);
    }

    const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
    onImageCaptured(dataUrl, false);
  };

  return (
    <div className="card flex flex-col gap-4">
      {/* Input Mode Tabs */}
      <div className="flex border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('live')}
          className={`flex items-center gap-1.5 px-3 py-1.5 font-medium text-xs rounded-t-md transition ${
            activeTab === 'live'
              ? 'text-blue-400 border-b-2 border-blue-500 bg-blue-500/10'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Camera className="w-3.5 h-3.5" />
          Live Capture
        </button>

        <button
          onClick={() => setActiveTab('upload')}
          className={`flex items-center gap-1.5 px-3 py-1.5 font-medium text-xs rounded-t-md transition ${
            activeTab === 'upload'
              ? 'text-blue-400 border-b-2 border-blue-500 bg-blue-500/10'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Upload className="w-3.5 h-3.5" />
          Manual Upload
        </button>

        <button
          onClick={() => setActiveTab('presets')}
          className={`flex items-center gap-1.5 px-3 py-1.5 font-medium text-xs rounded-t-md transition ${
            activeTab === 'presets'
              ? 'text-blue-400 border-b-2 border-blue-500 bg-blue-500/10'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          Demo Presets
        </button>
      </div>

      {/* Tab 1: Live Capture */}
      {activeTab === 'live' && (
        <div className="flex flex-col gap-2.5">
          <div className="relative rounded-lg overflow-hidden bg-black aspect-video border border-slate-800 flex items-center justify-center">
            {cameraError ? (
              <div className="p-4 text-center text-rose-400 text-xs">
                <p className="font-semibold">Camera Error</p>
                <p className="mt-1">{cameraError}</p>
                <button
                  onClick={startCamera}
                  className="btn btn-secondary text-xs mt-3 py-1"
                >
                  <RefreshCw className="w-3 h-3" /> Retry
                </button>
              </div>
            ) : (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />
            )}
          </div>

          <div className="flex items-center justify-between gap-2">
            <button
              onClick={captureFrame}
              disabled={!cameraActive || isDetecting}
              className="btn btn-primary flex-1 text-xs py-2"
            >
              <Camera className="w-4 h-4" />
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
                <option value={10}>Every 10s</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Manual Upload */}
      {activeTab === 'upload' && (
        <div className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-lg p-6 text-center transition cursor-pointer bg-slate-900/40">
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileUpload}
            className="hidden"
            id="field-file-input"
          />
          <label htmlFor="field-file-input" className="cursor-pointer flex flex-col items-center gap-2">
            <Upload className="w-8 h-8 text-blue-400" />
            <span className="text-xs font-semibold text-slate-200">
              Drag & drop field photo or click to browse
            </span>
            <span className="text-[10px] text-slate-500">Supports JPG, PNG, WEBP (EXIF auto-rotated)</span>
          </label>
        </div>
      )}

      {/* Tab 3: Synthetic Field Presets */}
      {activeTab === 'presets' && (
        <div className="flex flex-col gap-2 text-xs">
          <p className="text-slate-400 text-[11px]">
            Test detection & kinematic planning instantly on pre-configured field layouts:
          </p>

          <button
            onClick={() => loadFieldPreset('open')}
            className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-700 hover:border-blue-500 text-left transition flex items-center justify-between"
          >
            <div>
              <span className="font-semibold text-slate-200 block">1. Open Field (Collinear Weeds)</span>
              <span className="text-[10px] text-slate-400">2 weeds ahead in a line (straight pass)</span>
            </div>
            <span className="badge bg-emerald-500/20 text-emerald-400">Open</span>
          </button>

          <button
            onClick={() => loadFieldPreset('detour')}
            className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-700 hover:border-blue-500 text-left transition flex items-center justify-between"
          >
            <div>
              <span className="font-semibold text-slate-200 block">2. Crop Obstacle Detour</span>
              <span className="text-[10px] text-slate-400">Large crop in direct line of sight; maneuvers around</span>
            </div>
            <span className="badge bg-blue-500/20 text-blue-400">Obstacle</span>
          </button>

          <button
            onClick={() => loadFieldPreset('trapped')}
            className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-700 hover:border-blue-500 text-left transition flex items-center justify-between"
          >
            <div>
              <span className="font-semibold text-slate-200 block">3. Trapped Weed (Safety Skip)</span>
              <span className="text-[10px] text-slate-400">Weed inside crop safety buffer; marked SKIPPED</span>
            </div>
            <span className="badge bg-rose-500/20 text-rose-400">Skip Demo</span>
          </button>

          <button
            onClick={() => loadFieldPreset('multi')}
            className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-700 hover:border-blue-500 text-left transition flex items-center justify-between"
          >
            <div>
              <span className="font-semibold text-slate-200 block">4. Multi-Weed Mission</span>
              <span className="text-[10px] text-slate-400">4 weeds with turn slip penalty tour optimization</span>
            </div>
            <span className="badge bg-amber-500/20 text-amber-400">Multi-Target</span>
          </button>
        </div>
      )}

      {/* Plan Path Action Button */}
      <button
        onClick={onPlanMission}
        disabled={isPlanning || isDetecting}
        className="btn bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold py-2.5 shadow-lg shadow-blue-600/20 disabled:opacity-50 text-sm"
      >
        <Sparkles className="w-4 h-4" />
        <span>{isPlanning ? 'Planning Skid-Steer Path...' : 'Plan Rover Mission'}</span>
      </button>

      {/* Diagnostic & Telemetry Cards */}
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
            <span className="text-slate-400">Turns (90°):</span>
            <span className="font-bold text-slate-200">
              {planStats?.total_turns ?? '--'}
            </span>
          </div>
          <div className="flex items-center justify-between font-mono text-[11px] mt-1">
            <span className="text-slate-400">Est. Mission Time:</span>
            <span className="font-bold text-slate-200">
              {planStats?.estimated_time_s ? `${planStats.estimated_time_s.toFixed(1)} s` : '--'}
            </span>
          </div>
          <div className="flex items-center justify-between font-mono text-[11px] mt-1">
            <span className="text-slate-400">Weeds Handled / Total:</span>
            <span className="font-bold text-emerald-400">
              {planStats ? `${planStats.handled_weeds?.length || 0} / ${planStats.total_weeds || 0}` : '--'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
