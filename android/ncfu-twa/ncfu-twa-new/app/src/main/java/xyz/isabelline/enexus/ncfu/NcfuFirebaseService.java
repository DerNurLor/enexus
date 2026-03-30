package xyz.isabelline.enexus.ncfu;

import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.media.RingtoneManager;
import android.net.Uri;

import androidx.core.app.NotificationCompat;

import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

/**
 * Firebase Cloud Messaging сервис.
 *
 * Получает push-уведомления (например, об изменении расписания)
 * и показывает их в трее Android.
 *
 * Для отправки уведомлений со стороны сервера используй Firebase Admin SDK
 * или HTTP v1 API: https://firebase.google.com/docs/cloud-messaging/send-message
 *
 * Пример payload:
 * {
 *   "token": "FCM_DEVICE_TOKEN",
 *   "notification": {
 *     "title": "Изменение расписания",
 *     "body": "Пара 09:40 отменена"
 *   },
 *   "data": {
 *     "url": "https://app.enexus.isabelline.xyz/schedule"
 *   }
 * }
 */
public class NcfuFirebaseService extends FirebaseMessagingService {

    private static final String CHANNEL_ID = "ncfu_default";
    private static final int    NOTIF_ID   = 1001;

    @Override
    public void onMessageReceived(RemoteMessage message) {
        super.onMessageReceived(message);

        String title = "eNexus";
        String body  = "Новое уведомление";
        String url   = "https://app.enexus.isabelline.xyz/schedule";

        if (message.getNotification() != null) {
            if (message.getNotification().getTitle() != null)
                title = message.getNotification().getTitle();
            if (message.getNotification().getBody() != null)
                body = message.getNotification().getBody();
        }

        if (message.getData().containsKey("url")) {
            url = message.getData().get("url");
        }

        // Intent открывает приложение на нужном URL
        Intent intent = new Intent(this, LauncherActivity.class);
        intent.setData(Uri.parse(url));
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);

        PendingIntent pi = PendingIntent.getActivity(
                this, 0, intent,
                PendingIntent.FLAG_ONE_SHOT | PendingIntent.FLAG_IMMUTABLE
        );

        Uri soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(R.mipmap.ic_launcher_round)
                .setContentTitle(title)
                .setContentText(body)
                .setAutoCancel(true)
                .setSound(soundUri)
                .setContentIntent(pi);

        NotificationManager nm =
                (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) nm.notify(NOTIF_ID, builder.build());
    }

    @Override
    public void onNewToken(String token) {
        super.onNewToken(token);
        // TODO: отправить токен на бэкенд для адресных уведомлений
        // Пример: sendTokenToServer(token);
        android.util.Log.d("FCM", "New token: " + token);
    }
}
