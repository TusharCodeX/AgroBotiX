import React, { useState, useEffect } from 'react';
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
      } else {
        setHealth(null);
      }
    } catch (e) {
      console.warn('Backend offline or not reachable, using Vercel Cloud Demo mode:', e);
      setHealth(null);
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

  useEffect(() => {
    fetchHealth();
    fetchConfig();

    // Create an initial sample synthetic image so the app is immediately testable
    createInitialSyntheticField();
  }, []);

  const createInitialSyntheticField = () => {
    const canvas = document.createElement('canvas');
    canvas.width = 1000;
    canvas.height = 600;
    const ctx = canvas.getContext('2d');

    // Soil
    ctx.fillStyle = '#453823';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Subtle soil texture
    for (let i = 0; i < 400; i++) {
      ctx.fillStyle = i % 2 === 0 ? '#382d1b' : '#52432a';
      ctx.beginPath();
      ctx.arc(Math.random() * canvas.width, Math.random() * canvas.height, Math.random() * 3, 0, Math.PI * 2);
      ctx.fill();
    }

    // 2 Crops (large green circles)
    ctx.fillStyle = '#22c55e';
    ctx.beginPath();
    ctx.arc(300, 240, 50, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#16a34a';
    ctx.beginPath();
    ctx.arc(300, 240, 35, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#22c55e';
    ctx.beginPath();
    ctx.arc(700, 240, 55, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#16a34a';
    ctx.beginPath();
    ctx.arc(700, 240, 40, 0, Math.PI * 2);
    ctx.fill();

    // 2 Weeds (smaller irregular red/yellowish green patches)
    ctx.fillStyle = '#4ade80';
    ctx.beginPath();
    ctx.arc(500, 380, 25, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#86efac';
    ctx.beginPath();
    ctx.arc(350, 480, 20, 0, Math.PI * 2);
    ctx.fill();

    const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
    handleImageCaptured(dataUrl, false);
  };

  // Client-side fallback detection simulation when deployed on Vercel without active backend
  const simulateClientDetections = () => {
    const mockDetections = [
      {
        id: 1,
        class_id: 0,
        raw_class_name: 'crop',
        status: 'CROP',
        confidence: 0.942,
        bbox_px: [250, 190, 350, 290],
        center_px: [300, 240],
        center_cm: [-15.0, 54.0],
        bbox_cm: [-22.5, 46.5, -7.5, 61.5],
        is_obstacle: true,
        is_target: false,
      },
      {
        id: 2,
        class_id: 0,
        raw_class_name: 'crop',
        status: 'CROP',
        confidence: 0.915,
        bbox_px: [645, 185, 755, 295],
        center_px: [700, 240],
        center_cm: [15.0, 54.0],
        bbox_cm: [6.75, 45.75, 23.25, 62.25],
        is_obstacle: true,
        is_target: false,
      },
      {
        id: 3,
        class_id: 1,
        raw_class_name: 'weed',
        status: 'WEED',
        confidence: 0.884,
        bbox_px: [475, 355, 525, 405],
        center_px: [500, 380],
        center_cm: [0.0, 33.0],
        bbox_cm: [-3.75, 29.25, 3.75, 36.75],
        is_obstacle: false,
        is_target: true,
      },
      {
        id: 4,
        class_id: 1,
        raw_class_name: 'weed',
        status: 'WEED',
        confidence: 0.826,
        bbox_px: [330, 460, 370, 500],
        center_px: [350, 480],
        center_cm: [-11.2, 18.0],
        bbox_cm: [-14.2, 15.0, -8.2, 21.0],
        is_obstacle: false,
        is_target: true,
      },
    ];

    setDetections(mockDetections);
    setDetectionStats({
      inference_time_ms: 18.5,
      fps: 54.0,
      demo_mode: true,
      total_plants: 4,
    });
  };

  // Client-side fallback planning simulation when deployed on Vercel without active backend
  const simulateClientPlan = () => {
    const mockPlan = {
      success: true,
      total_distance_cm: 64.2,
      total_turns: 4,
      estimated_time_s: 10.3,
      handled_weeds: [4, 3],
      skipped_weeds: [],
      total_weeds: 2,
      path: [
        { x: 0.0, y: 0.0, heading: 0 },
        { x: 0.0, y: 8.0, heading: 0 },
        { x: 0.0, y: 8.0, heading: 3 },
        { x: -11.2, y: 8.0, heading: 3 },
        { x: -11.2, y: 8.0, heading: 0 },
        { x: -11.2, y: 10.0, heading: 0 },
        { x: -11.2, y: 10.0, heading: 1 },
        { x: 0.0, y: 10.0, heading: 1 },
        { x: 0.0, y: 10.0, heading: 0 },
        { x: 0.0, y: 23.0, heading: 0 },
      ],
      commands: [
        { seq: 1, action: 'FORWARD', dist_cm: 8.0, blade_active: false, raw: 'F80' },
        { seq: 2, action: 'TURN_LEFT', angle_deg: 90, blade_active: false, raw: 'TL90' },
        { seq: 3, action: 'FORWARD', dist_cm: 11.2, blade_active: false, raw: 'F112' },
        { seq: 4, action: 'TURN_RIGHT', angle_deg: 90, blade_active: false, raw: 'TR90' },
        { seq: 5, action: 'FORWARD', dist_cm: 2.0, blade_active: false, raw: 'F20' },
        { seq: 6, action: 'CUT', target_weed_id: 4, blade_active: true, raw: 'CUT4' },
        { seq: 7, action: 'TURN_RIGHT', angle_deg: 90, blade_active: false, raw: 'TR90' },
        { seq: 8, action: 'FORWARD', dist_cm: 11.2, blade_active: false, raw: 'F112' },
        { seq: 9, action: 'TURN_LEFT', angle_deg: 90, blade_active: false, raw: 'TL90' },
        { seq: 10, action: 'FORWARD', dist_cm: 13.0, blade_active: false, raw: 'F130' },
        { seq: 11, action: 'CUT', target_weed_id: 3, blade_active: true, raw: 'CUT3' },
      ],
    };
    setPlan(mockPlan);
  };

  const handleImageCaptured = async (dataUrl, isLive = false) => {
    setImageSrc(dataUrl);
    setIsDetecting(true);
    setPlan(null);

    try {
      const formData = new FormData();
      formData.append('image_base64', dataUrl);
      formData.append('is_live', isLive ? 'true' : 'false');

      const res = await fetch(getApiUrl('/api/detect'), {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Detection request failed: ${res.status}`);
      }

      const result = await res.json();
      setDetections(result.detections || []);
      setDetectionStats({
        inference_time_ms: result.inference_time_ms,
        fps: result.fps,
        demo_mode: result.demo_mode,
        total_plants: result.total_plants,
      });
      fetchHealth();
    } catch (err) {
      console.warn('Backend unavailable, using client-side simulation:', err);
      simulateClientDetections();
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
        throw new Error(`Path planning failed: ${res.status}`);
      }

      const planData = await res.json();
      setPlan(planData);
    } catch (err) {
      console.warn('Backend planner unavailable, using client-side kinematics simulation:', err);
      simulateClientPlan();
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
      />

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
