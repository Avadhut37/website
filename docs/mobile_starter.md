# Mobile Starter (Expo React Native)

1. `npx expo init istudiox-mobile` → choose **Managed / blank (TypeScript)** template.
2. Organize code:
   - `screens/` for main views.
   - `components/` for reusable UI (Button, Input, Modal, Card).
   - `services/api.ts` sharing the same API client as the web frontend.
3. Install deps:
   ```bash
   cd istudiox-mobile
   npm install axios @tanstack/react-query
   npm install --save-dev eslint @react-native/eslint-config
   ```
4. API client reuse:
   - Export axios instance from `packages/api-client` or copy from web `src/services/api.js`.
   - Use React Query hooks to mirror desktop behavior.
5. Preview flow:
   - `npx expo start` to launch Metro and QR code.
   - Provide preview QR inside the Builder UI for quick device testing.
6. Deployment:
   - Use Expo Application Services (EAS) for OTA updates.
   - Tie into Deploy Agent so previews push to Expo automatically after Build Agent success.
