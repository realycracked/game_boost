package com.filedrop.app.security

import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import javax.crypto.KeyAgreement

class HandshakeException(message: String, cause: Throwable? = null) : IOException(message, cause)

/**
 * Poignée de main de session, sans code PIN ni mot de passe.
 *
 * Déroulé :
 *
 * ```
 * client → serveur : "FDRP" | version | clé d'identité client | clé éphémère client
 * serveur → client : clé d'identité serveur | clé éphémère serveur | signature serveur
 * client → serveur : signature client
 * ```
 *
 * Les deux côtés dérivent ensuite un secret par ECDH sur les clés éphémères,
 * puis quatre valeurs par HKDF (une clé et un préfixe de nonce par sens).
 *
 * Ce que cela garantit :
 *  - **confidentialité et intégrité** : tout ce qui suit est chiffré et
 *    authentifié en AES-GCM, y compris le contenu des fichiers ;
 *  - **authentification de la session** : chaque camp signe les deux clés
 *    éphémères avec sa clé d'identité durable, donc personne ne peut se glisser
 *    au milieu sans être détecté *si l'empreinte présentée est déjà connue*.
 *
 * Ce que cela ne garantit pas, et qui est assumé : au tout premier contact avec
 * un appareil, rien ne prouve que l'empreinte affichée est la bonne. C'est le
 * modèle « confiance à la première utilisation ». Le remplacer imposerait un
 * code à comparer, que le cahier des charges exclut explicitement. L'empreinte
 * est donc affichée à l'écran pour qu'une vérification reste possible.
 */
object Handshake {

    const val PROTOCOL_VERSION = 1

    private val MAGIC = byteArrayOf(0x46, 0x44, 0x52, 0x50) // "FDRP"
    private const val MAX_BLOB_BYTES = 4096

    private val LABEL_SERVER = "FileDrop/v1/server".toByteArray()
    private val LABEL_CLIENT = "FileDrop/v1/client".toByteArray()
    private val INFO_C2S_KEY = "FileDrop/v1/c2s/key".toByteArray()
    private val INFO_C2S_NONCE = "FileDrop/v1/c2s/nonce".toByteArray()
    private val INFO_S2C_KEY = "FileDrop/v1/s2c/key".toByteArray()
    private val INFO_S2C_NONCE = "FileDrop/v1/s2c/nonce".toByteArray()

    class Result(val channel: SecureChannel, val peerIdentityPublicKey: ByteArray) {
        val peerFingerprint: String = Fingerprint.of(peerIdentityPublicKey)
    }

    /** Côté émetteur : c'est lui qui ouvre la connexion. */
    @Throws(IOException::class)
    fun asClient(input: InputStream, output: OutputStream, identity: DeviceIdentity): Result {
        val dataInput = DataInputStream(input)
        val dataOutput = DataOutputStream(output)
        val ephemeral = generateEphemeral()
        val clientEphemeral = ephemeral.public.encoded

        dataOutput.write(MAGIC)
        dataOutput.writeInt(PROTOCOL_VERSION)
        writeBlob(dataOutput, identity.publicKeyEncoded)
        writeBlob(dataOutput, clientEphemeral)
        dataOutput.flush()

        val serverIdentity = readBlob(dataInput)
        val serverEphemeral = readBlob(dataInput)
        val serverSignature = readBlob(dataInput)

        verify(serverIdentity, serverSignature, LABEL_SERVER, clientEphemeral, serverEphemeral)

        writeBlob(
            dataOutput,
            sign(identity, LABEL_CLIENT, clientEphemeral, serverEphemeral),
        )
        dataOutput.flush()

        val secrets = derive(ephemeral, serverEphemeral, clientEphemeral, serverEphemeral)
        FdLog.i(
            LogTags.SECURITY,
            "Session chiffrée établie (client) avec ${Fingerprint.of(serverIdentity)}",
        )
        return Result(
            SecureChannel(
                input = input,
                output = output,
                sendKey = secrets.clientToServerKey,
                sendNoncePrefix = secrets.clientToServerNonce,
                receiveKey = secrets.serverToClientKey,
                receiveNoncePrefix = secrets.serverToClientNonce,
            ),
            serverIdentity,
        )
    }

    /** Côté destinataire : il accepte la connexion entrante. */
    @Throws(IOException::class)
    fun asServer(input: InputStream, output: OutputStream, identity: DeviceIdentity): Result {
        val dataInput = DataInputStream(input)
        val dataOutput = DataOutputStream(output)

        val magic = ByteArray(MAGIC.size)
        dataInput.readFully(magic)
        if (!magic.contentEquals(MAGIC)) {
            throw HandshakeException("Ce n'est pas une connexion FileDrop")
        }
        val version = dataInput.readInt()
        if (version != PROTOCOL_VERSION) {
            throw HandshakeException(
                "Version de protocole incompatible : $version (attendu $PROTOCOL_VERSION). " +
                    "Mettez les deux appareils à jour avec le même APK.",
            )
        }

        val clientIdentity = readBlob(dataInput)
        val clientEphemeral = readBlob(dataInput)

        val ephemeral = generateEphemeral()
        val serverEphemeral = ephemeral.public.encoded

        writeBlob(dataOutput, identity.publicKeyEncoded)
        writeBlob(dataOutput, serverEphemeral)
        writeBlob(dataOutput, sign(identity, LABEL_SERVER, clientEphemeral, serverEphemeral))
        dataOutput.flush()

        val clientSignature = readBlob(dataInput)
        verify(clientIdentity, clientSignature, LABEL_CLIENT, clientEphemeral, serverEphemeral)

        val secrets = derive(ephemeral, clientEphemeral, clientEphemeral, serverEphemeral)
        FdLog.i(
            LogTags.SECURITY,
            "Session chiffrée établie (serveur) avec ${Fingerprint.of(clientIdentity)}",
        )
        return Result(
            SecureChannel(
                input = input,
                output = output,
                sendKey = secrets.serverToClientKey,
                sendNoncePrefix = secrets.serverToClientNonce,
                receiveKey = secrets.clientToServerKey,
                receiveNoncePrefix = secrets.clientToServerNonce,
            ),
            clientIdentity,
        )
    }

    private class Secrets(
        val clientToServerKey: ByteArray,
        val clientToServerNonce: ByteArray,
        val serverToClientKey: ByteArray,
        val serverToClientNonce: ByteArray,
    )

    private fun derive(
        ownEphemeral: KeyPair,
        peerEphemeralEncoded: ByteArray,
        clientEphemeral: ByteArray,
        serverEphemeral: ByteArray,
    ): Secrets {
        val agreement = KeyAgreement.getInstance("ECDH")
        agreement.init(ownEphemeral.private)
        agreement.doPhase(DeviceIdentity.decodePublicKey(peerEphemeralEncoded), true)
        val shared = agreement.generateSecret()

        val salt = MessageDigest.getInstance("SHA-256").apply {
            update(clientEphemeral)
            update(serverEphemeral)
        }.digest()

        return Secrets(
            clientToServerKey = Hkdf.derive(shared, salt, INFO_C2S_KEY, SecureChannel.KEY_BYTES),
            clientToServerNonce = Hkdf.derive(shared, salt, INFO_C2S_NONCE, SecureChannel.NONCE_PREFIX_BYTES),
            serverToClientKey = Hkdf.derive(shared, salt, INFO_S2C_KEY, SecureChannel.KEY_BYTES),
            serverToClientNonce = Hkdf.derive(shared, salt, INFO_S2C_NONCE, SecureChannel.NONCE_PREFIX_BYTES),
        )
    }

    private fun generateEphemeral(): KeyPair {
        val generator = KeyPairGenerator.getInstance(DeviceIdentity.KEY_ALGORITHM)
        generator.initialize(ECGenParameterSpec(DeviceIdentity.CURVE))
        return generator.generateKeyPair()
    }

    private fun sign(
        identity: DeviceIdentity,
        label: ByteArray,
        clientEphemeral: ByteArray,
        serverEphemeral: ByteArray,
    ): ByteArray {
        val signature = Signature.getInstance(DeviceIdentity.SIGNATURE_ALGORITHM)
        signature.initSign(identity.keyPair.private)
        signature.update(label)
        signature.update(clientEphemeral)
        signature.update(serverEphemeral)
        return signature.sign()
    }

    private fun verify(
        peerIdentityEncoded: ByteArray,
        signatureBytes: ByteArray,
        label: ByteArray,
        clientEphemeral: ByteArray,
        serverEphemeral: ByteArray,
    ) {
        val valid = try {
            val signature = Signature.getInstance(DeviceIdentity.SIGNATURE_ALGORITHM)
            signature.initVerify(DeviceIdentity.decodePublicKey(peerIdentityEncoded))
            signature.update(label)
            signature.update(clientEphemeral)
            signature.update(serverEphemeral)
            signature.verify(signatureBytes)
        } catch (error: Exception) {
            throw HandshakeException("Signature de session illisible", error)
        }
        if (!valid) {
            throw HandshakeException("Signature de session invalide : connexion abandonnée")
        }
    }

    private fun writeBlob(output: DataOutputStream, bytes: ByteArray) {
        output.writeInt(bytes.size)
        output.write(bytes)
    }

    private fun readBlob(input: DataInputStream): ByteArray {
        val length = input.readInt()
        if (length !in 1..MAX_BLOB_BYTES) {
            throw HandshakeException("Bloc de poignée de main invalide : $length octets")
        }
        val bytes = ByteArray(length)
        input.readFully(bytes)
        return bytes
    }
}
