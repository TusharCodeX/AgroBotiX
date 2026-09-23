import React, { useState, useEffect } from 'react';
import { AlertTriangle, AlertCircle, XCircle } from 'lucide-react';
import Navbar from './components/Navbar';
import CanvasViewer from './components/CanvasViewer';
import ControlPanel from './components/ControlPanel';
import CommandsList from './components/CommandsList';
import SimulationPlayer from './components/SimulationPlayer';
import CalibrationModal from './components/CalibrationModal';
import SettingsModal from './components/SettingsModal';
import FeedbackModal from './components/FeedbackModal';
import EvaluationView from './components/EvaluationView';

export default function App() {
  const [theme, setTheme] = useState('dark');
  const [currentTab, setCurrentTab] = useState('perception');

  // Backend Health & Config State
  const [health, setHealth] = useState(null);
  const [config, setConfig] = useState(null);
  const [availableCrops, setAvailableCrops] = useState([]);
  const [showOfflineBanner, setShowOfflineBanner] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // Indian Agronomic Perception Parameters
  const [selectedCropContext, setSelectedCropContext] = useState('wheat');
  const [candidateThreshold, setCandidateThreshold] = useState(0.70);
  const [uncertainMin, setUncertainMin] = useState(0.50);
  const [safetyBufferCm, setSafetyBufferCm] = useState(5.0);

  // Vision & Planning State
  const [imageSrc, setImageSrc] = useState(null);
  const [detections, setDetections] = useState([]);
  const [detectionStats, setDetectionStats] = useState(null);
  const [plan, setPlan] = useState(null);
  const [simPose, setSimPose] = useState(null);

  // Loading States
  const [isDetecting, setIsDetecting] = useState(false);
  const [isPlanning, setIsPlanning] = useState(false);

  // Modals & Calibration
  const [showSettings, setShowSettings] = useState(false);
  const [showCalibration, setShowCalibration] = useState(false);
  const [selectedPlantFeedback, setSelectedPlantFeedback] = useState(null);

  // 2-Point Calibration workflow state
  const [calibratingTwoPoint, setCalibratingTwoPoint] = useState(false);
  const [twoPointDistance, setTwoPointDistance] = useState(20.0);
  const [clickedPoints, setClickedPoints] = useState([]);

  // Dynamic API Base URL resolution (Vercel env variable or user-defined in localStorage)
  const getApiUrl = (path) => {
    const customUrl = localStorage.getItem('agripath_backend_url') || import.meta.env.VITE_API_BASE_URL || '';
    const cleanBase = customUrl.replace(/\/+$/, '');
    return cleanBase ? `${cleanBase}${path}` : path;
  };

  // Fetch initial health and config
  const fetchHealth = async () => {
    try {
      const res = await fetch(getApiUrl('/api/health'));
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
        setShowOfflineBanner(false);
      } else {
        setHealth(null);
        setShowOfflineBanner(true);
      }
    } catch (e) {
      console.warn('Backend offline or not reachable:', e);
      setHealth(null);
      setShowOfflineBanner(true);
    }
  };

  const fetchConfig = async () => {
    try {
      const res = await fetch(getApiUrl('/api/config'));
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      }
    } catch (e) {
      console.warn('Config fetch error:', e);
    }
  };

  const fetchCrops = async () => {
    try {
      const res = await fetch(getApiUrl('/api/crops'));
      if (res.ok) {
        const data = await res.json();
        setAvailableCrops(data.crops || []);
      }
    } catch (e) {
      console.warn('Failed to fetch Indian crop profiles:', e);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchConfig();
    fetchCrops();
  }, []);

  const handleImageCaptured = async (dataUrl, isLive = false) => {
    setImageSrc(dataUrl);
    setIsDetecting(true);
    setPlan(null);
    setErrorMessage(null);

    try {
      const formData = new FormData();
      formData.append('image_base64', dataUrl);
      formData.append('is_live', isLive ? 'true' : 'false');
      formData.append('crop_context', selectedCropContext);
      formData.append('candidate_threshold', candidateThreshold.toString());
      formData.append('uncertain_min', uncertainMin.toString());
      formData.append('safety_buffer_cm', safetyBufferCm.toString());

      const res = await fetch(getApiUrl('/api/detect'), {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        let msg = `Detection request failed: HTTP ${res.status}`;
        try {
          const errData = await res.json();
          if (errData.detail) msg = errData.detail;
        } catch (_) {}
        throw new Error(msg);
      }

      const result = await res.json();
      setDetections(result.detections || []);
      setDetectionStats({
        inference_time_ms: result.inference_time_ms,
        fps: result.fps,
        demo_mode: false,
        total_plants: result.total_plants,
      });
      fetchHealth();
    } catch (err) {
      console.error('Detection error:', err);
      // Strictly do NOT generate fake mock boxes!
      setDetections([]);
      setErrorMessage(err.message || 'Detection failed. Ensure backend YOLOv8 ONNX model is running.');
    } finally {
      setIsDetecting(false);
    }
  };

  const handlePlanMission = async () => {
    if (!detections.length) {
      alert('Please capture or upload an image with detected plants first.');
      return;
    }

    setIsPlanning(true);
    setErrorMessage(null);
    try {
      const res = await fetch(getApiUrl('/api/plan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          detections: detections,
          start_pose: [0.0, 0.0, 0],
          return_to_start: config?.planner?.return_to_start || false,
        }),
      });

      if (!res.ok) {
        let msg = `Path planning failed: HTTP ${res.status}`;
        try {
          const errData = await res.json();
          if (errData.detail) msg = errData.detail;
        } catch (_) {}
        throw new Error(msg);
      }

      const planData = await res.json();
      setPlan(planData);
    } catch (err) {
      console.error('Path planning error:', err);
      alert(`Path planning error: ${err.message}`);
    } finally {
      setIsPlanning(false);
    }
  };

  const handleSaveManualScale = async (scale) => {
    try {
      const res = await fetch(getApiUrl('/api/calibrate/manual'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cm_per_pixel: scale }),
      });
      if (res.ok) {
        fetchHealth();
      }
    } catch (err) {
      console.error('Save scale error:', err);
    }
  };

  const handleStartTwoPoint = (distCm) => {
    setTwoPointDistance(distCm);
    setClickedPoints([]);
    setCalibratingTwoPoint(true);
  };

  const handleTwoPointCanvasClick = async (x, y) => {
    const updated = [...clickedPoints, [x, y]];
    setClickedPoints(updated);

    if (updated.length === 2) {
      setCalibratingTwoPoint(false);
      try {
        const res = await fetch(getApiUrl('/api/calibrate/two-point'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pt1: updated[0],
            pt2: updated[1],
            real_distance_cm: twoPointDistance,
          }),
        });
        if (res.ok) {
          fetchHealth();
          alert('Two-point calibration successful!');
        }
      } catch (err) {
        console.error('Two-point calibration error:', err);
      }
    }
  };

  const handleSaveConfig = async (newCfg) => {
    try {
      const res = await fetch(getApiUrl('/api/config'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCfg),
      });
      if (res.ok) {
        setConfig(newCfg);
        fetchHealth();
      }
    } catch (err) {
      console.error('Save config error:', err);
    }
  };

  const handleSubmitFeedback = async (feedbackData) => {
    try {
      await fetch(getApiUrl('/api/feedback'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedbackData),
      });
    } catch (err) {
      console.error('Submit feedback error:', err);
    }
  };

  return (
    <div className={`min-h-screen ${theme === 'light' ? 'light-theme' : ''}`}>
      <Navbar
        health={health}
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        theme={theme}
        toggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
        onOpenSettings={() => setShowSettings(true)}
        onOpenCalibration={() => setShowCalibration(true)}
        selectedCropContext={selectedCropContext}
        onCropContextChange={setSelectedCropContext}
        availableCrops={availableCrops}
      />

      {showOfflineBanner && !health && (
        <div className="bg-amber-950/90 border-b border-amber-500/50 text-amber-200 px-4 py-2.5 text-xs flex flex-wrap items-center justify-between gap-2 shadow-inner">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Model Backend Offline:</strong> Real neural network inference and Indian field safety validation requires the Python FastAPI backend. Connect backend at <code className="bg-amber-900/60 px-1.5 py-0.5 rounded text-white font-mono">http://localhost:8000</code> or set URL in Settings (⚙️). Fake/mock detections are strictly disabled.
            </span>
          </div>
          <button
            onClick={() => setShowSettings(true)}
            className="px-3 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-semibold transition shrink-0"
          >
            Connect Backend (⚙️)
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="max-w-7xl mx-auto mt-3 px-4">
          <div className="bg-rose-950/80 border border-rose-500/50 text-rose-200 px-4 py-2.5 rounded-lg text-xs flex items-center justify-between gap-2 shadow">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span><strong>Inference Error:</strong> {errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-white">
              <XCircle className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto p-4">
        {currentTab === 'perception' ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Left / Center Column: Field Canvas Viewer & Simulation */}
            <div className="lg:col-span-8 flex flex-col gap-4">
              <CanvasViewer
                imageSrc={imageSrc}
                detections={detections}
                plan={plan}
                simPose={simPose}
                calibratingTwoPoint={calibratingTwoPoint}
                onTwoPointClick={handleTwoPointCanvasClick}
                onWrongDetection={(plant) => setSelectedPlantFeedback(plant)}
                calibrator={health?.calibration}
                cropContext={selectedCropContext}
                safetyBufferCm={safetyBufferCm}
              />

              {plan && (
                <SimulationPlayer
                  plan={plan}
                  onPoseUpdate={(pose) => setSimPose(pose)}
                />
              )}
            </div>

            {/* Right Column: Perception Inputs, Mission Control & Command Queue */}
            <div className="lg:col-span-4 flex flex-col gap-4">
              <ControlPanel
                onImageCaptured={handleImageCaptured}
                onPlanMission={handlePlanMission}
                isDetecting={isDetecting}
                isPlanning={isPlanning}
                detectionStats={detectionStats}
                planStats={plan}
                selectedCropContext={selectedCropContext}
                candidateThreshold={candidateThreshold}
                onCandidateThresholdChange={setCandidateThreshold}
                uncertainMin={uncertainMin}
                onUncertainMinChange={setUncertainMin}
                safetyBufferCm={safetyBufferCm}
                onSafetyBufferCmChange={setSafetyBufferCm}
                health={health}
              />

              <CommandsList plan={plan} />
            </div>
          </div>
        ) : (
          <EvaluationView />
        )}
      </main>

      {/* Modals */}
      <CalibrationModal
        isOpen={showCalibration}
        onClose={() => setShowCalibration(false)}
        currentScale={health?.calibration?.cm_per_pixel}
        onSaveManual={handleSaveManualScale}
        onStartTwoPoint={handleStartTwoPoint}
      />

      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        config={config}
        onSaveConfig={handleSaveConfig}
      />

      <FeedbackModal
        isOpen={!!selectedPlantFeedback}
        onClose={() => setSelectedPlantFeedback(null)}
        plant={selectedPlantFeedback}
        imageSrc={imageSrc}
        onSubmitFeedback={handleSubmitFeedback}
      />
    </div>
  );
}
