package com.filedrop.app.security

import java.io.Closeable
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.EOFException
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * Canal chiffré en trames au-dessus d'un flux d'octets quelconque.
 *
 * Chaque trame est chiffrée en AES-256-GCM avec une clé propre au sens de
 * circulation et un nonce déterministe `préfixe(4 o) || compteur(8 o)`. Le
 * compteur ne se répète jamais dans une session, ce qui est la condition de
 * sûreté de GCM ; le tag d'authentification rend toute altération détectable,
 * y compris la réorganisation ou la suppression d'une trame (le compteur
 * attendu ne correspondrait plus).
 *
 * Le format réseau est volontairement trivial : `longueur(4 o) || chiffré`.
 */
class SecureChannel(
    input: InputStream,
    output: OutputStream,
    sendKey: ByteArray,
    private val sendNoncePrefix: ByteArray,
    receiveKey: ByteArray,
    private val receiveNoncePrefix: ByteArray,
) : Closeable {

    private val dataInput = DataInputStream(input)
    private val dataOutput = DataOutputStream(output)

    private val sendKeySpec = SecretKeySpec(sendKey, "AES")
    private val receiveKeySpec = SecretKeySpec(receiveKey, "AES")

    private val encryptCipher = Cipher.getInstance(TRANSFORMATION)
    private val decryptCipher = Cipher.getInstance(TRANSFORMATION)

    private val sendLock = Any()
    private val receiveLock = Any()

    private var sendCounter = 0L
    private var receiveCounter = 0L

    private var cipherTextBuffer = ByteArray(MAX_PLAINTEXT + TAG_BYTES)

    /** Envoie une trame. Le contenu de [data] n'est pas conservé. */
    @Throws(IOException::class)
    fun writeFrame(data: ByteArray, offset: Int = 0, length: Int = data.size) {
        require(length in 0..MAX_PLAINTEXT) { "Trame trop grande : $length" }
        synchronized(sendLock) {
            val nonce = buildNonce(sendNoncePrefix, sendCounter)
            sendCounter++
            encryptCipher.init(Cipher.ENCRYPT_MODE, sendKeySpec, GCMParameterSpec(TAG_BITS, nonce))
            val written = encryptCipher.doFinal(data, offset, length, cipherTextBuffer, 0)
            dataOutput.writeInt(written)
            dataOutput.write(cipherTextBuffer, 0, written)
            dataOutput.flush()
        }
    }

    /**
     * Lit une trame dans [destination] sans allouer.
     * Renvoie le nombre d'octets déchiffrés, ou -1 si le pair a fermé proprement.
     */
    @Throws(IOException::class)
    fun readFrameInto(destination: ByteArray): Int {
        synchronized(receiveLock) {
            val cipherLength = try {
                dataInput.readInt()
            } catch (end: EOFException) {
                return -1
            }
            if (cipherLength < TAG_BYTES || cipherLength > MAX_PLAINTEXT + TAG_BYTES) {
                throw IOException("Longueur de trame invalide : $cipherLength")
            }
            if (cipherTextBuffer.size < cipherLength) {
                cipherTextBuffer = ByteArray(cipherLength)
            }
            dataInput.readFully(cipherTextBuffer, 0, cipherLength)

            val nonce = buildNonce(receiveNoncePrefix, receiveCounter)
            receiveCounter++
            decryptCipher.init(Cipher.DECRYPT_MODE, receiveKeySpec, GCMParameterSpec(TAG_BITS, nonce))
            return decryptCipher.doFinal(cipherTextBuffer, 0, cipherLength, destination, 0)
        }
    }

    /** Variante allouante, pour les petits messages de contrôle. */
    @Throws(IOException::class)
    fun readFrame(): ByteArray? {
        val buffer = ByteArray(MAX_PLAINTEXT)
        val length = readFrameInto(buffer)
        if (length < 0) return null
        return buffer.copyOf(length)
    }

    private fun buildNonce(prefix: ByteArray, counter: Long): ByteArray {
        val nonce = ByteArray(NONCE_BYTES)
        System.arraycopy(prefix, 0, nonce, 0, prefix.size)
        var value = counter
        for (index in NONCE_BYTES - 1 downTo prefix.size) {
            nonce[index] = (value and 0xFF).toByte()
            value = value ushr 8
        }
        return nonce
    }

    override fun close() {
        runCatching { dataOutput.flush() }
        runCatching { dataInput.close() }
        runCatching { dataOutput.close() }
    }

    companion object {
        /** 64 Kio de données utiles par trame : bon compromis débit / mémoire. */
        const val CHUNK_SIZE = 64 * 1024

        /** Plafond dur : protège d'un pair malveillant qui annoncerait une trame énorme. */
        const val MAX_PLAINTEXT = 1 shl 20

        const val TAG_BITS = 128
        const val TAG_BYTES = TAG_BITS / 8
        const val NONCE_BYTES = 12
        const val NONCE_PREFIX_BYTES = 4
        const val KEY_BYTES = 32

        private const val TRANSFORMATION = "AES/GCM/NoPadding"
    }
}
