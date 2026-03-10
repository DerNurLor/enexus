/** @type {import('next').NextConfig} */
const withPWA = require('@ducanh2912/next-pwa').default({
  dest: 'public',
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === 'development',
  fallbacks: {
    document: '/offline',
  },
  workboxOptions: {
    runtimeCaching: [
      // Страницы — Network First (показываем кеш если нет сети)
      {
        urlPattern: /^https:\/\/app\.enexus\.isabelline\.xyz\/(schedule|profile)?$/,
        handler: 'NetworkFirst',
        options: {
          cacheName: 'pages-cache',
          networkTimeoutSeconds: 5,
          expiration: { maxEntries: 10, maxAgeSeconds: 7 * 24 * 60 * 60 },
        },
      },
      // API расписания — StaleWhileRevalidate (показываем кеш, обновляем в фоне)
      {
        urlPattern: /\/api\/schedules\/.+\/day/,
        handler: 'StaleWhileRevalidate',
        options: {
          cacheName: 'schedule-api-cache',
          expiration: { maxEntries: 100, maxAgeSeconds: 24 * 60 * 60 },
        },
      },
      // Поиск — NetworkFirst (всегда актуальный)
      {
        urlPattern: /\/api\/search\//,
        handler: 'NetworkFirst',
        options: {
          cacheName: 'search-api-cache',
          networkTimeoutSeconds: 3,
          expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 },
        },
      },
      // Статика Next.js — CacheFirst
      {
        urlPattern: /\/_next\/static\/.*/,
        handler: 'CacheFirst',
        options: {
          cacheName: 'next-static-cache',
          expiration: { maxEntries: 200, maxAgeSeconds: 30 * 24 * 60 * 60 },
        },
      },
      // Шрифты и изображения — CacheFirst
      {
        urlPattern: /\.(png|jpg|jpeg|svg|ico|woff2?|ttf)$/,
        handler: 'CacheFirst',
        options: {
          cacheName: 'assets-cache',
          expiration: { maxEntries: 50, maxAgeSeconds: 30 * 24 * 60 * 60 },
        },
      },
    ],
  },
})

const nextConfig = {
  reactStrictMode: true,
}

module.exports = withPWA(nextConfig)
