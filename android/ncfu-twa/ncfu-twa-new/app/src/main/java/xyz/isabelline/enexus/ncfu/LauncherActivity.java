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
import android.view.KeyEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.SslErrorHandler;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class LauncherActivity extends Activity {

    private static final String LAUNCH_URL = "https://app.enexus.isabelline.xyz/schedule";
    private static final String HOST       = "app.enexus.isabelline.xyz";
    private static final String CHANNEL_ID = "ncfu_default";

    private WebView mWebView;
    private View    mSplash;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // ── Полноэкранный режим ──────────────────────────────────────────────
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(
                WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN
        );
        getWindow().setStatusBarColor(0xFF0a0a0a);
        getWindow().setNavigationBarColor(0xFF0a0a0a);

        setContentView(R.layout.activity_main);

        mWebView = findViewById(R.id.webview);
        mSplash  = findViewById(R.id.splash);

        // ── Канал push-уведомлений (Android 8+) ─────────────────────────────
        createNotificationChannel();

        // ── Настройки WebView для максимальной скорости ──────────────────────
        WebSettings s = mWebView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

        // Агрессивное кэширование — главный способ ускорения
        s.setCacheMode(WebSettings.LOAD_CACHE_ELSE_NETWORK);
        s.setDatabaseEnabled(true);
        s.setAppCacheEnabled(true);

        // Предзагрузка DNS и соединений
        s.setBlockNetworkImage(false);

        // Отключаем лишнее
        s.setSaveFormData(false);
        s.setSavePassword(false);
        s.setGeolocationEnabled(false);

        // User-Agent: добавляем метку для аналитики
        String ua = s.getUserAgentString();
        s.setUserAgentString(ua + " NCFUAndroid/1.0");

        mWebView.setBackgroundColor(0xFF0a0a0a);
        mWebView.setOverScrollMode(View.OVER_SCROLL_NEVER);

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
            public void onReceivedSslError(WebView view, SslErrorHandler h, SslError e) {
                h.cancel(); // Только валидный сертификат
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                // Скрываем сплэш после загрузки страницы
                mSplash.animate()
                        .alpha(0f)
                        .setDuration(250)
                        .withEndAction(() -> mSplash.setVisibility(View.GONE));
                mWebView.setVisibility(View.VISIBLE);
            }
        });

        // ── Deep link или обычный запуск ─────────────────────────────────────
        Uri incoming = getIntent() != null ? getIntent().getData() : null;
        String url = (incoming != null && HOST.equals(incoming.getHost()))
                ? incoming.toString()
                : LAUNCH_URL;

        mWebView.loadUrl(url);
    }

    // ── Кнопка назад — навигация внутри WebView ──────────────────────────────
    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && mWebView.canGoBack()) {
            mWebView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    // ── Жизненный цикл ───────────────────────────────────────────────────────
    @Override protected void onResume()  { super.onResume();  mWebView.onResume(); }
    @Override protected void onPause()   { super.onPause();   mWebView.onPause(); }
    @Override protected void onDestroy() { super.onDestroy(); mWebView.destroy(); }

    // ── Канал уведомлений ────────────────────────────────────────────────────
    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Уведомления НЦФУ",
                    NotificationManager.IMPORTANCE_DEFAULT
            );
            channel.setDescription("Изменения в расписании и важные новости");
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(channel);
        }
    }
}
