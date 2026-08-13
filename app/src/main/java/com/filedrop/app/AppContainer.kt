package com.filedrop.app

import android.content.Context
import com.filedrop.app.discovery.DeviceDiscovery
import com.filedrop.app.discovery.NsdDiscovery
import com.filedrop.app.history.HistoryStore
import com.filedrop.app.notifications.NotificationHelper
import com.filedrop.app.security.IdentityStore
import com.filedrop.app.sharing.ShareIntentParser
import com.filedrop.app.storage.FileResolver
import com.filedrop.app.storage.ReceivedFileWriter
import com.filedrop.app.storage.SettingsStore
import com.filedrop.app.transfer.TransferEngine
import com.filedrop.app.transport.BluetoothTransport
import com.filedrop.app.transport.LanTcpTransport
import com.filedrop.app.transport.TransportManager
import com.filedrop.app.transport.WifiDirectTransport
import com.filedrop.app.ui.UiStateHolder

/**
 * Assemblage des composants, à la main.
 *
 * Pas d'injection de dépendances automatique : le graphe tient en vingt lignes,
 * et éviter un processeur d'annotations garde le temps de compilation court sur
 * GitHub Actions, ce qui compte quand chaque essai passe par un build distant.
 */
class AppContainer(context: Context) {

    private val appContext = context.applicationContext

    val ui = UiStateHolder()
    val settings = SettingsStore(appContext)
    val identityStore = IdentityStore(appContext)
    val notifications = NotificationHelper(appContext)
    val history = HistoryStore(appContext)
    val fileResolver = FileResolver(appContext)
    val shareIntentParser = ShareIntentParser(fileResolver)
    val receivedFileWriter = ReceivedFileWriter(appContext, settings)

    val discovery: DeviceDiscovery = NsdDiscovery(appContext, identityStore)

    // L'ordre de la liste n'a pas d'importance : TransportManager classe les
    // transports par débit estimé, pas par position.
    val transportManager = TransportManager(
        listOf(
            LanTcpTransport(appContext),
            WifiDirectTransport(appContext),
            BluetoothTransport(appContext),
        ),
    )

    val engine = TransferEngine(
        identityStore = identityStore,
        transportManager = transportManager,
        discovery = discovery,
        settings = settings,
        history = history,
        fileResolver = fileResolver,
        receivedFileWriter = receivedFileWriter,
        notifications = notifications,
    )
}
