package com.filedrop.app.discovery

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Build
import android.util.Base64
import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags
import com.filedrop.app.security.IdentityStore
import com.filedrop.app.transport.TransportId
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * Découverte des appareils par mDNS / DNS-SD, via l'API système `NsdManager`.
 *
 * Pourquoi mDNS et pas autre chose en V1 : c'est la seule découverte Android
 * qui ne réclame **aucune permission d'exécution**. Un scan Wi-Fi ou un scan BLE
 * exigerait la localisation précise, ce qui serait disproportionné pour l'usage.
 *
 * Deux limites réelles de `NsdManager`, gérées explicitement ici :
 *
 *  1. `resolveService` ne supporte pas deux résolutions simultanées : la seconde
 *     échoue avec `FAILURE_ALREADY_ACTIVE`. Les résolutions sont donc mises en
 *     file et exécutées une par une.
 *  2. mDNS ne traverse pas les réseaux et ne fonctionne pas si le point d'accès
 *     isole ses clients. Ce n'est pas contournable côté application ; le cas est
 *     journalisé et expliqué à l'utilisateur plutôt que masqué.
 */
class NsdDiscovery(
    context: Context,
    private val identityStore: IdentityStore,
) : DeviceDiscovery {

    private val appContext = context.applicationContext
    private val nsdManager = appContext.getSystemService(Context.NSD_SERVICE) as NsdManager

    private val _peers = MutableStateFlow<List<PeerDevice>>(emptyList())
    override val peers: StateFlow<List<PeerDevice>> = _peers

    private val _isDiscovering = MutableStateFlow(false)
    override val isDiscovering: StateFlow<Boolean> = _isDiscovering

    private val _isAdvertising = MutableStateFlow(false)
    override val isAdvertising: StateFlow<Boolean> = _isAdvertising

    private val lock = Any()
    private val resolveQueue = ArrayDeque<NsdServiceInfo>()
    private var resolveInProgress = false

    private var discoveryListener: NsdManager.DiscoveryListener? = null
    private var registrationListener: NsdManager.RegistrationListener? = null

    private var advertisedPort: Int = -1
    private var advertisedName: String = ""

    // --- Publication ---------------------------------------------------------

    override fun startAdvertising(port: Int, displayName: String) {
        synchronized(lock) {
            if (registrationListener != null) {
                if (advertisedPort == port && advertisedName == displayName) return
                stopAdvertisingLocked()
            }
            advertisedPort = port
            advertisedName = displayName

            val serviceInfo = NsdServiceInfo().apply {
                // Le système renomme automatiquement en cas de collision.
                serviceName = "FileDrop-${identityStore.deviceId.take(6)}"
                serviceType = SERVICE_TYPE
                setPort(port)
                // Les valeurs TXT sont encodées en Base64 : un nom d'appareil peut
                // contenir des accents ou des espaces, que tous les résolveurs mDNS
                // ne traitent pas de la même façon.
                setAttribute(ATTR_DEVICE_ID, identityStore.deviceId)
                setAttribute(ATTR_NAME, encode(displayName))
                setAttribute(ATTR_MODEL, encode(deviceModel()))
                setAttribute(ATTR_FINGERPRINT, identityStore.identity.fingerprint)
                setAttribute(ATTR_VERSION, PROTOCOL_VERSION.toString())
            }

            val listener = object : NsdManager.RegistrationListener {
                override fun onServiceRegistered(info: NsdServiceInfo) {
                    _isAdvertising.value = true
                    FdLog.i(LogTags.DISCOVERY, "Visible sous « ${info.serviceName} » sur le port $port")
                }

                override fun onRegistrationFailed(info: NsdServiceInfo, errorCode: Int) {
                    _isAdvertising.value = false
                    FdLog.e(
                        LogTags.DISCOVERY,
                        "Publication mDNS refusée (code $errorCode) : les autres appareils ne vous verront pas",
                    )
                }

                override fun onServiceUnregistered(info: NsdServiceInfo) {
                    _isAdvertising.value = false
                    FdLog.i(LogTags.DISCOVERY, "Publication mDNS arrêtée")
                }

                override fun onUnregistrationFailed(info: NsdServiceInfo, errorCode: Int) {
                    FdLog.w(LogTags.DISCOVERY, "Arrêt de publication en échec (code $errorCode)")
                }
            }
            registrationListener = listener
            runCatching { nsdManager.registerService(serviceInfo, NsdManager.PROTOCOL_DNS_SD, listener) }
                .onFailure {
                    registrationListener = null
                    FdLog.e(LogTags.DISCOVERY, "registerService a échoué", it)
                }
        }
    }

    override fun stopAdvertising() = synchronized(lock) { stopAdvertisingLocked() }

    private fun stopAdvertisingLocked() {
        registrationListener?.let { listener ->
            runCatching { nsdManager.unregisterService(listener) }
                .onFailure { FdLog.w(LogTags.DISCOVERY, "unregisterService a échoué", it) }
        }
        registrationListener = null
        _isAdvertising.value = false
    }

    // --- Découverte ----------------------------------------------------------

    override fun startDiscovery() {
        synchronized(lock) {
            if (discoveryListener != null) return
            val listener = object : NsdManager.DiscoveryListener {
                override fun onDiscoveryStarted(serviceType: String) {
                    _isDiscovering.value = true
                    FdLog.i(LogTags.DISCOVERY, "Recherche démarrée sur $serviceType")
                }

                override fun onDiscoveryStopped(serviceType: String) {
                    _isDiscovering.value = false
                    FdLog.i(LogTags.DISCOVERY, "Recherche arrêtée")
                }

                override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {
                    _isDiscovering.value = false
                    FdLog.e(
                        LogTags.DISCOVERY,
                        "Impossible de démarrer la recherche (code $errorCode). " +
                            "Vérifiez que le Wi-Fi est activé.",
                    )
                    synchronized(lock) { discoveryListener = null }
                }

                override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {
                    FdLog.w(LogTags.DISCOVERY, "Arrêt de la recherche en échec (code $errorCode)")
                    _isDiscovering.value = false
                    synchronized(lock) { discoveryListener = null }
                }

                override fun onServiceFound(info: NsdServiceInfo) {
                    if (info.serviceType?.contains(SERVICE_TYPE_SUFFIX) != true) return
                    FdLog.d(LogTags.DISCOVERY, "Service repéré : ${info.serviceName}")
                    enqueueResolve(info)
                }

                override fun onServiceLost(info: NsdServiceInfo) {
                    FdLog.i(LogTags.DISCOVERY, "Service perdu : ${info.serviceName}")
                    _peers.value = _peers.value.filterNot { it.serviceName == info.serviceName }
                }
            }
            discoveryListener = listener
            runCatching {
                nsdManager.discoverServices(SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, listener)
            }.onFailure {
                discoveryListener = null
                FdLog.e(LogTags.DISCOVERY, "discoverServices a échoué", it)
            }
        }
    }

    override fun stopDiscovery() {
        synchronized(lock) {
            discoveryListener?.let { listener ->
                runCatching { nsdManager.stopServiceDiscovery(listener) }
                    .onFailure { FdLog.w(LogTags.DISCOVERY, "stopServiceDiscovery a échoué", it) }
            }
            discoveryListener = null
            resolveQueue.clear()
            _isDiscovering.value = false
        }
    }

    override fun refresh() {
        FdLog.i(LogTags.DISCOVERY, "Relance de la recherche demandée")
        stopDiscovery()
        _peers.value = emptyList()
        startDiscovery()
    }

    // --- Résolution sérialisée ----------------------------------------------

    private fun enqueueResolve(info: NsdServiceInfo) {
        synchronized(lock) {
            resolveQueue.addLast(info)
            pumpResolveLocked()
        }
    }

    private fun pumpResolveLocked() {
        if (resolveInProgress) return
        val next = resolveQueue.removeFirstOrNull() ?: return
        resolveInProgress = true

        val listener = object : NsdManager.ResolveListener {
            override fun onResolveFailed(info: NsdServiceInfo, errorCode: Int) {
                FdLog.w(
                    LogTags.DISCOVERY,
                    "Résolution de ${info.serviceName} en échec (code $errorCode)",
                )
                synchronized(lock) {
                    resolveInProgress = false
                    // FAILURE_ALREADY_ACTIVE : la file a été trop rapide, on repasse.
                    if (errorCode == NsdManager.FAILURE_ALREADY_ACTIVE) {
                        resolveQueue.addLast(info)
                    }
                    pumpResolveLocked()
                }
            }

            override fun onServiceResolved(info: NsdServiceInfo) {
                synchronized(lock) {
                    resolveInProgress = false
                    onResolved(info)
                    pumpResolveLocked()
                }
            }
        }

        runCatching {
            @Suppress("DEPRECATION")
            nsdManager.resolveService(next, listener)
        }.onFailure {
            FdLog.e(LogTags.DISCOVERY, "resolveService a levé une exception", it)
            resolveInProgress = false
            pumpResolveLocked()
        }
    }

    private fun onResolved(info: NsdServiceInfo) {
        val attributes = info.attributes ?: emptyMap()
        val deviceId = attributes[ATTR_DEVICE_ID]?.toString(Charsets.UTF_8).orEmpty()

        if (deviceId == identityStore.deviceId) {
            FdLog.d(LogTags.DISCOVERY, "Service ignoré : c'est cet appareil")
            return
        }

        val version = attributes[ATTR_VERSION]?.toString(Charsets.UTF_8)?.toIntOrNull() ?: 0
        if (version != PROTOCOL_VERSION) {
            FdLog.w(
                LogTags.DISCOVERY,
                "${info.serviceName} ignoré : protocole v$version, attendu v$PROTOCOL_VERSION",
            )
            return
        }

        @Suppress("DEPRECATION")
        val host = info.host?.hostAddress
        if (host == null) {
            FdLog.w(LogTags.DISCOVERY, "${info.serviceName} résolu sans adresse exploitable")
            return
        }

        val peer = PeerDevice(
            serviceName = info.serviceName,
            deviceId = deviceId,
            displayName = decode(attributes[ATTR_NAME]).ifBlank { info.serviceName },
            model = decode(attributes[ATTR_MODEL]).ifBlank { "Appareil Android" },
            fingerprint = attributes[ATTR_FINGERPRINT]?.toString(Charsets.UTF_8).orEmpty(),
            host = host,
            port = info.port,
            transport = TransportId.WIFI_LAN,
            lastSeenMs = System.currentTimeMillis(),
        )

        FdLog.i(
            LogTags.DISCOVERY,
            "Appareil disponible : ${peer.displayName} (${peer.model}) sur $host:${peer.port}, " +
                "empreinte ${peer.fingerprint}",
        )

        _peers.value = _peers.value.filterNot {
            it.serviceName == peer.serviceName || it.deviceId == peer.deviceId
        } + peer
    }

    private fun encode(value: String): String =
        Base64.encodeToString(value.toByteArray(Charsets.UTF_8), Base64.NO_WRAP or Base64.URL_SAFE)

    private fun decode(value: ByteArray?): String {
        if (value == null) return ""
        return try {
            String(Base64.decode(value.toString(Charsets.UTF_8), Base64.NO_WRAP or Base64.URL_SAFE), Charsets.UTF_8)
        } catch (error: IllegalArgumentException) {
            FdLog.w(LogTags.DISCOVERY, "Attribut mDNS illisible", error)
            ""
        }
    }

    companion object {
        const val SERVICE_TYPE = "_filedrop._tcp"
        private const val SERVICE_TYPE_SUFFIX = "_filedrop"
        private const val PROTOCOL_VERSION = 1

        private const val ATTR_DEVICE_ID = "id"
        private const val ATTR_NAME = "nm"
        private const val ATTR_MODEL = "md"
        private const val ATTR_FINGERPRINT = "fp"
        private const val ATTR_VERSION = "pv"

        fun deviceModel(): String {
            val manufacturer = Build.MANUFACTURER.orEmpty().replaceFirstChar { it.uppercase() }
            val model = Build.MODEL.orEmpty()
            return if (model.startsWith(manufacturer, ignoreCase = true)) model else "$manufacturer $model".trim()
        }
    }
}
