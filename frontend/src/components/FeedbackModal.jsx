import React, { useState } from 'react';
import { X, Check, AlertCircle, Save } from 'lucide-react';

export default function FeedbackModal({ isOpen, onClose, plant, imageSrc, onSubmitFeedback }) {
  const [correctedClass, setCorrectedClass] = useState(
    plant?.status === 'CROP' ? 'weed' : 'crop'
  );
  const [submitted, setSubmitted] = useState(false);

  if (!isOpen || !plant) return null;

  const handleSubmit = () => {
    onSubmitFeedback({
      plant_id: plant.id,
      corrected_class: correctedClass,
      bbox_px: plant.bbox_px,
      image_base64: imageSrc,
    });
    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      onClose();
    }, 1500);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="card w-full max-w-sm bg-slate-900 border border-slate-700 shadow-2xl flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-amber-400" />
            <h3 className="font-semibold text-slate-100 text-sm">Correct Misclassification</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-3 text-xs">
          <p className="text-slate-300">
            Detected Plant <span className="font-mono font-bold text-sky-400">#{plant.id}</span> was classified as{' '}
            <span className="font-bold text-amber-400">{plant.status}</span> with {(plant.confidence * 100).toFixed(0)}% confidence.
          </p>

          <div>
            <label className="text-slate-400 block mb-1.5 font-medium">True Ground Classification:</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setCorrectedClass('crop')}
                className={`py-2 px-3 rounded font-semibold border transition ${
                  correctedClass === 'crop'
                    ? 'bg-emerald-600 text-white border-emerald-500 shadow'
                    : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-750'
                }`}
              >
                CROP
              </button>

              <button
                type="button"
                onClick={() => setCorrectedClass('weed')}
                className={`py-2 px-3 rounded font-semibold border transition ${
                  correctedClass === 'weed'
                    ? 'bg-rose-600 text-white border-rose-500 shadow'
                    : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-750'
                }`}
              >
                WEED
              </button>
            </div>
          </div>

          <p className="text-[11px] text-slate-500 italic">
            This saves the image and corrected bounding box to <code>data/feedback/</code> for active retraining.
          </p>
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-800 pt-3">
          <button onClick={onClose} className="btn btn-secondary text-xs">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitted}
            className="btn btn-primary text-xs"
          >
            {submitted ? <Check className="w-4 h-4 text-emerald-300" /> : <Save className="w-4 h-4" />}
            <span>{submitted ? 'Saved to Feedback!' : 'Save Correction'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
