package com.filedrop.app.history

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RecordCodecTest {

    @Test
    fun `un historique survit a un aller-retour`() {
        val records = listOf(
            TransferRecord(
                id = "a",
                timestampMs = 1_700_000_000_000,
                direction = TransferDirection.SENT,
                peerName = "Galaxy S24",
                peerFingerprint = "A7F2-90BC-31D4",
                fileCount = 12,
                totalBytes = 2_400_000_000,
                outcome = TransferOutcome.COMPLETED,
                detail = "IMG_001.jpg",
            ),
            TransferRecord(
                id = "b",
                timestampMs = 1_700_000_100_000,
                direction = TransferDirection.RECEIVED,
                peerName = "PC de Lucien",
                peerFingerprint = "1122-3344-5566",
                fileCount = 34,
                totalBytes = 850_000_000,
                outcome = TransferOutcome.FAILED,
                detail = "Connexion perdue",
            ),
        )
        assertEquals(records, RecordCodec.decodeTransfers(RecordCodec.encodeTransfers(records)))
    }

    @Test
    fun `les appareils connus survivent a un aller-retour`() {
        val devices = listOf(
            KnownDevice("A7F2-90BC-31D4", "Galaxy S24", "Samsung SM-S921B", 1_700_000_000_000, 3),
        )
        assertEquals(devices, RecordCodec.decodeDevices(RecordCodec.encodeDevices(devices)))
    }

    @Test
    fun `une entree corrompue est ignoree sans faire tomber le reste`() {
        val valid = RecordCodec.encodeTransfers(
            listOf(
                TransferRecord(
                    "a", 1, TransferDirection.SENT, "P", "F", 1, 1,
                    TransferOutcome.COMPLETED, "d",
                ),
            ),
        )
        val corrupted = "n importe quoi" + Char(30) + valid
        assertEquals(1, RecordCodec.decodeTransfers(corrupted).size)
    }

    @Test
    fun `un historique vide se relit sans erreur`() {
        assertTrue(RecordCodec.decodeTransfers(null).isEmpty())
        assertTrue(RecordCodec.decodeTransfers("").isEmpty())
        assertTrue(RecordCodec.decodeDevices(null).isEmpty())
    }
}
