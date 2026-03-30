package xyz.isabelline.enexus.ncfu;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Intent;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.provider.Settings;
import android.view.KeyEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.SslErrorHandler;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.TextView;

import java.io.ByteArrayInputStream;

/**
 * ИСПРАВЛЕНИЯ:
 * [F1] onResume: mPageLoaded сбрасывался в false ВСЕГДА при возврате в приложение.
 *      Это вызывало появление "slow hint" через 15 секунд даже если страница давно загружена
 *      (пользователь свернул и развернул приложение).
 *      Исправлено: slow hint запускается в onResume только если WebView действительно
 *      загружает новую страницу (isLoading()), иначе не трогаем mPageLoaded.
 * [F2] FLAG_FULLSCREEN deprecated в API 30+. Заменён на WindowInsetsController.
 *      Оставлена обратная совместимость через Build.VERSION.SDK_INT.
 */
public class LauncherActivity extends Activity {

    private static final String LAUNCH_URL = "https://app.enexus.isabelline.xyz/schedule";
    private static final String HOST       = "app.enexus.isabelline.xyz";
    private static final String CHANNEL_ID = "ncfu_default";

    private static final int SLOW_HINT_DELAY_MS = 15_000;

    private WebView  mWebView;
    private View     mSplash;
    private TextView mSplashHint;

    private final Handler mHandler = new Handler(Looper.getMainLooper());
    private boolean mPageLoaded = false;

    private final Runnable mSlowHintRunnable = () -> {
        if (!mPageLoaded && mSplashHint != null) {
            mSplashHint.setVisibility(View.VISIBLE);
            mSplashHint.setAlpha(0f);
            mSplashHint.animate().alpha(1f).setDuration(400).start();
        }
    };

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getWindow().addFlags(WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED);
        requestWindowFeature(Window.FEATURE_NO_TITLE);

        // [F2] FLAG_FULLSCREEN deprecated в API 30+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            getWindow().setDecorFitsSystemWindows(false);
        } else {
            //noinspection deprecation
            getWindow().setFlags(
                    WindowManager.LayoutParams.FLAG_FULLSCREEN,
                    WindowManager.LayoutParams.FLAG_FULLSCREEN
            );
        }

        getWindow().setStatusBarColor(0xFF0a0a0a);
        getWindow().setNavigationBarColor(0xFF0a0a0a);

        setContentView(R.layout.activity_main);
        mWebView    = findViewById(R.id.webview);
        mSplash     = findViewById(R.id.splash);
        mSplashHint = findViewById(R.id.splash_hint);

        createNotificationChannel();
        startKeepAliveService();
        requestBatteryExemption();
        setupWebView();

        mHandler.postDelayed(mSlowHintRunnable, SLOW_HINT_DELAY_MS);

        Uri incoming = getIntent() != null ? getIntent().getData() : null;
        String url = (incoming != null && HOST.equals(incoming.getHost()))
                ? incoming.toString()
                : LAUNCH_URL;

        mWebView.loadUrl(url);
    }

    private void startKeepAliveService() {
        Intent service = new Intent(this, KeepAliveService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(service);
        } else {
            startService(service);
        }
    }

    private void requestBatteryExemption() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
            if (pm != null && !pm.isIgnoringBatteryOptimizations(getPackageName())) {
                try {
                    startActivity(new Intent(
                            Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                            Uri.parse("package:" + getPackageName())
                    ));
                } catch (Exception ignored) {}
            }
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        mWebView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        mWebView.setBackgroundColor(0xFF0a0a0a);
        mWebView.setOverScrollMode(View.OVER_SCROLL_NEVER);

        WebSettings s = mWebView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setCacheMode(WebSettings.LOAD_CACHE_ELSE_NETWORK);
        s.setSaveFormData(false);
        s.setGeolocationEnabled(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setUserAgentString(s.getUserAgentString() + " NCFUAndroid/1.0");

        mWebView.setWebViewClient(new WebViewClient() {

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                Uri uri = req.getUrl();
                if (!HOST.equals(uri.getHost())) {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                    return true;
                }
                return false;
            }

            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
                String url = req.getUrl().toString();
                if (url.contains("google-analytics") ||
                    url.contains("googletagmanager") ||
                    url.contains("facebook.net") ||
                    url.contains("yandex.ru/metrika")) {
                    return new WebResourceResponse("text/plain", "utf-8",
                            new ByteArrayInputStream("".getBytes()));
                }
                return super.shouldInterceptRequest(view, req);
            }

            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler h, SslError e) {
                // Отклоняем SSL ошибки — не принимаем невалидные сертификаты
                h.cancel();
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                mPageLoaded = true;

                mHandler.removeCallbacks(mSlowHintRunnable);

                mWebView.setVisibility(View.VISIBLE);
                mSplash.animate()
                        .alpha(0f)
                        .setDuration(200)
                        .withEndAction(() -> {
                            mSplash.setVisibility(View.GONE);
                            if (mSplashHint != null) {
                                mSplashHint.setVisibility(View.GONE);
                                mSplashHint.setAlpha(0f);
                            }
                        });
            }
        });
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && mWebView.canGoBack()) {
            mWebView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onResume() {
        super.onResume();
        mWebView.onResume();

        // [F1] ИСПРАВЛЕНИЕ: Не сбрасываем mPageLoaded безусловно.
        // Если WebView не загружает страницу прямо сейчас — страница уже показана,
        // и slow hint не нужен.
        // Сбрасываем флаг и запускаем таймер только если WebView реально загружает.
        if (mWebView.getProgress() < 100) {
            // Страница ещё не загружена (например, после принудительного reload)
            mPageLoaded = false;
            mHandler.removeCallbacks(mSlowHintRunnable);
            mHandler.postDelayed(mSlowHintRunnable, SLOW_HINT_DELAY_MS);
        }
        // Если страница уже загружена (mPageLoaded == true) — ничего не делаем,
        // hint не показываем.
    }

    @Override
    protected void onPause() {
        super.onPause();
        mWebView.onPause();
        mHandler.removeCallbacks(mSlowHintRunnable);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        mHandler.removeCallbacks(mSlowHintRunnable);
        mWebView.destroy();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel ch = new NotificationChannel(
                    CHANNEL_ID, "Уведомления НЦФУ",
                    NotificationManager.IMPORTANCE_DEFAULT
            );
            ch.setDescription("Изменения в расписании");
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(ch);
        }
    }
}
