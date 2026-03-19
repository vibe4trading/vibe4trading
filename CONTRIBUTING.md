# Contributing to Vibe4Trading

## Internationalization (i18n)

This project supports English and Chinese locales using react-i18next. All user-facing strings must be translated.

### Adding New Translatable Strings

1. **Identify the namespace** for your component:
   - `common`: Navigation, buttons, shared UI elements
   - `landing`: Marketing pages
   - `arena`: Arena and leaderboard pages
   - `runs`: Run pages (list, detail, creation)
   - `admin`: Admin interface
   - `errors`: Form validation and error messages

2. **Add keys to both locale files**:
   ```bash
   # English
   vibe4trading-frontend/src/i18n/locales/en/{namespace}.json
   
   # Chinese
   vibe4trading-frontend/src/i18n/locales/zh/{namespace}.json
   ```

3. **Use nested structure** for organization:
   ```json
   {
     "hero": {
       "title": "Welcome to Vibe4Trading",
       "subtitle": "Benchmark AI trading strategies"
     }
   }
   ```

4. **Use the translation** in your component:
   ```tsx
   import { useTranslation } from 'react-i18next';
   
   function MyComponent() {
     const { t } = useTranslation('landing');
     return <h1>{t('hero.title')}</h1>;
   }
   ```

### Translation File Structure

**6 namespaces** organize translations by feature area:

```
src/i18n/locales/
├── en/
│   ├── common.json      # Navigation, buttons, status (29 keys)
│   ├── landing.json     # Marketing copy (128 keys)
│   ├── arena.json       # Arena/leaderboard (123 keys)
│   ├── runs.json        # Runs pages (89 keys)
│   ├── admin.json       # Admin interface (48 keys)
│   └── errors.json      # Error messages (22 keys)
└── zh/
    └── (same structure)
```

**Total: 439 translation keys** across both languages.

### Using Translations in Components

**Basic usage:**
```tsx
const { t } = useTranslation('common');
<button>{t('nav.home')}</button>
```

**With interpolation:**
```tsx
const { t } = useTranslation('common');
<span>{t('profile.quota', { current: 2, total: 3 })}</span>
```

Translation file:
```json
{
  "profile": {
    "quota": "{{current}}/{{total}} runs today"
  }
}
```

**Multiple namespaces:**
```tsx
const { t } = useTranslation(['runs', 'errors']);
<div>
  <h1>{t('runs:page.title')}</h1>
  <p>{t('errors:validation.required')}</p>
</div>
```

### Date and Number Formatting

Use locale-aware formatters from `src/i18n/formatters.ts`:

```tsx
import { useFormatDate, useFormatNumber, useFormatCurrency } from '@/i18n/formatters';

function MetricsCard() {
  const formatDate = useFormatDate();
  const formatNumber = useFormatNumber();
  const formatCurrency = useFormatCurrency();
  
  return (
    <div>
      <p>{formatDate(new Date())}</p>
      {/* English: March 18, 2026 */}
      {/* Chinese: 2026年3月18日 */}
      
      <p>{formatNumber(1234.56)}</p>
      {/* Locale-specific thousand separators */}
      
      <p>{formatCurrency(1234.56, 'USD')}</p>
      {/* English: $1,234.56 */}
      {/* Chinese: ¥1,234.56 (when currency='CNY') */}
    </div>
  );
}
```

### CI Translation Coverage

The CI pipeline runs `scripts/check-i18n-coverage.js` to enforce 100% key coverage between English and Chinese.

**How it works:**
- Compares all 6 namespaces between `en/` and `zh/`
- Recursively flattens nested keys (e.g., `hero.title`, `profile.quota`)
- Fails build if any keys are missing in Chinese translations

**Fixing coverage failures:**

```bash
# Run the check locally
cd vibe4trading-frontend
node scripts/check-i18n-coverage.js

# Example output:
# ❌ Missing keys in zh:
#   landing.hero.newFeature
#   runs.detail.exportButton
```

**To fix:**
1. Add the missing keys to the appropriate `zh/{namespace}.json` file
2. Provide proper Chinese translations (no placeholders or machine translation markers)
3. Re-run the check to verify

### Backend Error Translation

Backend API errors are automatically translated based on the `Accept-Language` header.

**How it works:**
- Middleware parses `Accept-Language` header (e.g., `zh-CN,zh;q=0.9,en;q=0.8`)
- Stores locale in `request.state.locale`
- Validation errors use translations from `vibe4trading-backend/src/v4t/i18n/locales/{en,zh}.json`

**Error translation structure:**
```json
{
  "errors": {
    "http": {
      "401": "Unauthorized",
      "404": "Not Found"
    },
    "pydantic": {
      "missing": "Field is required",
      "string_type": "Input should be a valid string"
    }
  }
}
```

**Frontend receives translated errors:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "model_key"],
      "msg": "字段必填",
      "input": null
    }
  ]
}
```

### Language Switcher

The language switcher in the header toggles between English and Chinese.

**Persistence priority:**
1. User profile (if logged in)
2. localStorage (`i18nextLng`)
3. Browser language

**How it works:**
- Click toggles `i18n.changeLanguage('en' | 'zh')`
- Saves to localStorage immediately
- Saves to user profile via `PATCH /api/me/preferences` (if authenticated)
- Updates `document.documentElement.lang` for CSS `:lang()` selectors

### Translation Guidelines

**DO:**
- Add keys to both `en/` and `zh/` files simultaneously
- Use nested structure for related keys
- Keep technical identifiers in English (e.g., model keys, API endpoints)
- Use interpolation for dynamic content
- Test both locales before committing

**DON'T:**
- Leave placeholder text like "TODO", "TBD", or "机器翻译"
- Use machine translation without review
- Hardcode strings in components
- Skip CI coverage checks
- Translate brand names ("Vibe4Trading", "WEB4")

### Quick Reference

**Add a new translation in under 2 minutes:**

1. Open both locale files:
   ```bash
   # English
   src/i18n/locales/en/common.json
   
   # Chinese
   src/i18n/locales/zh/common.json
   ```

2. Add the same key to both files:
   ```json
   // en/common.json
   { "newFeature": { "title": "New Feature" } }
   
   // zh/common.json
   { "newFeature": { "title": "新功能" } }
   ```

3. Use in component:
   ```tsx
   const { t } = useTranslation('common');
   <h2>{t('newFeature.title')}</h2>
   ```

4. Verify coverage:
   ```bash
   node scripts/check-i18n-coverage.js
   ```

Done.
