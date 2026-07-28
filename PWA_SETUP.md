# PathCare PWA Setup Guide

Your Django project has been configured as a Progressive Web App (PWA). Here's what has been implemented and what you need to do next.

## ✅ What's Been Done

### 1. **Service Worker** (`tracking/static/service-worker.js`)
   - Caches static assets (CSS, JS, images)
   - Implements network-first strategy for API calls
   - Provides offline fallback page
   - Auto-caches successful responses for offline use

### 2. **Web App Manifest** (`tracking/static/manifest.json`)
   - Defines app metadata (name, description, icons, theme colors)
   - Enables "Add to Home Screen" feature
   - Configures standalone display mode
   - Specifies theme and background colors

### 3. **Offline Page** (`templates/offline.html`)
   - Beautiful offline experience for users
   - Auto-reloads when connection is restored
   - Professional design with PathCare branding

### 4. **Base Template Updates** (`tracking/templates/tracking/base.html`)
   - Added PWA meta tags for iOS support
   - Added manifest link
   - Registered service worker on page load

### 5. **Django Settings** (`pathcare/settings.py`)
   - Configured static files for production
   - Added security headers for PWA (CSP, SSL, etc.)
   - Set up STATIC_ROOT for deployment

### 6. **URLs & Views** (`pathcare/urls.py`, `pathcare/pwa_views.py`)
   - Routes for offline page and manifest.json
   - Proper content-type headers for PWA files

---

## 🎨 Next Steps: Adding App Icons

The manifest expects icon files in `tracking/static/icons/`. You need to generate these sizes:

- 72x72 (`icon-72x72.png`)
- 96x96 (`icon-96x96.png`)
- 128x128 (`icon-128x128.png`)
- 144x144 (`icon-144x144.png`)
- 152x152 (`icon-152x152.png`)
- 192x192 (`icon-192x192.png`) - Required
- 384x384 (`icon-384x384.png`)
- 512x512 (`icon-512x512.png`) - Required
- 180x180 (`icon-180x180.png`) - For iOS
- Screenshots (540x720) - Optional

### Tools to Generate Icons:
1. **Free Online**: https://www.favicon-generator.org/ (Upload logo → generates all sizes)
2. **PWA Builder**: https://www.pwabuilder.com/ (Upload image, downloads all assets)
3. **imagemagick** (CLI):
   ```bash
   convert logo.png -resize 192x192 icon-192x192.png
   ```

### Recommended Approach:
1. Create/prepare a 512x512 PNG logo for PathCare
2. Use https://www.pwabuilder.com/ to generate all icon sizes
3. Download the icons
4. Place them in `tracking/static/icons/`

---

## 🚀 Deployment Checklist

Before deploying to production:

- [ ] Update `manifest.json` with correct app name, description, and colors
- [ ] Generate and add all required app icons (192x192 & 512x512 minimum)
- [ ] Update `settings.py`:
  - [ ] Set `DEBUG = False`
  - [ ] Update `ALLOWED_HOSTS`
  - [ ] Set `SECRET_KEY` to a strong random value
  - [ ] Configure proper database (PostgreSQL recommended)
  - [ ] Enable HTTPS (required for service workers)
- [ ] Run `python manage.py collectstatic` to gather all static files
- [ ] Test PWA features in Chrome DevTools:
  - [ ] Lighthouse audit
  - [ ] Service Worker registration
  - [ ] Offline functionality
  - [ ] "Add to Home Screen" prompt

---

## 🧪 Testing Your PWA

### In Development:
```bash
python manage.py runserver
```

### Chrome/Edge:
1. Open DevTools (F12)
2. Go to **Application** tab
3. Check **Service Workers** - should show your registered worker
4. Check **Manifest** - should display your manifest.json
5. Test offline: DevTools → Network → Offline checkbox
6. Test "Add to Home Screen": DevTools → more tools → Add to Home Screen

### Firefox:
1. about:debugging → This Firefox
2. Check Service Workers section
3. "Install" your app from Firefox menu

---

## 📱 Testing on Real Devices

### Android:
1. Open Chrome
2. Navigate to your app URL
3. Tap menu (⋮) → "Install app"
4. Tap the app from home screen

### iOS:
1. Open Safari
2. Navigate to your app URL
3. Tap Share button
4. Tap "Add to Home Screen"
5. Tap app from home screen (doesn't use service worker, but caches main page)

---

## 🔒 Security Notes

- Service worker only works over **HTTPS** (except localhost for development)
- CSP headers restrict loading external resources
- Update Content-Security-Policy in settings.py if adding external APIs
- Keep service worker code secure - it has access to user data

---

## 📝 Customization

### Change Theme Color:
Edit in `base.html` and `manifest.json`:
```json
"theme_color": "#1e3a8a"  // Change hex color
```

### Add More Offline Features:
Edit `service-worker.js` to cache more pages and add sync APIs.

### Update Cache Strategy:
- Currently: Cache-first for static assets, Network-first for API
- Modify `fetch` event listener in `service-worker.js` to adjust

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Service Worker not registering | Check browser console for errors; ensure HTTPS in production |
| Offline page not showing | Verify `offline.html` path in service-worker.js |
| Icons not displaying | Check file paths; ensure icons are in correct directory |
| "Add to Home Screen" not appearing | Run Lighthouse audit; may need https + valid manifest |
| App works but looks broken | Clear cache in DevTools Application tab and reload |

---

## 📚 Resources

- [MDN PWA Docs](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps)
- [Google PWA Checklist](https://web.dev/pwa-checklist/)
- [Web.dev PWA Learning Path](https://web.dev/progressive-web-apps/)

---

You're all set! Your Django app is now a PWA. Next, add your app icons and test in Chrome DevTools! 🎉
