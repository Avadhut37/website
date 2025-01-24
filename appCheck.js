import { initializeAppCheck, ReCaptchaV3Provider } from "firebase/app-check";
import app from './config.js';

export function initializeAppCheck() {
  const appCheck = initializeAppCheck(app, {
    provider: new ReCaptchaV3Provider('6LdRUMEqAAAAABd_BW_zNoX8GHAukNjdq6B4uct0'),
    isTokenAutoRefreshEnabled: true
  });
  return appCheck;
}
