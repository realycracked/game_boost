package com.filedrop.app.notifications

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.filedrop.app.R
import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags
import com.filedrop.app.core.formatBytes
import com.filedrop.app.core.formatFileCount
import kotlin.math.abs

class NotificationHelper(private val context: Context) {

    private val manager = context.getSystemService(NotificationManager::class.java)

    fun ensureChannels() {
        val requests = NotificationChannel(
            CHANNEL_REQUESTS,
            context.getString(R.string.channel_requests_name),
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = context.getString(R.string.channel_requests_description)
            setShowBadge(true)
        }
        val progress = NotificationChannel(
            CHANNEL_PROGRESS,
            context.getString(R.string.channel_progress_name),
            NotificationManager.IMPORTANCE_LOW,
        ).apply {
            description = context.getString(R.string.channel_progress_description)
            setShowBadge(false)
        }
        manager.createNotificationChannel(requests)
        manager.createNotificationChannel(progress)
    }

    fun notificationsAllowed(): Boolean = NotificationManagerCompat.from(context).areNotificationsEnabled()

    /**
     * Demande entrante : la seule interaction exigée du destinataire.
     * Deux actions, aucun code à saisir, aucun formulaire.
     */
    fun showIncomingRequest(
        sessionId: String,
        peerName: String,
        peerModel: String,
        fileCount: Int,
        totalBytes: Long,
    ) {
        if (!notificationsAllowed()) {
            FdLog.w(
                LogTags.NOTIF,
                "Notifications désactivées : la demande de $peerName ne peut pas être affichée. " +
                    "Elle reste visible dans l'application.",
            )
            return
        }
        val notification = NotificationCompat.Builder(context, CHANNEL_REQUESTS)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("$peerName souhaite vous envoyer")
            .setContentText("${formatFileCount(fileCount)} — ${formatBytes(totalBytes)}")
            .setSubText(peerModel)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setAutoCancel(false)
            .setOngoing(true)
            .setContentIntent(openAppIntent())
            .addAction(0, context.getString(R.string.action_refuse), decisionIntent(sessionId, false))
            .addAction(0, context.getString(R.string.action_accept), decisionIntent(sessionId, true))
            .build()

        manager.notify(idFor(sessionId), notification)
        FdLog.i(LogTags.NOTIF, "Demande affichée pour la session $sessionId ($peerName)")
    }

    fun cancelRequest(sessionId: String) {
        manager.cancel(idFor(sessionId))
    }

    fun buildProgressNotification(title: String, text: String, percent: Int?): Notification =
        NotificationCompat.Builder(context, CHANNEL_PROGRESS)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(text)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(openAppIntent())
            .apply {
                if (percent != null) {
                    setProgress(100, percent.coerceIn(0, 100), false)
                } else {
                    setProgress(0, 0, true)
                }
            }
            .build()

    fun showFinished(sessionId: String, title: String, text: String) {
        if (!notificationsAllowed()) return
        val notification = NotificationCompat.Builder(context, CHANNEL_PROGRESS)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(text)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .setContentIntent(openAppIntent())
            .build()
        manager.notify(idFor(sessionId) + 1, notification)
    }

    private fun openAppIntent(): PendingIntent {
        val intent = Intent().apply {
            setClassName(context, "com.filedrop.app.ui.MainActivity")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        return PendingIntent.getActivity(
            context,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    private fun decisionIntent(sessionId: String, accept: Boolean): PendingIntent {
        val suffix = if (accept) "accept" else "refuse"
        val intent = Intent(context, TransferActionReceiver::class.java).apply {
            action = if (accept) TransferActionReceiver.ACTION_ACCEPT else TransferActionReceiver.ACTION_REFUSE
            putExtra(TransferActionReceiver.EXTRA_SESSION_ID, sessionId)
            // Deux PendingIntent ne se distinguent pas par leurs extras : sans une
            // donnée différente, « Accepter » écraserait « Refuser ».
            data = Uri.parse("filedrop://session/$sessionId/$suffix")
        }
        return PendingIntent.getBroadcast(
            context,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    private fun idFor(sessionId: String): Int = 1000 + (abs(sessionId.hashCode()) % 100_000) * 2

    companion object {
        const val CHANNEL_REQUESTS = "transfer_requests"
        const val CHANNEL_PROGRESS = "transfer_progress"

        /** Identifiant fixe de la notification du service de premier plan. */
        const val FOREGROUND_ID = 42
    }
}
