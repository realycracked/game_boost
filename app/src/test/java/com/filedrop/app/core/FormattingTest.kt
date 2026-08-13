package com.filedrop.app.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class FormattingTest {

    @Test
    fun `les petites tailles restent en octets`() {
        assertEquals("0 o", formatBytes(0))
        assertEquals("999 o", formatBytes(999))
    }

    @Test
    fun `les grandes tailles changent d unite`() {
        assertTrue(formatBytes(1_000).endsWith(" ko"))
        assertTrue(formatBytes(842_000_000).endsWith(" Mo"))
        assertTrue(formatBytes(2_400_000_000L).endsWith(" Go"))
        assertTrue(formatBytes(18_700_000_000L).endsWith(" Go"))
    }

    @Test
    fun `une taille inconnue est signalee`() {
        assertEquals("—", formatBytes(-1))
        assertEquals("—", formatSpeed(0))
    }

    @Test
    fun `les durees sont lisibles`() {
        assertEquals("45 s", formatDuration(45))
        assertEquals("6 min", formatDuration(6 * 60 + 12))
        assertEquals("1 h 12 min", formatDuration(72 * 60))
        assertEquals("2 h", formatDuration(2 * 3600))
        assertEquals("—", formatDuration(-1))
    }

    @Test
    fun `le pluriel des fichiers est correct`() {
        assertEquals("1 fichier", formatFileCount(1))
        assertEquals("12 fichiers", formatFileCount(12))
    }
}
