// i18n.js
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import translationEn from './locales/en.json';
import translationKo from './locales/ko.json';

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        translation: translationEn,
      },
      ko: {
        translation: translationKo,
      },
    },
    lng: 'en', // 초기 언어 설정
    fallbackLng: 'en', // 번역 텍스트가 없을 경우 대체할 언어
    interpolation: { escapeValue: false },
  });

export default i18n;
