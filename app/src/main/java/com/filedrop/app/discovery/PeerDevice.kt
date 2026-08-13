package com.filedrop.app.discovery

import com.filedrop.app.transport.TransportId

data class PeerDevice(
    /** Nom du service mDNS : identifiant unique côté réseau. */
    val serviceName: String,
    val deviceId: String,
    val displayName: String,
    val model: String,
    /** Empreinte de la clé d'identité, connue avant même de se connecter. */
    val fingerprint: String,
    /** Renseignée seulement une fois le service résolu. */
    val host: String?,
    val port: Int,
    val transport: TransportId,
    val lastSeenMs: Long,
) {
    val isReachable: Boolean get() = host != null && port > 0
}

interface DeviceDiscovery {
    val peers: kotlinx.coroutines.flow.StateFlow<List<PeerDevice>>
    val isDiscovering: kotlinx.coroutines.flow.StateFlow<Boolean>
    val isAdvertising: kotlinx.coroutines.flow.StateFlow<Boolean>

    /** Se rend visible des autres appareils, en annonçant le port d'écoute. */
    fun startAdvertising(port: Int, displayName: String)
    fun stopAdvertising()

    fun startDiscovery()
    fun stopDiscovery()

    /** Relance la recherche à zéro (bouton « Rechercher »). */
    fun refresh()
}
