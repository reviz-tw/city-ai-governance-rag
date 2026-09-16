export const CONTENT_LANGUAGES = {'zh-TW': '繁體中文', 'zh-CN': '简体中文', en: 'English', ja: '日本語', fr: 'Français', es: 'Español', ru: 'Русский', ko: '한국어', de: 'Deutsch'};
export type InterfaceLanguage = 'zh' | 'en' | 'ja' | 'fr' | 'es' | 'ru';
export const INTERFACE_LANGUAGES = {zh: '中文', en: 'English', ja: '日本語', fr: 'Français', es: 'Español', ru: 'Русский'};
export function normalizeInterfaceLanguage(value: string | null): InterfaceLanguage {
  if (!value) return 'zh';
  const code = value.toLowerCase().split(/[-_]/)[0];
  return code in INTERFACE_LANGUAGES ? code as InterfaceLanguage : 'en';
}
