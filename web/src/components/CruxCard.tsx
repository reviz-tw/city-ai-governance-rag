import { useState, FC } from 'react';
import { Crux } from '../types';
import { CheckCircle2, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';

interface CruxCardProps {
  crux: Crux;
  index: number;
}

export const CruxCard: FC<CruxCardProps> = ({ crux, index }) => {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:shadow transition-shadow">
      <div 
        className="flex items-start justify-between cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center space-x-2.5">
          <span className="flex items-center justify-center w-6 h-6 rounded-full bg-sky-100 text-sky-800 text-xs font-bold">
            {index + 1}
          </span>
          <h4 className="font-semibold text-slate-900 text-sm sm:text-base">
            {crux.title}
          </h4>
        </div>
        <button className="text-slate-400 hover:text-slate-600 p-1">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      <p className="text-xs sm:text-sm text-slate-600 mt-2 mb-3 leading-relaxed">
        {crux.description}
      </p>

      {expanded && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-100">
          {/* 積極/推動觀點 */}
          <div className="bg-emerald-50/70 border border-emerald-200/80 rounded-lg p-3">
            <div className="flex items-center space-x-1.5 text-emerald-800 font-semibold text-xs mb-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>推動效益與支持視角</span>
            </div>
            <ul className="space-y-1.5">
              {crux.proPoints.map((point, i) => (
                <li key={i} className="text-xs text-slate-700 flex items-start space-x-1.5">
                  <span className="text-emerald-500 font-bold">•</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* 挑戰/顧慮觀點 */}
          <div className="bg-amber-50/70 border border-amber-200/80 rounded-lg p-3">
            <div className="flex items-center space-x-1.5 text-amber-800 font-semibold text-xs mb-2">
              <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
              <span>實務挑戰與風險顧慮</span>
            </div>
            <ul className="space-y-1.5">
              {crux.conPoints.map((point, i) => (
                <li key={i} className="text-xs text-slate-700 flex items-start space-x-1.5">
                  <span className="text-amber-500 font-bold">•</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};
