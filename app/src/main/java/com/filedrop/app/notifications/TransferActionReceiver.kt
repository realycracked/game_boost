package com.filedrop.app.notifications

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.filedrop.app.FileDropApplication
import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags

/** Reçoit les appuis sur « Accepter » et « Refuser » depuis la notification. */
class TransferActionReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val sessionId = intent.getStringExtra(EXTRA_SESSION_ID)
        if (sessionId.isNullOrBlank()) {
            FdLog.w(LogTags.NOTIF, "Action de notification sans identifiant de session")
            return
        }
        val accept = when (intent.action) {
            ACTION_ACCEPT -> true
            ACTION_REFUSE -> false
            else -> {
                FdLog.w(LogTags.NOTIF, "Action de notification inconnue : ${intent.action}")
                return
            }
        }

        val application = context.applicationContext as? FileDropApplication
        if (application == null) {
            FdLog.e(LogTags.NOTIF, "Contexte applicatif inattendu : réponse perdue")
            return
        }

        FdLog.i(LogTags.NOTIF, "Notification : ${if (accept) "Accepter" else "Refuser"} ($sessionId)")
        application.container.notifications.cancelRequest(sessionId)
        application.container.engine.respond(sessionId, accept)
    }

    companion object {
        const val ACTION_ACCEPT = "com.filedrop.app.ACCEPT_TRANSFER"
        const val ACTION_REFUSE = "com.filedrop.app.REFUSE_TRANSFER"
        const val EXTRA_SESSION_ID = "session_id"
    }
}
