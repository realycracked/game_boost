package com.filedrop.app.transfer

import android.app.Service
import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.Uri
import android.os.Build
import android.os.IBinder
import androidx.core.app.ServiceCompat
import com.filedrop.app.FileDropApplication
import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags
import com.filedrop.app.core.formatBytes
import com.filedrop.app.notifications.NotificationHelper
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch

/**
 * Service de premier plan qui héberge la réception et les transferts en cours.
 *
 * Il existe pour une raison précise : sans lui, Android met le processus en
 * veille dès que l'écran s'éteint ou que l'utilisateur quitte l'application, et
 * un transfert de plusieurs Go serait coupé. Le type déclaré est `dataSync`,
 * obligatoire depuis Android 14, et la notification associée est de faible
 * priorité pour ne pas être intrusive.
 */
class FileDropService : Service() {

    private val container by lazy { (application as FileDropApplication).container }
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private var observing = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        container.notifications.ensureChannels()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Android impose de passer en premier plan dans les secondes qui suivent
        // le démarrage, avant tout traitement.
        promoteToForeground("FileDrop", "Préparation…", null)
        startObserving()

        when (intent?.action) {
            ACTION_START_RECEIVING -> {
                FdLog.i(LogTags.SERVICE, "Démarrage de la réception demandé")
                container.settings.setReceivingEnabled(true)
                container.engine.startReceiving()
            }

            ACTION_STOP_RECEIVING -> {
                FdLog.i(LogTags.SERVICE, "Arrêt de la réception demandé")
                container.settings.setReceivingEnabled(false)
                container.engine.stopReceiving()
                stopIfIdle()
            }

            ACTION_SEND -> handleSend(intent)

            ACTION_CANCEL -> intent.getStringExtra(EXTRA_SESSION_ID)?.let { container.engine.cancel(it) }

            else -> FdLog.d(LogTags.SERVICE, "Service démarré sans action particulière")
        }
        return START_STICKY
    }

    private fun handleSend(intent: Intent) {
        val peerServiceName = intent.getStringExtra(EXTRA_PEER_SERVICE_NAME)
        val uris = intent.clipData?.let { clip ->
            (0 until clip.itemCount).mapNotNull { clip.getItemAt(it)?.uri }
        }.orEmpty()

        if (peerServiceName == null || uris.isEmpty()) {
            FdLog.e(LogTags.SERVICE, "Envoi impossible : appareil ou fichiers manquants dans l'intent")
            stopIfIdle()
            return
        }

        val peer = container.discovery.peers.value.firstOrNull { it.serviceName == peerServiceName }
        if (peer == null) {
            FdLog.e(
                LogTags.SERVICE,
                "Envoi impossible : $peerServiceName n'est plus visible sur le réseau",
            )
            stopIfIdle()
            return
        }

        val files = uris.mapNotNull { container.fileResolver.resolve(it) }
        if (files.isEmpty()) {
            FdLog.e(LogTags.SERVICE, "Envoi impossible : aucun fichier lisible parmi ${uris.size} URI")
            stopIfIdle()
            return
        }

        container.engine.send(peer, files)
    }

    private fun startObserving() {
        if (observing) return
        observing = true
        serviceScope.launch {
            combine(container.engine.sessions, container.engine.isReceiving) { sessions, receiving ->
                sessions to receiving
            }.collect { (sessions, receiving) ->
                val active = sessions.filter { it.isActive }
                when {
                    active.isNotEmpty() -> {
                        val session = active.first()
                        val percent = if (session.status == SessionStatus.TRANSFERRING) {
                            (session.progress * 100).toInt()
                        } else {
                            null
                        }
                        val title = if (session.outgoing) {
                            "Envoi vers ${session.peerName}"
                        } else {
                            "Réception depuis ${session.peerName}"
                        }
                        val text = when (session.status) {
                            SessionStatus.CONNECTING -> "Connexion…"
                            SessionStatus.AWAITING_DECISION -> "En attente d'acceptation"
                            else -> "${formatBytes(session.transferredBytes)} / " +
                                formatBytes(session.totalBytes)
                        }
                        promoteToForeground(title, text, percent)
                    }

                    receiving -> promoteToForeground(
                        "FileDrop est visible",
                        "Prêt à recevoir des fichiers",
                        null,
                    )

                    else -> stopIfIdle()
                }
            }
        }
    }

    private fun promoteToForeground(title: String, text: String, percent: Int?) {
        val notification = container.notifications.buildProgressNotification(title, text, percent)
        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
        } else {
            0
        }
        ServiceCompat.startForeground(this, NotificationHelper.FOREGROUND_ID, notification, type)
    }

    private fun stopIfIdle() {
        val busy = container.engine.sessions.value.any { it.isActive } || container.engine.isReceiving.value
        if (!busy) {
            FdLog.i(LogTags.SERVICE, "Plus rien à faire : arrêt du service")
            ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
            stopSelf()
        }
    }

    override fun onDestroy() {
        serviceScope.cancel()
        observing = false
        super.onDestroy()
    }

    companion object {
        const val ACTION_START_RECEIVING = "com.filedrop.app.START_RECEIVING"
        const val ACTION_STOP_RECEIVING = "com.filedrop.app.STOP_RECEIVING"
        const val ACTION_SEND = "com.filedrop.app.SEND"
        const val ACTION_CANCEL = "com.filedrop.app.CANCEL"

        const val EXTRA_SESSION_ID = "session_id"
        const val EXTRA_PEER_SERVICE_NAME = "peer_service_name"

        fun startReceiving(context: Context) {
            context.startForegroundService(
                Intent(context, FileDropService::class.java).setAction(ACTION_START_RECEIVING),
            )
        }

        fun stopReceiving(context: Context) {
            context.startForegroundService(
                Intent(context, FileDropService::class.java).setAction(ACTION_STOP_RECEIVING),
            )
        }

        fun cancel(context: Context, sessionId: String) {
            context.startForegroundService(
                Intent(context, FileDropService::class.java)
                    .setAction(ACTION_CANCEL)
                    .putExtra(EXTRA_SESSION_ID, sessionId),
            )
        }

        /**
         * Démarre un envoi en transmettant au service l'autorisation de lecture
         * des URI.
         *
         * Le `ClipData` combiné à `FLAG_GRANT_READ_URI_PERMISSION` est le
         * mécanisme officiel pour propager une autorisation d'URI à un autre
         * composant : sans lui, un partage reçu via le menu Partager d'Android
         * deviendrait illisible dès que l'activité d'origine se termine.
         */
        fun send(context: Context, peerServiceName: String, uris: List<Uri>) {
            if (uris.isEmpty()) return
            val intent = Intent(context, FileDropService::class.java)
                .setAction(ACTION_SEND)
                .putExtra(EXTRA_PEER_SERVICE_NAME, peerServiceName)
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

            val clip = ClipData.newUri(context.contentResolver, "FileDrop", uris.first())
            uris.drop(1).forEach { clip.addItem(ClipData.Item(it)) }
            intent.clipData = clip

            context.startForegroundService(intent)
        }
    }
}
