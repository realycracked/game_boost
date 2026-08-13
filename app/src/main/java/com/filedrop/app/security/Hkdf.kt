package com.filedrop.app.security

import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * HKDF-SHA256 (RFC 5869), implémenté avec les seules primitives fournies par
 * la plateforme. Aucune dépendance cryptographique externe n'est ajoutée :
 * `Mac`, `KeyAgreement`, `Cipher` et `Signature` sont dans le JDK Android.
 */
internal object Hkdf {

    private const val ALGORITHM = "HmacSHA256"
    private const val HASH_LENGTH = 32

    fun derive(inputKeyMaterial: ByteArray, salt: ByteArray, info: ByteArray, length: Int): ByteArray {
        require(length > 0 && length <= 255 * HASH_LENGTH) { "Longueur HKDF invalide : $length" }

        val mac = Mac.getInstance(ALGORITHM)

        // Extract
        mac.init(SecretKeySpec(if (salt.isEmpty()) ByteArray(HASH_LENGTH) else salt, ALGORITHM))
        val pseudoRandomKey = mac.doFinal(inputKeyMaterial)

        // Expand
        mac.init(SecretKeySpec(pseudoRandomKey, ALGORITHM))
        val output = ByteArray(length)
        var block = ByteArray(0)
        var position = 0
        var counter = 1
        while (position < length) {
            mac.reset()
            mac.update(block)
            mac.update(info)
            mac.update(counter.toByte())
            block = mac.doFinal()
            val take = minOf(block.size, length - position)
            System.arraycopy(block, 0, output, position, take)
            position += take
            counter++
        }
        return output
    }
}
