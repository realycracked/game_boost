package com.filedrop.app.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import com.filedrop.app.AppContainer
import com.filedrop.app.FileDropApplication
import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags
import com.filedrop.app.transfer.FileDropService

class MainActivity : ComponentActivity() {

    private val container: AppContainer by lazy { (application as FileDropApplication).container }

    private val requestNotifications =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            FdLog.i(
                LogTags.UI,
                if (granted) {
                    "Permission de notification accordée"
                } else {
                    "Permission de notification refusée : les demandes entrantes ne s'afficheront " +
                        "que dans l'application, pas en notification"
                },
            )
        }

    private val requestLegacyStorage =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            FdLog.i(LogTags.UI, "Permission de stockage (Android 9 et moins) : accordée=$granted")
        }

    private val pickFiles =
        registerForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { uris ->
            if (uris.isNullOrEmpty()) {
                FdLog.i(LogTags.UI, "Sélection de fichiers annulée")
                return@registerForActivityResult
            }
            val files = uris.mapNotNull { container.fileResolver.resolve(it) }
            FdLog.i(LogTags.UI, "${files.size} fichier(s) sélectionné(s) par l'utilisateur")
            container.ui.pendingFiles = files
            container.ui.route = if (files.isEmpty()) Route.HOME else Route.SEND
        }

    private val pickDestination =
        registerForActivityResult(ActivityResultContracts.OpenDocumentTree()) { uri ->
            if (uri == null) return@registerForActivityResult
            runCatching {
                contentResolver.takePersistableUriPermission(
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION,
                )
            }.onFailure {
                FdLog.e(LogTags.UI, "Impossible de conserver l'accès au dossier choisi", it)
            }
            container.settings.setDestinationTreeUri(uri.toString())
            FdLog.i(LogTags.UI, "Dossier de réception choisi : $uri")
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        handleShareIntent(intent)
        ensureNotificationPermission()

        // La réception reprend au lancement si l'utilisateur l'avait laissée active.
        if (container.settings.receivingEnabled.value) {
            FileDropService.startReceiving(this)
        }

        setContent {
            FileDropTheme {
                FileDropApp(
                    container = container,
                    onPickFiles = { pickFiles.launch(arrayOf("*/*")) },
                    onPickDestination = { pickDestination.launch(null) },
                    onStartReceiving = {
                        ensureLegacyStoragePermission()
                        FileDropService.startReceiving(this)
                    },
                    onStopReceiving = { FileDropService.stopReceiving(this) },
                    onSend = { peer, files ->
                        FileDropService.send(this, peer.serviceName, files.map { it.uri })
                    },
                    onCancel = { sessionId -> FileDropService.cancel(this, sessionId) },
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleShareIntent(intent)
    }

    override fun onResume() {
        super.onResume()
        container.discovery.startDiscovery()
    }

    override fun onPause() {
        super.onPause()
        // La découverte s'arrête dès que l'écran n'est plus visible : mDNS en
        // continu réveille la radio Wi-Fi et coûte cher en batterie pour rien.
        // La réception, elle, reste active grâce au service de premier plan.
        container.discovery.stopDiscovery()
    }

    private fun handleShareIntent(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND && intent?.action != Intent.ACTION_SEND_MULTIPLE) return
        val files = container.shareIntentParser.parse(intent)
        if (files.isEmpty()) {
            container.ui.lastError =
                "Aucun fichier exploitable dans ce partage. FileDrop ne transfère que des fichiers."
            return
        }
        container.ui.pendingFiles = files
        container.ui.selectedPeer = null
        container.ui.route = Route.SEND
    }

    private fun ensureNotificationPermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) return
        requestNotifications.launch(Manifest.permission.POST_NOTIFICATIONS)
    }

    private fun ensureLegacyStoragePermission() {
        if (Build.VERSION.SDK_INT > Build.VERSION_CODES.P) return
        if (checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED) return
        requestLegacyStorage.launch(Manifest.permission.WRITE_EXTERNAL_STORAGE)
    }

    @Suppress("unused")
    private fun openUri(uri: Uri) {
        startActivity(Intent(Intent.ACTION_VIEW, uri))
    }
}
