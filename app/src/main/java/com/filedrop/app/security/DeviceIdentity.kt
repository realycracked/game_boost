package com.filedrop.app.security

import java.security.KeyFactory
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.PublicKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.PKCS8EncodedKeySpec
import java.security.spec.X509EncodedKeySpec

/**
 * Identité cryptographique durable de l'appareil : une paire de clés EC P-256.
 *
 * Elle sert à signer la poignée de main de chaque session, ce qui permet
 * d'authentifier l'appareil en face **sans code PIN** : l'utilisateur voit le
 * nom et l'empreinte de l'appareil, et un appareil déjà rencontré est reconnu
 * parce qu'il présente la même clé (confiance à la première utilisation).
 */
class DeviceIdentity(val keyPair: KeyPair) {

    val publicKeyEncoded: ByteArray get() = keyPair.public.encoded
    val fingerprint: String by lazy { Fingerprint.of(publicKeyEncoded) }

    companion object {
        const val CURVE = "secp256r1"
        const val KEY_ALGORITHM = "EC"
        const val SIGNATURE_ALGORITHM = "SHA256withECDSA"

        fun generate(): DeviceIdentity {
            val generator = KeyPairGenerator.getInstance(KEY_ALGORITHM)
            generator.initialize(ECGenParameterSpec(CURVE))
            return DeviceIdentity(generator.generateKeyPair())
        }

        fun fromEncoded(privateKeyPkcs8: ByteArray, publicKeyX509: ByteArray): DeviceIdentity {
            val factory = KeyFactory.getInstance(KEY_ALGORITHM)
            val privateKey = factory.generatePrivate(PKCS8EncodedKeySpec(privateKeyPkcs8))
            val publicKey = factory.generatePublic(X509EncodedKeySpec(publicKeyX509))
            return DeviceIdentity(KeyPair(publicKey, privateKey))
        }

        fun decodePublicKey(encoded: ByteArray): PublicKey =
            KeyFactory.getInstance(KEY_ALGORITHM).generatePublic(X509EncodedKeySpec(encoded))
    }
}
