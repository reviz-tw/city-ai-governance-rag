import React from 'react';
import { Topic } from '../types';
import { PhoneCall, ShieldCheck, Users, Globe2, ChevronRight } from 'lucide-react';

interface TopicSelectorProps {
  topics: Topic[];
  selectedTopicId: string;
  onSelectTopic: (topicId: string) => void;
}

const getTopicIcon = (id: string) => {
  if (id.includes('1999')) return <PhoneCall className="w-5 h-5 text-amber-500" />;
  if (id.includes('guidelines')) return <ShieldCheck className="w-5 h-5 text-sky-500" />;
  if (id.includes('bureau')) return <Users className="w-5 h-5 text-indigo-500" />;
  return <Globe2 className="w-5 h-5 text-emerald-500" />;
};

export const TopicSelector: React.FC<TopicSelectorProps> = ({
  topics,
  selectedTopicId,
  onSelectTopic,
}) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
      {topics.map((t) => {
        const isSelected = t.id === selectedTopicId;
        return (
          <div
            key={t.id}
            onClick={() => onSelectTopic(t.id)}
            className={`cursor-pointer rounded-xl p-4 transition-all duration-200 border text-left relative flex flex-col justify-between ${
              isSelected
                ? 'bg-sky-50/90 border-sky-500 shadow-md ring-2 ring-sky-500/20'
                : 'bg-white border-slate-200 hover:border-sky-300 hover:shadow-sm'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 rounded-lg bg-slate-100/80">
                  {getTopicIcon(t.id)}
                </div>
                <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {t.category}
                </span>
              </div>

              <h3 className="font-bold text-slate-900 text-sm mb-1 leading-snug line-clamp-2">
                {t.title}
              </h3>

              <p className="text-xs text-slate-500 line-clamp-2 mb-3">
                {t.description}
              </p>
            </div>

            <div>
              <div className="flex flex-wrap gap-1 mb-2">
                {t.tags.slice(0, 3).map((tag, idx) => (
                  <span
                    key={idx}
                    className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded"
                  >
                    #{tag}
                  </span>
                ))}
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs font-medium">
                <span className="text-slate-500">
                  📚 {t.documentsCount} 份相關文獻
                </span>
                <span className={`flex items-center text-xs ${isSelected ? 'text-sky-600 font-bold' : 'text-slate-400'}`}>
                  {isSelected ? '焦點專題' : '切換'}
                  <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
