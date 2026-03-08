import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.sempretard.app',
  appName: 'SempreTard',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
  plugins: {
    AdMob: {
      // Replace with your real AdMob app IDs before publishing
      androidAppId: 'ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY',
      iosAppId: 'ca-app-pub-XXXXXXXXXXXXXXXX~ZZZZZZZZZZ',
    },
  },
  ios: {
    contentInset: 'automatic',
    backgroundColor: '#F4F1F8',
  },
  android: {
    backgroundColor: '#F4F1F8',
  },
};

export default config;
