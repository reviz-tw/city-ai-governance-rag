import { FC } from 'react';
import { Sparkles, Database, Scale, BookOpen, ExternalLink, ShieldCheck } from 'lucide-react';

interface HeaderProps {
  activeTab: 'chat' | 'documents' | 'cruxes';
  onSelectTab: (tab: 'chat' | 'documents' | 'cruxes') => void;
  documentCount: number;
}

export const Header: FC<HeaderProps> = ({
  activeTab,
  onSelectTab,
  documentCount
}) => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-sky-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-bold text-slate-900 tracking-tight">
                  台北市與全球城市 AI 治理顧問系統
                </h1>
                <span className="hidden md:inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-sky-100 text-sky-800 border border-sky-200">
                  Topos Edition
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">
                基於 Vertex AI Search 政策檢索與首長/專家訪談逐字稿分析
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center space-x-1 sm:space-x-2 bg-slate-100 p-1 rounded-lg">
            <button
              onClick={() => onSelectTab('chat')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition-all ${
                activeTab === 'chat'
                  ? 'bg-white text-sky-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              <span>AI 政策顧問</span>
            </button>

            <button
              onClick={() => onSelectTab('documents')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition-all ${
                activeTab === 'documents'
                  ? 'bg-white text-sky-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              <span>政策文獻庫 ({documentCount})</span>
            </button>

            <button
              onClick={() => onSelectTab('cruxes')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition-all ${
                activeTab === 'cruxes'
                  ? 'bg-white text-sky-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              <Scale className="w-4 h-4" />
              <span>核心爭點矩陣</span>
            </button>
          </nav>

          {/* Right Links / Status */}
          <div className="hidden lg:flex items-center space-x-3 text-xs text-slate-500">
            <div className="flex items-center space-x-1.5 bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-full border border-emerald-200">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Vertex AI Search 正常</span>
            </div>
            <a
              href="/admin"
              target="_blank"
              rel="noreferrer"
              className="flex items-center space-x-1 text-slate-600 hover:text-sky-600 transition-colors"
              title="檢視切片與資料庫管理"
            >
              <Database className="w-3.5 h-3.5" />
              <span>管理端</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>
    </header>
  );
};
