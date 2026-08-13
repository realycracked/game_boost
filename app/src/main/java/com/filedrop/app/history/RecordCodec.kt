package com.filedrop.app.history

/**
 * Encodage texte des enregistrements d'historique.
 *
 * Volontairement sans base de données : quelques centaines de lignes stockées
 * dans les préférences suffisent, et cela évite d'ajouter Room, son processeur
 * d'annotations et le temps de compilation correspondant à un projet construit
 * sur GitHub Actions. Le format est séparé du stockage pour être testable sans
 * Android.
 */
internal object RecordCodec {

    // Séparateurs de champ et d'enregistrement ASCII : ils ne peuvent pas
    // apparaître dans un nom de fichier ou d'appareil.
    private val FIELD = Char(31)
    private val RECORD = Char(30)

    fun encodeTransfers(records: List<TransferRecord>): String =
        records.joinToString(RECORD.toString()) { record ->
            listOf(
                record.id,
                record.timestampMs.toString(),
                record.direction.name,
                clean(record.peerName),
                record.peerFingerprint,
                record.fileCount.toString(),
                record.totalBytes.toString(),
                record.outcome.name,
                clean(record.detail),
            ).joinToString(FIELD.toString())
        }

    fun decodeTransfers(raw: String?): List<TransferRecord> {
        if (raw.isNullOrEmpty()) return emptyList()
        return raw.split(RECORD).mapNotNull { line ->
            val parts = line.split(FIELD)
            if (parts.size != 9) return@mapNotNull null
            runCatching {
                TransferRecord(
                    id = parts[0],
                    timestampMs = parts[1].toLong(),
                    direction = TransferDirection.valueOf(parts[2]),
                    peerName = parts[3],
                    peerFingerprint = parts[4],
                    fileCount = parts[5].toInt(),
                    totalBytes = parts[6].toLong(),
                    outcome = TransferOutcome.valueOf(parts[7]),
                    detail = parts[8],
                )
            }.getOrNull()
        }
    }

    fun encodeDevices(devices: List<KnownDevice>): String =
        devices.joinToString(RECORD.toString()) { device ->
            listOf(
                device.fingerprint,
                clean(device.name),
                clean(device.model),
                device.lastTransferMs.toString(),
                device.transferCount.toString(),
            ).joinToString(FIELD.toString())
        }

    fun decodeDevices(raw: String?): List<KnownDevice> {
        if (raw.isNullOrEmpty()) return emptyList()
        return raw.split(RECORD).mapNotNull { line ->
            val parts = line.split(FIELD)
            if (parts.size != 5) return@mapNotNull null
            runCatching {
                KnownDevice(
                    fingerprint = parts[0],
                    name = parts[1],
                    model = parts[2],
                    lastTransferMs = parts[3].toLong(),
                    transferCount = parts[4].toInt(),
                )
            }.getOrNull()
        }
    }

    private fun clean(value: String): String = value.replace(FIELD, ' ').replace(RECORD, ' ')
}
