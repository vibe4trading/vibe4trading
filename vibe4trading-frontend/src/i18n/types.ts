import common from './locales/en/common.json';
import landing from './locales/en/landing.json';
import arena from './locales/en/arena.json';
import runs from './locales/en/runs.json';
import admin from './locales/en/admin.json';
import errors from './locales/en/errors.json';
import commonZh from './locales/zh/common.json';
import landingZh from './locales/zh/landing.json';
import arenaZh from './locales/zh/arena.json';
import runsZh from './locales/zh/runs.json';
import adminZh from './locales/zh/admin.json';
import errorsZh from './locales/zh/errors.json';

export const resources = {
  en: {
    common,
    landing,
    arena,
    runs,
    admin,
    errors,
  },
  zh: {
    common: commonZh,
    landing: landingZh,
    arena: arenaZh,
    runs: runsZh,
    admin: adminZh,
    errors: errorsZh,
  },
} as const;
