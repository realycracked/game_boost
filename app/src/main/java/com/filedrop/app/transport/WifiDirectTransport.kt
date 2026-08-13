package com.filedrop.app.transport

import android.content.Context
import android.content.pm.PackageManager
import com.filedrop.app.discovery.PeerDevice

/**
 * Wi-Fi Direct : place réservée, volontairement non implémentée en V1.
 *
 * Le transport est déjà branché dans [TransportManager] et déclare honnêtement
 * son indisponibilité plutôt que de faire semblant de fonctionner. Ce qu'il
 * faudra faire pour l'activer (V3) est réel et non trivial :
 *
 *  - `WifiP2pManager` impose les permissions `NEARBY_WIFI_DEVICES` (Android 13+)
 *    ou `ACCESS_FINE_LOCATION` (avant), demandées à l'exécution ;
 *  - un des deux appareils devient propriétaire de groupe, et son adresse n'est
 *    connue qu'après `WifiP2pManager.requestConnectionInfo` ;
 *  - se connecter à un groupe Wi-Fi Direct coupe souvent le Wi-Fi habituel,
 *    donc la découverte mDNS en cours, ce qui demande un enchaînement précis.
 *
 * Tant que ce travail n'est pas fait, annoncer le transport comme disponible
 * ferait échouer des transferts sans explication.
 */
class WifiDirectTransport(private val context: Context) : TransferTransport {

    override val id = TransportId.WIFI_DIRECT
    override val displayName = "Wi-Fi Direct"

    override fun availability(): TransportAvailability {
        val supported = context.packageManager.hasSystemFeature(PackageManager.FEATURE_WIFI_DIRECT)
        return TransportAvailability.Unavailable(
            if (supported) {
                "Pris en charge par l'appareil, mais pas encore implémenté (prévu en V3)"
            } else {
                "Non pris en charge par cet appareil"
            },
        )
    }

    override fun listen(): TransportServer =
        throw UnsupportedOperationException("Wi-Fi Direct n'est pas implémenté en V1")

    override fun connect(peer: PeerDevice, timeoutMs: Int): TransportConnection =
        throw UnsupportedOperationException("Wi-Fi Direct n'est pas implémenté en V1")
}
