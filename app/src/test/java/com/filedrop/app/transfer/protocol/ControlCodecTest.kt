package com.filedrop.app.transfer.protocol

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class ControlCodecTest {

    @Test
    fun `une offre survit a un aller-retour`() {
        val offer = ControlMessage.Offer(
            sessionId = "session-1",
            deviceName = "Téléphone de Lucas",
            deviceModel = "Galaxy A07",
            fileCount = 12,
            totalBytes = 2_400_000_000L,
            previewNames = listOf("IMG_001.jpg", "vidéo.mp4"),
        )
        assertEquals(offer, ControlCodec.decode(ControlCodec.encode(offer)))
    }

    @Test
    fun `l apercu est tronque a la limite annoncee`() {
        val offer = ControlMessage.Offer(
            sessionId = "s",
            deviceName = "n",
            deviceModel = "m",
            fileCount = 5_000,
            totalBytes = 1,
            previewNames = (1..100).map { "fichier$it.txt" },
        )
        val decoded = ControlCodec.decode(ControlCodec.encode(offer)) as ControlMessage.Offer
        assertEquals(ControlCodec.PREVIEW_LIMIT, decoded.previewNames.size)
    }

    @Test
    fun `les messages simples survivent a un aller-retour`() {
        assertEquals(ControlMessage.Accept, ControlCodec.decode(ControlCodec.encode(ControlMessage.Accept)))
        assertEquals(
            ControlMessage.TransferEnd,
            ControlCodec.decode(ControlCodec.encode(ControlMessage.TransferEnd)),
        )
        val reject = ControlMessage.Reject("Refusé par le destinataire")
        assertEquals(reject, ControlCodec.decode(ControlCodec.encode(reject)))
        val cancel = ControlMessage.Cancel("Annulé")
        assertEquals(cancel, ControlCodec.decode(ControlCodec.encode(cancel)))
    }

    @Test
    fun `les metadonnees de fichier survivent a un aller-retour`() {
        val start = ControlMessage.FileStart(
            index = 3,
            meta = FileMeta(
                name = "IMG_003.jpg",
                relativePath = "Voyage Mexico/Jour 02",
                size = 18_700_000_000L,
                mimeType = "image/jpeg",
            ),
        )
        assertEquals(start, ControlCodec.decode(ControlCodec.encode(start)))
        val end = ControlMessage.FileEnd(3, 18_700_000_000L)
        assertEquals(end, ControlCodec.decode(ControlCodec.encode(end)))
    }

    @Test
    fun `une trame de donnees est reconnue sans etre desserialisee`() {
        val frame = ByteArray(1 + 4096)
        frame[0] = ControlCodec.TYPE_FILE_DATA.toByte()
        val message = ControlCodec.decode(frame, frame.size)
        assertTrue(message is ControlMessage.FileData)
        assertEquals(4096, (message as ControlMessage.FileData).length)
    }

    @Test
    fun `un type inconnu est rejete`() {
        val frame = byteArrayOf(99, 0, 0)
        assertThrows(ProtocolException::class.java) { ControlCodec.decode(frame) }
    }

    @Test
    fun `un nombre de fichiers aberrant est rejete`() {
        val valid = ControlCodec.encode(
            ControlMessage.Offer("s", "n", "m", 1, 1, emptyList()),
        )
        // On corrompt le champ fileCount, situé après les trois chaînes.
        val corrupted = valid.copyOf()
        val offsetOfCount = corrupted.size - 4 - 8 - 4
        corrupted[offsetOfCount] = 0x7F
        assertThrows(ProtocolException::class.java) { ControlCodec.decode(corrupted) }
    }
}
