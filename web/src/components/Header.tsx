import { FC, ChangeEvent } from 'react';
import { BookOpen, Check, Globe } from 'lucide-react';
import { LanguageCode } from '../types';
import { UIStrings } from '../i18n';

interface HeaderProps {
  t: UIStrings;
  lang: LanguageCode;
  onLangChange: (newLang: LanguageCode) => void;
  documentCount?: number;
}

export const Header: FC<HeaderProps> = ({ t, lang, onLangChange, documentCount }) => {
  const handleSelectChange = (e: ChangeEvent<HTMLSelectElement>) => {
    onLangChange(e.target.value as LanguageCode);
  };

  // Format doc count if dynamic count available
  const docText = documentCount && documentCount !== 22
    ? t.docCount.replace(/\d+/, documentCount.toString())
    : t.docCount;

  return (
    <header
      className="flex-none flex items-center gap-3 px-5 border-b border-[var(--color-neutral-200)] bg-[var(--color-bg)] sticky top-0 z-30"
      style={{ height: '68px' }}
    >
      {/* TFD & AI Governance Logo Emblem */}
      <div className="flex-none flex items-center justify-center">
        <div
          className="w-[38px] h-[38px] rounded-[10px] bg-gradient-to-br from-[#c67139] to-[#8c491a] shadow-sm flex items-center justify-center text-white relative overflow-hidden"
          title="台灣民主基金會 • AI 治理政策顧問"
        >
          {/* Stylized Emblem SVG */}
          <svg className="w-5 h-5 text-amber-100" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
          <div className="absolute inset-0 bg-white/10 pointer-events-none" />
        </div>
      </div>

      {/* Brand & Subtitle */}
      <div className="flex flex-col gap-0.5 select-none">
        <span className="font-heading text-[17px] text-[var(--color-text)] leading-tight">
          {t.brand}
        </span>
        <span className="font-body font-normal text-[12px] text-[var(--color-neutral-600)] leading-tight">
          {t.brandSub}
        </span>
      </div>

      {/* Right Controls */}
      <div className="ml-auto flex items-center gap-3">
        {/* Document Count Tag */}
        <div className="tag tag-accent-2 hidden sm:inline-flex gap-1.5 py-1 px-3">
          <BookOpen className="w-3.5 h-3.5 flex-none" />
          <span>{docText}</span>
        </div>

        {/* Live Q&A Tag */}
        <div className="tag tag-accent inline-flex gap-1.5 py-1 px-3">
          <Check className="w-3.5 h-3.5 flex-none stroke-[2.75]" />
          <span>{t.liveTag}</span>
        </div>

        {/* Language Selector */}
        <div className="flex-none flex items-center gap-1.5 ml-1">
          <Globe className="w-4 h-4 text-[var(--color-neutral-600)] flex-none" />
          <select
            className="input text-xs cursor-pointer"
            value={lang}
            onChange={handleSelectChange}
            style={{
              width: 'auto',
              minHeight: '34px',
              padding: '4px 28px 4px 12px',
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-divider)',
              color: 'var(--color-text)'
            }}
            aria-label="選擇介面語言"
          >
            <option value="zh">中文 (Chinese)</option>
            <option value="en">English</option>
            <option value="ja">日本語 (Japanese)</option>
            <option value="fr">Français (French)</option>
            <option value="es">Español (Spanish)</option>
            <option value="ru">Русский (Russian)</option>
            <option value="ar">العربية (Arabic)</option>
          </select>
        </div>
      </div>
    </header>
  );
};
