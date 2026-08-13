package com.filedrop.app.storage

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PathSanitizerTest {

    @Test
    fun `un nom normal est conserve tel quel`() {
        assertEquals("IMG_001.jpg", PathSanitizer.sanitizeName("IMG_001.jpg"))
        assertEquals("Rapport final - v2.pdf", PathSanitizer.sanitizeName("Rapport final - v2.pdf"))
    }

    @Test
    fun `la remontee d arborescence est neutralisee`() {
        assertEquals(emptyList<String>(), PathSanitizer.sanitizeRelativePath("../.."))
        assertEquals(
            listOf("etc", "passwd"),
            PathSanitizer.sanitizeRelativePath("../../etc/passwd"),
        )
        assertEquals("fichier", PathSanitizer.sanitizeName(".."))
    }

    @Test
    fun `les separateurs sont retires des noms`() {
        val cleaned = PathSanitizer.sanitizeName("dossier/sous/fichier.txt")
        assertFalse(cleaned.contains('/'))
        assertEquals("dossier_sous_fichier.txt", cleaned)
    }

    @Test
    fun `une arborescence legitime est preservee`() {
        assertEquals(
            listOf("Voyage Mexico", "Jour 01"),
            PathSanitizer.sanitizeRelativePath("Voyage Mexico/Jour 01"),
        )
        assertEquals("Voyage Mexico/Jour 01", PathSanitizer.joinRelativePath("Voyage Mexico/Jour 01/"))
    }

    @Test
    fun `la profondeur et la longueur sont bornees`() {
        val deep = (1..50).joinToString("/") { "niveau$it" }
        assertTrue(PathSanitizer.sanitizeRelativePath(deep).size <= 16)

        val long = "a".repeat(400) + ".jpg"
        val cleaned = PathSanitizer.sanitizeName(long)
        assertTrue(cleaned.length <= 120)
        assertTrue(cleaned.endsWith(".jpg"))
    }

    @Test
    fun `un nom vide donne un nom de repli`() {
        assertEquals("fichier", PathSanitizer.sanitizeName("   "))
        assertEquals("fichier", PathSanitizer.sanitizeName("."))
    }
}
