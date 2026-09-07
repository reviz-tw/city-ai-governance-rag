import { FC } from 'react';
import { Sparkles, ShieldCheck } from 'lucide-react';

interface HeaderProps {
  documentCount: number;
}

export const Header: FC<HeaderProps> = ({ documentCount }) => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-sky-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
                  台北市 AI 治理政策顧問系統
                </h1>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-sky-100 text-sky-800 border border-sky-200">
                  AI Advisor
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">
                基於 Vertex AI Search 政策檢索與首長/專家訪談逐字稿分析
              </p>
            </div>
          </div>

          {/* Right Status Indicator */}
          <div className="flex items-center space-x-2.5 text-xs">
            <span className="hidden sm:inline-flex items-center px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 font-medium">
              📚 已載入 {documentCount} 份政策與訪談文獻
            </span>
            <div className="flex items-center space-x-1.5 bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-full border border-emerald-200 font-medium">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>線上即時問答</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
