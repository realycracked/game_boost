package com.filedrop.app.history

import android.content.Context
import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/** Historique des transferts et liste des appareils déjà rencontrés. */
class HistoryStore(context: Context) {

    private val prefs = context.applicationContext
        .getSharedPreferences("filedrop_history", Context.MODE_PRIVATE)

    private val _records = MutableStateFlow(RecordCodec.decodeTransfers(prefs.getString(KEY_TRANSFERS, null)))
    val records: StateFlow<List<TransferRecord>> = _records

    private val _knownDevices = MutableStateFlow(RecordCodec.decodeDevices(prefs.getString(KEY_DEVICES, null)))
    val knownDevices: StateFlow<List<KnownDevice>> = _knownDevices

    fun record(record: TransferRecord) {
        val updated = (listOf(record) + _records.value).take(MAX_RECORDS)
        _records.value = updated
        prefs.edit().putString(KEY_TRANSFERS, RecordCodec.encodeTransfers(updated)).apply()
        FdLog.i(
            LogTags.APP,
            "Historique : ${record.direction} ${record.fileCount} fichier(s) avec ${record.peerName} " +
                "— ${record.outcome}",
        )

        if (record.outcome == TransferOutcome.COMPLETED && record.peerFingerprint.isNotBlank()) {
            rememberDevice(record.peerFingerprint, record.peerName, record.timestampMs)
        }
    }

    fun rememberDevice(fingerprint: String, name: String, timestampMs: Long, model: String = "") {
        val existing = _knownDevices.value.firstOrNull { it.fingerprint == fingerprint }
        val updatedDevice = KnownDevice(
            fingerprint = fingerprint,
            name = name.ifBlank { existing?.name.orEmpty() },
            model = model.ifBlank { existing?.model.orEmpty() },
            lastTransferMs = timestampMs,
            transferCount = (existing?.transferCount ?: 0) + 1,
        )
        val updated = (listOf(updatedDevice) + _knownDevices.value.filterNot { it.fingerprint == fingerprint })
            .take(MAX_DEVICES)
        _knownDevices.value = updated
        prefs.edit().putString(KEY_DEVICES, RecordCodec.encodeDevices(updated)).apply()
    }

    fun isKnown(fingerprint: String): Boolean =
        fingerprint.isNotBlank() && _knownDevices.value.any { it.fingerprint == fingerprint }

    fun clearHistory() {
        _records.value = emptyList()
        prefs.edit().remove(KEY_TRANSFERS).apply()
    }

    fun forgetDevices() {
        _knownDevices.value = emptyList()
        prefs.edit().remove(KEY_DEVICES).apply()
    }

    private companion object {
        const val KEY_TRANSFERS = "transfers"
        const val KEY_DEVICES = "devices"
        const val MAX_RECORDS = 200
        const val MAX_DEVICES = 50
    }
}
