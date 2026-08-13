package com.filedrop.app.security

import java.security.MessageDigest

/**
 * Empreinte courte et lisible d'une clé publique, du type `A7F2-90BC-31D4`.
 *
 * Elle sert à deux choses :
 *  - identifier durablement un appareil connu (confiance à la première
 *    utilisation), même si son nom change ;
 *  - permettre à l'utilisateur de comparer visuellement deux appareils s'il a
 *    un doute, sans imposer de code PIN à chaque transfert.
 */
object Fingerprint {

    private const val BYTES_SHOWN = 6
    private val HEX = "0123456789ABCDEF".toCharArray()

    fun of(publicKeyEncoded: ByteArray): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(publicKeyEncoded)
        val builder = StringBuilder()
        for (index in 0 until BYTES_SHOWN) {
            if (index > 0 && index % 2 == 0) builder.append('-')
            val value = digest[index].toInt() and 0xFF
            builder.append(HEX[value ushr 4])
            builder.append(HEX[value and 0x0F])
        }
        return builder.toString()
    }
}
