package xyz.isabelline.enexus.ncfu;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;

public class KeepAliveService extends Service {

    private static final String CHANNEL_ID = "ncfu_keepalive";
    private static final int    NOTIF_ID   = 2001;

    @Override
    public void onCreate() {
        super.onCreate();
        createChannel();
        startForeground(NOTIF_ID, buildNotification());
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        // START_STICKY — система перезапустит сервис если убьёт
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }

    private void createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel ch = new NotificationChannel(
                    CHANNEL_ID,
                    "eNexus",
                    NotificationManager.IMPORTANCE_MIN // минимальный приоритет — без звука
            );
            ch.setShowBadge(false);
            ch.setSound(null, null);
            ch.enableVibration(false);
            ch.setDescription("Быстрый запуск приложения");
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(ch);
        }
    }

    private Notification buildNotification() {
        // Тап по уведомлению открывает приложение
        Intent open = new Intent(this, LauncherActivity.class);
        PendingIntent pi = PendingIntent.getActivity(
                this, 0, open,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
        );

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            return new Notification.Builder(this, CHANNEL_ID)
                    .setSmallIcon(R.mipmap.ic_launcher)
                    .setContentTitle("eNexus")
                    .setContentText("Расписание НЦФУ — нажмите для открытия")
                    .setContentIntent(pi)
                    .setPriority(Notification.PRIORITY_MIN)
                    .setOngoing(true)
                    .setShowWhen(false)
                    .build();
        } else {
            return new Notification.Builder(this)
                    .setSmallIcon(R.mipmap.ic_launcher)
                    .setContentTitle("eNexus")
                    .setContentText("Расписание НЦФУ")
                    .setContentIntent(pi)
                    .setPriority(Notification.PRIORITY_MIN)
                    .setOngoing(true)
                    .build();
        }
    }
}
