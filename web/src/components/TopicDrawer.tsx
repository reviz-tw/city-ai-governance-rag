import { FC, useState } from 'react';
import {
  Phone,
  ShieldCheck,
  Users,
  Leaf,
  Layers,
  FlaskConical,
  ChevronDown,
  X
} from 'lucide-react';
import { Topic, Crux } from '../types';
import { UIStrings } from '../i18n';

interface TopicDrawerProps {
  t: UIStrings;
  topics: Topic[];
  selectedTopicId: string;
  onSelectTopic: (id: string) => void;
  isOpen: boolean;
  activeTab: 'topics' | 'analysis';
  onTabChange: (tab: 'topics' | 'analysis') => void;
  onClose: () => void;
}

export const TopicDrawer: FC<TopicDrawerProps> = ({
  t,
  topics,
  selectedTopicId,
  onSelectTopic,
  isOpen,
  activeTab,
  onTabChange,
  onClose,
}) => {
  const [expandedAnalysisIdx, setExpandedAnalysisIdx] = useState<number | null>(0);

  const selectedTopic = topics.find((tp) => tp.id === selectedTopicId) || topics[0];
  const cruxes = selectedTopic?.keyCruxes || [];

  const toggleAnalysis = (idx: number) => {
    setExpandedAnalysisIdx((prev) => (prev === idx ? null : idx));
  };

  const renderTopicIcon = (iconType?: string, id?: string) => {
    if (iconType === 'phone' || id?.includes('1999')) {
      return <Phone className="w-4 h-4" />;
    }
    if (iconType === 'shield' || id?.includes('guideline')) {
      return <ShieldCheck className="w-4 h-4" />;
    }
    if (iconType === 'users' || id?.includes('bureau')) {
      return <Users className="w-4 h-4" />;
    }
    return <Leaf className="w-4 h-4" />;
  };

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="absolute inset-0 left-[84px] bg-[#201e1d]/30 backdrop-blur-[1px] z-15 transition-opacity"
          aria-label={t.drawerCloseLabel}
        />
      )}

      {/* Drawer Panel */}
      <div
        className={`absolute top-0 left-[84px] bottom-0 w-[min(440px,88vw)] bg-[var(--color-bg)] border-r border-[var(--color-neutral-200)] shadow-[var(--shadow-lg)] z-20 transition-all duration-300 ease-in-out flex flex-col ${
          isOpen
            ? 'translate-x-0 opacity-100 pointer-events-auto'
            : '-translate-x-[calc(100%+84px)] opacity-0 pointer-events-none'
        }`}
      >
        {/* Drawer Header: Segmented Toggle & Close */}
        <div className="flex-none flex items-center gap-3 p-4 pb-3 border-b border-[var(--color-neutral-200)]">
          <div className="seg flex-1">
            <button
              type="button"
              onClick={() => onTabChange('topics')}
              className={`seg-opt flex-1 text-center ${activeTab === 'topics' ? 'active' : ''}`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>{t.railTopics}</span>
            </button>
            <button
              type="button"
              onClick={() => onTabChange('analysis')}
              className={`seg-opt flex-1 text-center ${activeTab === 'analysis' ? 'active' : ''}`}
            >
              <FlaskConical className="w-3.5 h-3.5" />
              <span>{t.railAnalysis}</span>
            </button>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="btn btn-icon btn-ghost text-[var(--color-neutral-700)] hover:text-[var(--color-text)]"
            aria-label={t.drawerCloseLabel}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {/* TAB 1: TOPICS */}
          {activeTab === 'topics' && (
            <div className="space-y-3">
              <p className="text-xs text-[var(--color-neutral-600)] mb-1">
                {t.topicsHint}
              </p>

              {topics.map((tp) => {
                const isActive = tp.id === selectedTopicId;
                return (
                  <button
                    key={tp.id}
                    type="button"
                    onClick={() => {
                      onSelectTopic(tp.id);
                      onClose();
                    }}
                    className={`w-full text-left rounded-[var(--radius-lg)] p-4 cursor-pointer font-body flex flex-col gap-2.5 transition-all duration-200 border-2 ${
                      isActive
                        ? 'border-[var(--color-accent)] bg-[var(--color-accent-100)] shadow-xs ring-1 ring-[var(--color-accent)]/20'
                        : 'border-[var(--color-neutral-200)] bg-[var(--color-neutral-100)] hover:border-[var(--color-accent-300)]'
                    }`}
                  >
                    {/* Top Row: Icon + Category Tag + Active Badge */}
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-[34px] h-[34px] rounded-[var(--radius-md)] flex items-center justify-center flex-none text-white shadow-2xs ${
                          isActive
                            ? 'bg-[var(--color-accent)]'
                            : 'bg-[var(--color-neutral-700)]'
                        }`}
                      >
                        {renderTopicIcon(tp.icon, tp.id)}
                      </div>
                      <span className="tag tag-neutral text-[10.5px]">
                        {tp.category}
                      </span>
                      {isActive && (
                        <span className="tag tag-accent ml-auto text-[10.5px]">
                          {t.currentBadge}
                        </span>
                      )}
                    </div>

                    {/* Title */}
                    <div className="font-heading text-[15px] text-[var(--color-text)] leading-snug">
                      {tp.title}
                    </div>

                    {/* Description */}
                    <p className="text-[12.5px] text-[var(--color-neutral-700)] leading-relaxed m-0 line-clamp-3">
                      {tp.description}
                    </p>

                    {/* Tags */}
                    <div className="flex gap-1.5 flex-wrap pt-1">
                      {tp.tags.map((tag, idx) => (
                        <span
                          key={idx}
                          className="tag tag-outline text-[10px] py-0.5 px-2"
                        >
                          {tag.startsWith('#') ? tag : `#${tag}`}
                        </span>
                      ))}
                    </div>

                    {/* Document count */}
                    <div className="text-[11.5px] font-semibold text-[var(--color-accent-700)] pt-1 border-t border-[var(--color-divider)]">
                      {t.docsCountFormatted(tp.documentsCount)}
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* TAB 2: ANALYSIS (CRUXES) */}
          {activeTab === 'analysis' && (
            <div className="space-y-3">
              <div className="mb-2">
                <p className="text-xs text-[var(--color-neutral-600)] m-0">
                  {t.analysisHint}
                </p>
                <div className="mt-1 text-xs font-bold text-[var(--color-accent-700)]">
                  {t.currentTopicLabel}{selectedTopic.title}
                </div>
              </div>

              {cruxes.length === 0 ? (
                <div className="card p-6 text-center text-xs text-[var(--color-neutral-600)]">
                  {t.noCruxText}
                </div>
              ) : (
                cruxes.map((crux: Crux, idx: number) => {
                  const isExpanded = expandedAnalysisIdx === idx;
                  return (
                    <div
                      key={idx}
                      className="card elev-sm p-4 flex flex-col gap-3 bg-[var(--color-surface)] border border-[var(--color-neutral-200)]"
                    >
                      {/* Header Toggle */}
                      <button
                        type="button"
                        onClick={() => toggleAnalysis(idx)}
                        className="flex items-center gap-3 border-none bg-transparent p-0 cursor-pointer text-left font-body w-full"
                      >
                        <span className="w-[26px] h-[26px] rounded-full bg-[var(--color-accent-100)] text-[var(--color-accent-700)] flex items-center justify-center text-xs font-bold flex-none shadow-2xs">
                          {idx + 1}
                        </span>
                        <span className="font-heading text-[14px] text-[var(--color-text)] flex-1 leading-snug">
                          {crux.title}
                        </span>
                        <ChevronDown
                          className={`w-4 h-4 text-[var(--color-neutral-600)] flex-none transition-transform duration-200 ${
                            isExpanded ? 'rotate-180' : ''
                          }`}
                        />
                      </button>

                      {/* Collapsible Content */}
                      {isExpanded && (
                        <div className="flex flex-col gap-3 pt-1 text-xs animate-fade-up">
                          <p className="m-0 text-[12.5px] text-[var(--color-neutral-800)] leading-relaxed">
                            {crux.description}
                          </p>

                          {/* Support / Pro Points */}
                          <div className="bg-[var(--color-accent-2-100)] rounded-[var(--radius-md)] p-3 flex flex-col gap-1.5 border border-[var(--color-accent-2-300)]">
                            <span className="text-[11.5px] font-bold text-[var(--color-accent-2-800)]">
                              ✅ {t.supportLabel}
                            </span>
                            <div className="space-y-1">
                              {crux.proPoints.map((pt, pIdx) => (
                                <div
                                  key={pIdx}
                                  className="text-[12px] text-[var(--color-neutral-900)] leading-relaxed flex gap-1.5"
                                >
                                  <span className="text-[var(--color-accent-2-600)] font-bold">•</span>
                                  <span>{pt}</span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Risk / Con Points */}
                          <div className="bg-[var(--color-accent-100)] rounded-[var(--radius-md)] p-3 flex flex-col gap-1.5 border border-[var(--color-accent-300)]">
                            <span className="text-[11.5px] font-bold text-[var(--color-accent-800)]">
                              ⚠️ {t.riskLabel}
                            </span>
                            <div className="space-y-1">
                              {crux.conPoints.map((pt, cIdx) => (
                                <div
                                  key={cIdx}
                                  className="text-[12px] text-[var(--color-neutral-900)] leading-relaxed flex gap-1.5"
                                >
                                  <span className="text-[var(--color-accent-600)] font-bold">•</span>
                                  <span>{pt}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
};
