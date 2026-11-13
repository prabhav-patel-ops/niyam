# Install Niyam on iPhone

1. Open https://prabhav-patel-ops.github.io/niyam/ in **Safari**.
2. Tap **Share**, then **Add to Home Screen**. Depending on your Safari layout, Share may be under its menu.
3. Leave **Open as Web App** enabled if offered, then tap **Add**.
4. Open **Niyam** from the home screen. It opens in a standalone window with a mobile tab bar.

This is an installable web app, not an App Store application. No Apple developer account or paid subscription is needed. Its Install app button shows the same Safari instructions because iPhone does not expose Android's automatic install prompt.

The current app is the frontend review edition. All reports, signals, coverage and portfolio values are synthetic interface samples. It does not contact an AI provider, Yahoo, a broker or the local backend. Editing rules does not calculate results. Review-session changes reset on reload.

After the first online visit finishes downloading the app shell, the install card says **Ready for offline review**. The sample studio, toolbox, reports and paper screens are then available offline. iOS can reclaim website storage, so reopen online if an offline launch is unavailable. Future versions show an **Update app** action once their complete shell has downloaded.

Only public frontend assets are cached, under the Niyam Pages path. API requests, private market files, account data and other applications' caches are excluded. The normal local-backend build does not register this service worker.

Verification: `node tests/pwa.cjs` checks the manifest, icon files, offline navigation and asset fallback, iPhone install guidance, cache-update isolation and private-data exclusions. This is supplemented by a browser check of the deployed installation UI. Actual addition to an iPhone home screen must be completed on that device.
