package com.filedrop.app.transfer

enum class SessionStatus {
    CONNECTING,
    AWAITING_DECISION,
    TRANSFERRING,
    COMPLETED,
    REFUSED,
    CANCELLED,
    FAILED,
}

/** État observable d'un transfert, dans un sens ou dans l'autre. */
data class TransferSession(
    val id: String,
    val outgoing: Boolean,
    val peerName: String,
    val peerModel: String,
    val peerFingerprint: String,
    val fileCount: Int,
    val totalBytes: Long,
    val previewNames: List<String> = emptyList(),
    val status: SessionStatus = SessionStatus.CONNECTING,
    val transferredBytes: Long = 0,
    val currentFileIndex: Int = 0,
    val currentFileName: String = "",
    val currentFileBytes: Long = 0,
    val currentFileTotal: Long = 0,
    val bytesPerSecond: Long = 0,
    val etaSeconds: Long = -1,
    val message: String = "",
    val startedAtMs: Long = System.currentTimeMillis(),
) {
    val progress: Float
        get() = if (totalBytes <= 0) 0f else (transferredBytes.toDouble() / totalBytes).toFloat().coerceIn(0f, 1f)

    val currentFileProgress: Float
        get() = if (currentFileTotal <= 0) 0f else (currentFileBytes.toDouble() / currentFileTotal).toFloat().coerceIn(0f, 1f)

    val isActive: Boolean
        get() = status == SessionStatus.CONNECTING ||
            status == SessionStatus.AWAITING_DECISION ||
            status == SessionStatus.TRANSFERRING

    val isPendingDecision: Boolean
        get() = !outgoing && status == SessionStatus.AWAITING_DECISION
}

/**
 * Estimation de débit lissée.
 *
 * Une mesure brute sur l'intervalle précédent saute dans tous les sens dès que
 * l'écriture disque hoquette ; la moyenne exponentielle donne un chiffre qu'un
 * humain peut lire, et une estimation de temps restant qui ne bondit pas.
 */
class SpeedMeter(private val minIntervalMs: Long = 500) {

    private var lastTimeMs = 0L
    private var lastBytes = 0L
    private var smoothed = 0L

    fun update(totalBytes: Long, nowMs: Long): Long {
        if (lastTimeMs == 0L) {
            lastTimeMs = nowMs
            lastBytes = totalBytes
            return 0
        }
        val elapsed = nowMs - lastTimeMs
        if (elapsed < minIntervalMs) return smoothed

        val instant = ((totalBytes - lastBytes) * 1000L) / elapsed
        smoothed = if (smoothed == 0L) instant else (smoothed * 7 + instant * 3) / 10
        lastTimeMs = nowMs
        lastBytes = totalBytes
        return smoothed
    }

    fun etaSeconds(remainingBytes: Long): Long =
        if (smoothed <= 0 || remainingBytes <= 0) -1 else remainingBytes / smoothed
}
