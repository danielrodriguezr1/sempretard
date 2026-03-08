import { useEffect, useRef } from "react";

/**
 * AdMob integration via @capacitor-community/admob.
 * Only runs on native (Capacitor). Does nothing on web.
 *
 * Replace TEST_BANNER_ID with your real ad unit IDs before publishing.
 */

const TEST_BANNER_ID = "ca-app-pub-3940256099942544/6300978111"; // Google test banner

let initialized = false;

export function useAdMobBanner() {
  const shown = useRef(false);

  useEffect(() => {
    if (shown.current) return;
    if (!(window as any).Capacitor?.isNativePlatform()) return;

    (async () => {
      try {
        const { AdMob, BannerAdSize, BannerAdPosition } = await import(
          "@capacitor-community/admob"
        );

        if (!initialized) {
          await AdMob.initialize({
            initializeForTesting: true, // Set false for production
          });
          initialized = true;
        }

        await AdMob.showBanner({
          adId: TEST_BANNER_ID,
          adSize: BannerAdSize.ADAPTIVE_BANNER,
          position: BannerAdPosition.BOTTOM_CENTER,
          isTesting: true, // Set false for production
        });

        shown.current = true;
      } catch (e) {
        console.warn("AdMob banner failed:", e);
      }
    })();

    return () => {
      if (shown.current) {
        import("@capacitor-community/admob").then(({ AdMob }) => {
          AdMob.removeBanner().catch(() => {});
        });
      }
    };
  }, []);
}
