package com.filedrop.app.transport

import com.filedrop.app.discovery.PeerDevice
import java.io.Closeable
import java.io.InputStream
import java.io.OutputStream

enum class TransportId { WIFI_LAN, WIFI_DIRECT, BLUETOOTH }

sealed interface TransportAvailability {
    data class Available(
        val details: String,
        /** Débit typique observé, utilisé pour classer les transports entre eux. */
        val estimatedBytesPerSecond: Long,
    ) : TransportAvailability

    data class Unavailable(val reason: String) : TransportAvailability
}

/**
 * Une connexion établie, réduite à ce dont le protocole a besoin : deux flux.
 *
 * C'est volontaire. Le TCP local, le Wi-Fi Direct (socket sur l'interface p2p)
 * et le RFCOMM Bluetooth exposent tous une paire de flux ; en s'arrêtant là,
 * ajouter un transport plus tard ne touche à aucune ligne du protocole ni de
 * l'interface.
 */
interface TransportConnection : Closeable {
    val input: InputStream
    val output: OutputStream
    val remoteDescription: String
}

/** Point d'écoute d'un transport, côté destinataire. */
interface TransportServer : Closeable {
    /** Port annoncé aux autres appareils, ou -1 si la notion n'a pas de sens. */
    val localPort: Int
    fun accept(): TransportConnection
}

interface TransferTransport {
    val id: TransportId
    val displayName: String

    /** Évalué à chaque fois : l'état du réseau change sous les pieds de l'app. */
    fun availability(): TransportAvailability

    fun listen(): TransportServer

    fun connect(peer: PeerDevice, timeoutMs: Int): TransportConnection
}
