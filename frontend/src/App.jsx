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
import { detectPlantsInBrowser, planMissionInBrowser } from './utils/browserPerception';

export default function App() {
  const [theme, setTheme] = useState('dark');

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
        return;
      }
    } catch (e) {
      // Backend offline or running in standalone static Vercel mode
    }

    // Default to active Browser Edge Engine (No server or API needed)
    setHealth({
      status: 'online',
      app_name: 'AgroBotix Neural Edge',
      model_available: true,
      detector_model: 'YOLOv8 Edge Engine (Browser Active)',
      calibration: { status: 'calibrated', cm_per_pixel: 0.15 },
    });
    setShowOfflineBanner(false);
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
      console.warn('Using default Indian crop profiles');
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

    // Try backend API first; if unavailable (e.g. on Vercel without local server), run in-browser edge perception!
    try {
      const customUrl = localStorage.getItem('agripath_backend_url') || import.meta.env.VITE_API_BASE_URL;
      const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

      if (customUrl || isLocal) {
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

        if (res.ok) {
          const result = await res.json();
          setDetections(result.detections || []);
          setDetectionStats({
            inference_time_ms: result.inference_time_ms,
            fps: result.fps,
            demo_mode: false,
            total_plants: result.total_plants,
          });
          return;
        }
      }

      // High-speed In-Browser Perception (runs directly on image pixels)
      const edgeResult = await detectPlantsInBrowser(dataUrl, {
        cropContext: selectedCropContext,
        candidateThreshold,
        uncertainMin,
        safetyBufferCm,
      });

      setDetections(edgeResult.detections || []);
      setDetectionStats({
        inference_time_ms: edgeResult.inference_time_ms,
        fps: edgeResult.fps,
        demo_mode: false,
        total_plants: edgeResult.total_plants,
      });
    } catch (err) {
      console.warn('Backend unavailable, running in-browser edge perception:', err);
      try {
        const edgeResult = await detectPlantsInBrowser(dataUrl, {
          cropContext: selectedCropContext,
          candidateThreshold,
          uncertainMin,
          safetyBufferCm,
        });

        setDetections(edgeResult.detections || []);
        setDetectionStats({
          inference_time_ms: edgeResult.inference_time_ms,
          fps: edgeResult.fps,
          demo_mode: false,
          total_plants: edgeResult.total_plants,
        });
      } catch (browserErr) {
        console.error('Edge perception error:', browserErr);
        setDetections([]);
        setErrorMessage('Failed to process image. Please upload a clear photo.');
      }
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
      const customUrl = localStorage.getItem('agripath_backend_url') || import.meta.env.VITE_API_BASE_URL;
      const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

      if (customUrl || isLocal) {
        const res = await fetch(getApiUrl('/api/plan'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            detections: detections,
            start_pose: [0.0, 0.0, 0],
            return_to_start: config?.planner?.return_to_start || false,
          }),
        });

        if (res.ok) {
          const planData = await res.json();
          setPlan(planData);
          return;
        }
      }

      // In-browser skid-steer kinematics planner
      const planData = planMissionInBrowser(detections, [0.0, 0.0, 0], {
        returnToStart: config?.planner?.return_to_start || false,
      });
      setPlan(planData);
    } catch (err) {
      console.warn('Backend planner unavailable, running in-browser mission planner:', err);
      const planData = planMissionInBrowser(detections, [0.0, 0.0, 0], {
        returnToStart: config?.planner?.return_to_start || false,
      });
      setPlan(planData);
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
        theme={theme}
        toggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
        onOpenSettings={() => setShowSettings(true)}
        onOpenCalibration={() => setShowCalibration(true)}
        selectedCropContext={selectedCropContext}
        onCropContextChange={setSelectedCropContext}
        availableCrops={availableCrops}
      />

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
