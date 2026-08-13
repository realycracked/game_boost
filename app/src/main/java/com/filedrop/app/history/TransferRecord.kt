package com.filedrop.app.history

enum class TransferDirection { SENT, RECEIVED }

enum class TransferOutcome { COMPLETED, CANCELLED, REFUSED, FAILED }

data class TransferRecord(
    val id: String,
    val timestampMs: Long,
    val direction: TransferDirection,
    val peerName: String,
    val peerFingerprint: String,
    val fileCount: Int,
    val totalBytes: Long,
    val outcome: TransferOutcome,
    /** Première ligne de détail affichée : nom du premier fichier, ou message d'erreur. */
    val detail: String,
)

data class KnownDevice(
    val fingerprint: String,
    val name: String,
    val model: String,
    val lastTransferMs: Long,
    val transferCount: Int,
)
