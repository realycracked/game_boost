package com.filedrop.app.security

import org.junit.Assert.assertEquals
import org.junit.Test

class HkdfTest {

    /** Vecteur d'essai n°1 de la RFC 5869 (HKDF-SHA256). */
    @Test
    fun `vecteur RFC 5869`() {
        val ikm = ByteArray(22) { 0x0b }
        val salt = ByteArray(13) { it.toByte() }
        val info = ByteArray(10) { (0xf0 + it).toByte() }

        val okm = Hkdf.derive(ikm, salt, info, 42)

        assertEquals(
            "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865",
            okm.toHex(),
        )
    }

    @Test
    fun `des labels differents donnent des cles differentes`() {
        val ikm = ByteArray(32) { 7 }
        val salt = ByteArray(16) { 3 }
        val first = Hkdf.derive(ikm, salt, "c2s".toByteArray(), 32)
        val second = Hkdf.derive(ikm, salt, "s2c".toByteArray(), 32)
        assertEquals(32, first.size)
        assertEquals(32, second.size)
        org.junit.Assert.assertNotEquals(first.toHex(), second.toHex())
    }

    private fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }
}
