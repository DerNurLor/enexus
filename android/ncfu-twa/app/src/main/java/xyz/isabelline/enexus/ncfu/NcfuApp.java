package xyz.isabelline.enexus.ncfu;

import android.app.Application;
import android.webkit.WebView;

public class NcfuApp extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        // Предзагружаем WebView движок при старте приложения в фоновом потоке.
        // Это устраняет 10-15 секунд инициализации Chromium при первом открытии экрана.
        new Thread(() -> {
            try {
                new WebView(getApplicationContext()).destroy();
            } catch (Exception ignored) {}
        }).start();
    }
}
