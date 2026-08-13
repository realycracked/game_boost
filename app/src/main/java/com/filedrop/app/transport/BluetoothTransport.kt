package com.filedrop.app.transport

import android.content.Context
import android.content.pm.PackageManager
import com.filedrop.app.discovery.PeerDevice

/**
 * Bluetooth : place réservée, non implémentée en V1.
 *
 * Le débit utile de RFCOMM plafonne autour de 1 à 2 Mo/s en pratique : envoyer
 * 2 Go par ce chemin prendrait plus d'une demi-heure. Le Bluetooth a donc un
 * rôle précis dans le plan (V3) — découvrir et amorcer une session quand le
 * Wi-Fi local ne donne rien — mais il ne doit jamais être choisi pour un gros
 * transfert si le Wi-Fi est disponible. C'est exactement ce qu'exprime
 * [TransportAvailability.Available.estimatedBytesPerSecond] dans le classement
 * de [TransportManager].
 *
 * Activer ce transport demandera les permissions `BLUETOOTH_SCAN`,
 * `BLUETOOTH_ADVERTISE` et `BLUETOOTH_CONNECT` (Android 12+), qui ne sont
 * volontairement pas déclarées tant que le code n'existe pas.
 */
class BluetoothTransport(private val context: Context) : TransferTransport {

    override val id = TransportId.BLUETOOTH
    override val displayName = "Bluetooth"

    override fun availability(): TransportAvailability {
        val supported = context.packageManager.hasSystemFeature(PackageManager.FEATURE_BLUETOOTH)
        return TransportAvailability.Unavailable(
            if (supported) {
                "Pris en charge par l'appareil, mais pas encore implémenté (prévu en V3)"
            } else {
                "Non pris en charge par cet appareil"
            },
        )
    }

    override fun listen(): TransportServer =
        throw UnsupportedOperationException("Le Bluetooth n'est pas implémenté en V1")

    override fun connect(peer: PeerDevice, timeoutMs: Int): TransportConnection =
        throw UnsupportedOperationException("Le Bluetooth n'est pas implémenté en V1")
}
