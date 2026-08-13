package com.filedrop.app.transfer

import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags
import com.filedrop.app.core.formatBytes
import com.filedrop.app.discovery.DeviceDiscovery
import com.filedrop.app.discovery.NsdDiscovery
import com.filedrop.app.discovery.PeerDevice
import com.filedrop.app.history.HistoryStore
import com.filedrop.app.history.TransferDirection
import com.filedrop.app.history.TransferOutcome
import com.filedrop.app.history.TransferRecord
import com.filedrop.app.notifications.NotificationHelper
import com.filedrop.app.security.Handshake
import com.filedrop.app.security.IdentityStore
import com.filedrop.app.security.SecureChannel
import com.filedrop.app.storage.FileResolver
import com.filedrop.app.storage.ReceivedFileWriter
import com.filedrop.app.storage.SelectedFile
import com.filedrop.app.storage.SettingsStore
import com.filedrop.app.transfer.protocol.ControlCodec
import com.filedrop.app.transfer.protocol.ControlMessage
import com.filedrop.app.transport.TransferTransport
import com.filedrop.app.transport.TransportConnection
import com.filedrop.app.transport.TransportManager
import com.filedrop.app.transport.TransportServer
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import java.io.IOException
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Cœur de FileDrop : établit les sessions, négocie l'acceptation et fait
 * circuler les octets.
 *
 * Deux principes tenus de bout en bout :
 *
 *  - **rien n'est chargé en mémoire.** Les fichiers sont lus et écrits par
 *    blocs de 64 Kio ; un envoi de 18 Go consomme la même mémoire qu'un envoi
 *    de 1 Mo ;
 *  - **tout est journalisé.** Chaque étape (connexion, poignée de main, offre,
 *    décision, début et fin de fichier, erreur) laisse une trace consultable
 *    dans l'écran Journal, seule façon de diagnostiquer sans PC.
 */
class TransferEngine(
    private val identityStore: IdentityStore,
    private val transportManager: TransportManager,
    private val discovery: DeviceDiscovery,
    private val settings: SettingsStore,
    private val history: HistoryStore,
    private val fileResolver: FileResolver,
    private val receivedFileWriter: ReceivedFileWriter,
    private val notifications: NotificationHelper,
) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private val _sessions = MutableStateFlow<List<TransferSession>>(emptyList())
    val sessions: StateFlow<List<TransferSession>> = _sessions

    private val _isReceiving = MutableStateFlow(false)
    val isReceiving: StateFlow<Boolean> = _isReceiving

    private val decisions = ConcurrentHashMap<String, CompletableDeferred<Boolean>>()
    private val cancelFlags = ConcurrentHashMap<String, AtomicBoolean>()

    private var server: TransportServer? = null
    private var acceptJob: Job? = null

    // --- Réception -----------------------------------------------------------

    @Synchronized
    fun startReceiving() {
        if (server != null) {
            FdLog.d(LogTags.RECEIVE, "Réception déjà active")
            return
        }
        val transport = transportManager.selectBest()
        if (transport == null) {
            FdLog.e(
                LogTags.RECEIVE,
                "Réception impossible : aucun transport disponible. Connectez le Wi-Fi puis réessayez.",
            )
            return
        }
        val opened = try {
            transport.listen()
        } catch (error: IOException) {
            FdLog.e(LogTags.RECEIVE, "Ouverture du port d'écoute impossible", error)
            return
        }
        server = opened
        _isReceiving.value = true

        discovery.startAdvertising(opened.localPort, settings.deviceName.value)
        FdLog.i(
            LogTags.RECEIVE,
            "Prêt à recevoir sur le port ${opened.localPort} via ${transport.displayName}",
        )

        acceptJob = scope.launch {
            while (isActive) {
                val connection = try {
                    opened.accept()
                } catch (error: IOException) {
                    if (isActive) FdLog.i(LogTags.RECEIVE, "Boucle d'écoute arrêtée : ${error.message}")
                    break
                }
                FdLog.i(LogTags.RECEIVE, "Connexion entrante depuis ${connection.remoteDescription}")
                launch { handleIncoming(connection) }
            }
        }
    }

    @Synchronized
    fun stopReceiving() {
        acceptJob?.cancel()
        acceptJob = null
        server?.close()
        server = null
        discovery.stopAdvertising()
        _isReceiving.value = false
        FdLog.i(LogTags.RECEIVE, "Réception désactivée")
    }

    /** Port réellement ouvert, utile à l'écran de diagnostic. */
    fun listeningPort(): Int = server?.localPort ?: -1

    private fun handleIncoming(connection: TransportConnection) {
        var sessionId: String? = null
        var channel: SecureChannel? = null
        var target: ReceivedFileWriter.Target? = null
        var transferred = 0L
        var offer: ControlMessage.Offer? = null

        try {
            val handshake = Handshake.asServer(
                connection.input,
                connection.output,
                identityStore.identity,
            )
            channel = handshake.channel

            val firstFrame = channel.readFrame()
                ?: throw IOException("L'émetteur a coupé avant d'envoyer son offre")
            val received = ControlCodec.decode(firstFrame)
            if (received !is ControlMessage.Offer) {
                throw IOException("Message inattendu à l'ouverture : $received")
            }
            offer = received
            sessionId = received.sessionId
            val id = received.sessionId

            FdLog.i(
                LogTags.RECEIVE,
                "Offre de ${received.deviceName} (${received.deviceModel}, empreinte " +
                    "${handshake.peerFingerprint}) : ${received.fileCount} fichier(s), " +
                    formatBytes(received.totalBytes),
            )

            val cancelFlag = AtomicBoolean(false)
            cancelFlags[sessionId] = cancelFlag

            updateSession(
                TransferSession(
                    id = sessionId,
                    outgoing = false,
                    peerName = received.deviceName,
                    peerModel = received.deviceModel,
                    peerFingerprint = handshake.peerFingerprint,
                    fileCount = received.fileCount,
                    totalBytes = received.totalBytes,
                    previewNames = received.previewNames,
                    status = SessionStatus.AWAITING_DECISION,
                ),
            )

            val decision = CompletableDeferred<Boolean>()
            decisions[sessionId] = decision

            val known = history.isKnown(handshake.peerFingerprint)
            if (settings.autoAcceptKnownDevices.value && known) {
                FdLog.i(LogTags.RECEIVE, "Acceptation automatique : appareil connu et option activée")
                decision.complete(true)
            } else {
                notifications.showIncomingRequest(
                    sessionId = sessionId,
                    peerName = received.deviceName,
                    peerModel = received.deviceModel,
                    fileCount = received.fileCount,
                    totalBytes = received.totalBytes,
                )
            }

            val accepted = runBlockingDecision(decision)
            notifications.cancelRequest(sessionId)
            decisions.remove(sessionId)

            if (!accepted) {
                FdLog.i(LogTags.RECEIVE, "Transfert refusé (ou sans réponse) pour la session $sessionId")
                channel.writeFrame(ControlCodec.encode(ControlMessage.Reject("Refusé par le destinataire")))
                finishSession(sessionId, SessionStatus.REFUSED, "Refusé")
                writeHistory(sessionId, received, handshake.peerFingerprint, TransferOutcome.REFUSED, 0, "Refusé")
                return
            }

            channel.writeFrame(ControlCodec.encode(ControlMessage.Accept))
            updateSession(id) { it.copy(status = SessionStatus.TRANSFERRING) }
            FdLog.i(LogTags.RECEIVE, "Transfert accepté, réception en cours")

            val buffer = ByteArray(SecureChannel.MAX_PLAINTEXT)
            val speedMeter = SpeedMeter()
            var lastPublishMs = 0L
            var completed = false
            var currentIndex = 0
            var currentName = ""
            var currentFileBytes = 0L
            var currentFileTotal = 0L
            var lastLocation = ""

            loop@ while (true) {
                if (cancelFlag.get()) {
                    channel.writeFrame(ControlCodec.encode(ControlMessage.Cancel("Annulé par le destinataire")))
                    target?.abort()
                    target = null
                    finishSession(sessionId, SessionStatus.CANCELLED, "Annulé")
                    writeHistory(sessionId, received, handshake.peerFingerprint, TransferOutcome.CANCELLED, transferred, "Annulé")
                    return
                }

                val length = channel.readFrameInto(buffer)
                if (length < 0) {
                    FdLog.w(LogTags.RECEIVE, "Connexion fermée par l'émetteur avant la fin")
                    break@loop
                }

                when (val message = ControlCodec.decode(buffer, length)) {
                    is ControlMessage.FileData -> {
                        val stream = target?.output
                        if (stream == null) {
                            throw IOException("Données reçues sans en-tête de fichier")
                        }
                        stream.write(buffer, 1, message.length)
                        transferred += message.length
                        currentFileBytes += message.length

                        val now = System.currentTimeMillis()
                        val speed = speedMeter.update(transferred, now)
                        if (now - lastPublishMs >= PROGRESS_INTERVAL_MS) {
                            lastPublishMs = now
                            val done = transferred
                            val fileBytes = currentFileBytes
                            updateSession(id) {
                                it.copy(
                                    transferredBytes = done,
                                    currentFileBytes = fileBytes,
                                    bytesPerSecond = speed,
                                    etaSeconds = speedMeter.etaSeconds(it.totalBytes - done),
                                )
                            }
                        }
                    }

                    is ControlMessage.FileStart -> {
                        target?.abort()
                        currentIndex = message.index
                        currentName = message.meta.name
                        currentFileBytes = 0
                        currentFileTotal = message.meta.size
                        FdLog.i(
                            LogTags.RECEIVE,
                            "Fichier ${message.index + 1}/${received.fileCount} : " +
                                "${message.meta.name} (${formatBytes(message.meta.size)})",
                        )
                        target = receivedFileWriter.open(message.meta)
                        lastLocation = target.location
                        val index = currentIndex
                        val name = currentName
                        val total = currentFileTotal
                        updateSession(id) {
                            it.copy(
                                currentFileIndex = index,
                                currentFileName = name,
                                currentFileBytes = 0,
                                currentFileTotal = total,
                            )
                        }
                    }

                    is ControlMessage.FileEnd -> {
                        target?.finish()
                        target = null
                        FdLog.i(LogTags.RECEIVE, "Fichier terminé : $currentName vers $lastLocation")
                    }

                    ControlMessage.TransferEnd -> {
                        completed = true
                        break@loop
                    }

                    is ControlMessage.Cancel -> {
                        FdLog.w(LogTags.RECEIVE, "Annulé par l'émetteur : ${message.reason}")
                        target?.abort()
                        target = null
                        finishSession(sessionId, SessionStatus.CANCELLED, message.reason)
                        writeHistory(sessionId, received, handshake.peerFingerprint, TransferOutcome.CANCELLED, transferred, message.reason)
                        return
                    }

                    else -> FdLog.w(LogTags.RECEIVE, "Message ignoré pendant le transfert : $message")
                }
            }

            if (completed) {
                channel.writeFrame(ControlCodec.encode(ControlMessage.TransferEnd))
                val done = transferred
                updateSession(id) { it.copy(transferredBytes = done, status = SessionStatus.COMPLETED) }
                FdLog.i(LogTags.RECEIVE, "Réception terminée : ${formatBytes(transferred)}")
                notifications.showFinished(
                    sessionId,
                    "Réception terminée",
                    "${received.fileCount} fichier(s) — ${formatBytes(transferred)}",
                )
                history.rememberDevice(
                    handshake.peerFingerprint,
                    received.deviceName,
                    System.currentTimeMillis(),
                    received.deviceModel,
                )
                writeHistory(sessionId, received, handshake.peerFingerprint, TransferOutcome.COMPLETED, transferred, lastLocation)
            } else {
                target?.abort()
                target = null
                finishSession(sessionId, SessionStatus.FAILED, "Interrompu avant la fin")
                writeHistory(sessionId, received, handshake.peerFingerprint, TransferOutcome.FAILED, transferred, "Interrompu")
            }
        } catch (error: Exception) {
            FdLog.e(LogTags.RECEIVE, "Réception en échec", error)
            runCatching { target?.abort() }
            sessionId?.let { id ->
                notifications.cancelRequest(id)
                decisions.remove(id)
                finishSession(id, SessionStatus.FAILED, error.message ?: "Erreur inconnue")
                offer?.let {
                    writeHistory(id, it, "", TransferOutcome.FAILED, transferred, error.message ?: "Erreur")
                }
            }
        } finally {
            sessionId?.let { cancelFlags.remove(it) }
            runCatching { channel?.close() }
            runCatching { connection.close() }
        }
    }

    private fun runBlockingDecision(decision: CompletableDeferred<Boolean>): Boolean =
        kotlinx.coroutines.runBlocking {
            withTimeoutOrNull(DECISION_TIMEOUT_MS) { decision.await() } ?: run {
                FdLog.w(LogTags.RECEIVE, "Aucune réponse en ${DECISION_TIMEOUT_MS / 1000} s : refus par défaut")
                false
            }
        }

    /** Réponse de l'utilisateur à une demande entrante. */
    fun respond(sessionId: String, accept: Boolean) {
        val decision = decisions[sessionId]
        if (decision == null) {
            FdLog.w(LogTags.RECEIVE, "Réponse pour une session inconnue ou expirée : $sessionId")
            return
        }
        FdLog.i(LogTags.RECEIVE, "L'utilisateur a ${if (accept) "accepté" else "refusé"} la session $sessionId")
        decision.complete(accept)
    }

    // --- Envoi ---------------------------------------------------------------

    fun send(peer: PeerDevice, files: List<SelectedFile>): String {
        val sessionId = UUID.randomUUID().toString()
        val totalBytes = files.sumOf { it.size }

        updateSession(
            TransferSession(
                id = sessionId,
                outgoing = true,
                peerName = peer.displayName,
                peerModel = peer.model,
                peerFingerprint = peer.fingerprint,
                fileCount = files.size,
                totalBytes = totalBytes,
                previewNames = files.take(ControlCodec.PREVIEW_LIMIT).map { it.displayName },
                status = SessionStatus.CONNECTING,
            ),
        )

        val cancelFlag = AtomicBoolean(false)
        cancelFlags[sessionId] = cancelFlag
        scope.launch { runSend(sessionId, peer, files, totalBytes, cancelFlag) }
        return sessionId
    }

    private fun runSend(
        sessionId: String,
        peer: PeerDevice,
        files: List<SelectedFile>,
        totalBytes: Long,
        cancelFlag: AtomicBoolean,
    ) {
        var connection: TransportConnection? = null
        var channel: SecureChannel? = null
        var transferred = 0L

        try {
            val transport: TransferTransport = transportManager.selectBest(totalBytes)
                ?: throw IOException(
                    "Aucun transport disponible. Connectez les deux appareils au même réseau Wi-Fi.",
                )

            FdLog.i(
                LogTags.SEND,
                "Envoi de ${files.size} fichier(s) (${formatBytes(totalBytes)}) vers ${peer.displayName}",
            )

            connection = transport.connect(peer, CONNECT_TIMEOUT_MS)
            val handshake = Handshake.asClient(connection.input, connection.output, identityStore.identity)
            channel = handshake.channel

            if (peer.fingerprint.isNotBlank() && peer.fingerprint != handshake.peerFingerprint) {
                throw IOException(
                    "L'appareil ne présente pas l'identité annoncée (${peer.fingerprint} attendu, " +
                        "${handshake.peerFingerprint} reçu). Transfert abandonné.",
                )
            }

            channel.writeFrame(
                ControlCodec.encode(
                    ControlMessage.Offer(
                        sessionId = sessionId,
                        deviceName = settings.deviceName.value,
                        deviceModel = NsdDiscovery.deviceModel(),
                        fileCount = files.size,
                        totalBytes = totalBytes,
                        previewNames = files.take(ControlCodec.PREVIEW_LIMIT).map { it.displayName },
                    ),
                ),
            )
            updateSession(sessionId) { it.copy(status = SessionStatus.AWAITING_DECISION) }
            FdLog.i(LogTags.SEND, "Offre envoyée, en attente de la réponse de ${peer.displayName}")

            val replyFrame = channel.readFrame()
                ?: throw IOException("Le destinataire a coupé la connexion sans répondre")
            when (val reply = ControlCodec.decode(replyFrame)) {
                ControlMessage.Accept -> Unit
                is ControlMessage.Reject -> {
                    FdLog.i(LogTags.SEND, "Transfert refusé par ${peer.displayName} : ${reply.reason}")
                    finishSession(sessionId, SessionStatus.REFUSED, reply.reason)
                    writeSendHistory(sessionId, peer, files.size, totalBytes, TransferOutcome.REFUSED, 0, reply.reason)
                    return
                }

                else -> throw IOException("Réponse inattendue : $reply")
            }

            updateSession(sessionId) { it.copy(status = SessionStatus.TRANSFERRING) }

            // Un seul tampon pour tout le transfert : l'octet 0 porte le type de
            // trame, les 64 Kio suivants les données lues sur le disque.
            val buffer = ByteArray(1 + SecureChannel.CHUNK_SIZE)
            buffer[0] = ControlCodec.TYPE_FILE_DATA.toByte()
            val speedMeter = SpeedMeter()
            var lastPublishMs = 0L

            files.forEachIndexed { index, file ->
                if (cancelFlag.get()) throw TransferCancelled()

                FdLog.i(
                    LogTags.SEND,
                    "Fichier ${index + 1}/${files.size} : ${file.displayName} (${formatBytes(file.size)})",
                )
                channel.writeFrame(ControlCodec.encode(ControlMessage.FileStart(index, file.toMeta())))
                updateSession(sessionId) {
                    it.copy(
                        currentFileIndex = index,
                        currentFileName = file.displayName,
                        currentFileBytes = 0,
                        currentFileTotal = file.size,
                    )
                }

                var sentForFile = 0L
                fileResolver.openInput(file.uri).use { input ->
                    while (true) {
                        if (cancelFlag.get()) throw TransferCancelled()
                        val read = input.read(buffer, 1, SecureChannel.CHUNK_SIZE)
                        if (read <= 0) break
                        channel.writeFrame(buffer, 0, read + 1)
                        sentForFile += read
                        transferred += read

                        val now = System.currentTimeMillis()
                        val speed = speedMeter.update(transferred, now)
                        if (now - lastPublishMs >= PROGRESS_INTERVAL_MS) {
                            lastPublishMs = now
                            val done = transferred
                            val fileBytes = sentForFile
                            updateSession(sessionId) {
                                it.copy(
                                    transferredBytes = done,
                                    currentFileBytes = fileBytes,
                                    bytesPerSecond = speed,
                                    etaSeconds = speedMeter.etaSeconds(totalBytes - done),
                                )
                            }
                        }
                    }
                }
                channel.writeFrame(ControlCodec.encode(ControlMessage.FileEnd(index, sentForFile)))
                if (sentForFile != file.size) {
                    FdLog.w(
                        LogTags.SEND,
                        "${file.displayName} : ${sentForFile} octets envoyés pour ${file.size} annoncés " +
                            "(le fichier a changé pendant l'envoi ?)",
                    )
                }
            }

            channel.writeFrame(ControlCodec.encode(ControlMessage.TransferEnd))
            FdLog.i(LogTags.SEND, "Données envoyées, attente de la confirmation du destinataire")

            val confirmation = channel.readFrame()
            val confirmed = confirmation != null &&
                ControlCodec.decode(confirmation) == ControlMessage.TransferEnd

            val done = transferred
            if (confirmed) {
                updateSession(sessionId) {
                    it.copy(transferredBytes = done, status = SessionStatus.COMPLETED)
                }
                FdLog.i(LogTags.SEND, "Envoi terminé et confirmé : ${formatBytes(transferred)}")
                notifications.showFinished(
                    sessionId,
                    "Envoi terminé",
                    "${files.size} fichier(s) — ${formatBytes(transferred)} vers ${peer.displayName}",
                )
                history.rememberDevice(
                    handshake.peerFingerprint,
                    peer.displayName,
                    System.currentTimeMillis(),
                    peer.model,
                )
                writeSendHistory(
                    sessionId, peer, files.size, totalBytes, TransferOutcome.COMPLETED, transferred,
                    files.firstOrNull()?.displayName.orEmpty(),
                )
            } else {
                finishSession(sessionId, SessionStatus.FAILED, "Le destinataire n'a pas confirmé la réception")
                writeSendHistory(
                    sessionId, peer, files.size, totalBytes, TransferOutcome.FAILED, transferred,
                    "Sans confirmation",
                )
            }
        } catch (cancelled: TransferCancelled) {
            FdLog.i(LogTags.SEND, "Envoi annulé par l'utilisateur")
            runCatching {
                channel?.writeFrame(ControlCodec.encode(ControlMessage.Cancel("Annulé par l'expéditeur")))
            }
            finishSession(sessionId, SessionStatus.CANCELLED, "Annulé")
            writeSendHistory(sessionId, peer, files.size, totalBytes, TransferOutcome.CANCELLED, transferred, "Annulé")
        } catch (error: Exception) {
            FdLog.e(LogTags.SEND, "Envoi en échec vers ${peer.displayName}", error)
            finishSession(sessionId, SessionStatus.FAILED, error.message ?: "Erreur inconnue")
            writeSendHistory(
                sessionId, peer, files.size, totalBytes, TransferOutcome.FAILED, transferred,
                error.message ?: "Erreur",
            )
        } finally {
            cancelFlags.remove(sessionId)
            runCatching { channel?.close() }
            runCatching { connection?.close() }
        }
    }

    fun cancel(sessionId: String) {
        val flag = cancelFlags[sessionId]
        if (flag == null) {
            FdLog.w(LogTags.APP, "Annulation demandée pour une session inconnue : $sessionId")
            return
        }
        FdLog.i(LogTags.APP, "Annulation demandée pour la session $sessionId")
        flag.set(true)
        // Une session encore en attente de décision se termine par un refus.
        decisions[sessionId]?.complete(false)
    }

    fun clearFinishedSessions() {
        _sessions.value = _sessions.value.filter { it.isActive }
    }

    // --- Utilitaires d'état --------------------------------------------------

    private fun updateSession(session: TransferSession) {
        _sessions.value = _sessions.value.filterNot { it.id == session.id } + session
    }

    @Synchronized
    private fun updateSession(id: String, block: (TransferSession) -> TransferSession) {
        _sessions.value = _sessions.value.map { if (it.id == id) block(it) else it }
    }

    private fun finishSession(id: String, status: SessionStatus, message: String) {
        updateSession(id) { it.copy(status = status, message = message) }
    }

    private fun writeHistory(
        sessionId: String,
        offer: ControlMessage.Offer,
        fingerprint: String,
        outcome: TransferOutcome,
        transferred: Long,
        detail: String,
    ) {
        history.record(
            TransferRecord(
                id = sessionId,
                timestampMs = System.currentTimeMillis(),
                direction = TransferDirection.RECEIVED,
                peerName = offer.deviceName,
                peerFingerprint = fingerprint,
                fileCount = offer.fileCount,
                totalBytes = if (outcome == TransferOutcome.COMPLETED) offer.totalBytes else transferred,
                outcome = outcome,
                detail = detail,
            ),
        )
    }

    private fun writeSendHistory(
        sessionId: String,
        peer: PeerDevice,
        fileCount: Int,
        totalBytes: Long,
        outcome: TransferOutcome,
        transferred: Long,
        detail: String,
    ) {
        history.record(
            TransferRecord(
                id = sessionId,
                timestampMs = System.currentTimeMillis(),
                direction = TransferDirection.SENT,
                peerName = peer.displayName,
                peerFingerprint = peer.fingerprint,
                fileCount = fileCount,
                totalBytes = if (outcome == TransferOutcome.COMPLETED) totalBytes else transferred,
                outcome = outcome,
                detail = detail,
            ),
        )
    }

    private class TransferCancelled : Exception("Transfert annulé")

    private companion object {
        const val CONNECT_TIMEOUT_MS = 8_000
        const val DECISION_TIMEOUT_MS = 60_000L
        const val PROGRESS_INTERVAL_MS = 200L
    }
}
