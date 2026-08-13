package com.filedrop.app.transfer.protocol

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.IOException

class ProtocolException(message: String) : IOException(message)

/**
 * Sérialisation binaire des messages de contrôle.
 *
 * Pas de JSON ni de bibliothèque de sérialisation : le format est fixe, tient
 * en quelques dizaines de lignes, ne dépend d'aucune API Android et se teste
 * donc entièrement dans les tests unitaires JVM, qui tournent sur GitHub
 * Actions sans émulateur.
 */
object ControlCodec {

    const val TYPE_OFFER = 1
    const val TYPE_ACCEPT = 2
    const val TYPE_REJECT = 3
    const val TYPE_FILE_START = 4
    const val TYPE_FILE_DATA = 5
    const val TYPE_FILE_END = 6
    const val TYPE_TRANSFER_END = 7
    const val TYPE_CANCEL = 8

    /** Nombre de noms envoyés à titre d'aperçu dans l'offre. */
    const val PREVIEW_LIMIT = 20

    private const val MAX_FILE_COUNT = 500_000

    fun encode(message: ControlMessage): ByteArray {
        val bytes = ByteArrayOutputStream()
        val output = DataOutputStream(bytes)
        when (message) {
            is ControlMessage.Offer -> {
                output.writeByte(TYPE_OFFER)
                output.writeUTF(message.sessionId)
                output.writeUTF(message.deviceName)
                output.writeUTF(message.deviceModel)
                output.writeInt(message.fileCount)
                output.writeLong(message.totalBytes)
                val preview = message.previewNames.take(PREVIEW_LIMIT)
                output.writeInt(preview.size)
                preview.forEach { output.writeUTF(it) }
            }

            ControlMessage.Accept -> output.writeByte(TYPE_ACCEPT)

            is ControlMessage.Reject -> {
                output.writeByte(TYPE_REJECT)
                output.writeUTF(message.reason)
            }

            is ControlMessage.FileStart -> {
                output.writeByte(TYPE_FILE_START)
                output.writeInt(message.index)
                output.writeUTF(message.meta.name)
                output.writeUTF(message.meta.relativePath)
                output.writeLong(message.meta.size)
                output.writeUTF(message.meta.mimeType)
            }

            is ControlMessage.FileEnd -> {
                output.writeByte(TYPE_FILE_END)
                output.writeInt(message.index)
                output.writeLong(message.bytesSent)
            }

            ControlMessage.TransferEnd -> output.writeByte(TYPE_TRANSFER_END)

            is ControlMessage.Cancel -> {
                output.writeByte(TYPE_CANCEL)
                output.writeUTF(message.reason)
            }

            is ControlMessage.FileData ->
                throw ProtocolException("Les trames de données sont construites directement, pas encodées")
        }
        output.flush()
        return bytes.toByteArray()
    }

    fun decode(frame: ByteArray, length: Int = frame.size): ControlMessage {
        if (length < 1) throw ProtocolException("Trame vide")
        val type = frame[0].toInt() and 0xFF
        if (type == TYPE_FILE_DATA) {
            return ControlMessage.FileData(length - 1)
        }
        val input = DataInputStream(ByteArrayInputStream(frame, 1, length - 1))
        return try {
            when (type) {
                TYPE_OFFER -> {
                    val sessionId = input.readUTF()
                    val deviceName = input.readUTF()
                    val deviceModel = input.readUTF()
                    val fileCount = input.readInt()
                    val totalBytes = input.readLong()
                    if (fileCount < 0 || fileCount > MAX_FILE_COUNT) {
                        throw ProtocolException("Nombre de fichiers aberrant : $fileCount")
                    }
                    if (totalBytes < 0) {
                        throw ProtocolException("Taille totale aberrante : $totalBytes")
                    }
                    val previewCount = input.readInt()
                    if (previewCount < 0 || previewCount > PREVIEW_LIMIT) {
                        throw ProtocolException("Aperçu invalide : $previewCount entrées")
                    }
                    val preview = ArrayList<String>(previewCount)
                    repeat(previewCount) { preview.add(input.readUTF()) }
                    ControlMessage.Offer(
                        sessionId = sessionId,
                        deviceName = deviceName,
                        deviceModel = deviceModel,
                        fileCount = fileCount,
                        totalBytes = totalBytes,
                        previewNames = preview,
                    )
                }

                TYPE_ACCEPT -> ControlMessage.Accept

                TYPE_REJECT -> ControlMessage.Reject(input.readUTF())

                TYPE_FILE_START -> {
                    val index = input.readInt()
                    val name = input.readUTF()
                    val relativePath = input.readUTF()
                    val size = input.readLong()
                    val mimeType = input.readUTF()
                    if (size < 0) throw ProtocolException("Taille de fichier négative")
                    ControlMessage.FileStart(index, FileMeta(name, relativePath, size, mimeType))
                }

                TYPE_FILE_END -> ControlMessage.FileEnd(input.readInt(), input.readLong())

                TYPE_TRANSFER_END -> ControlMessage.TransferEnd

                TYPE_CANCEL -> ControlMessage.Cancel(input.readUTF())

                else -> throw ProtocolException("Type de message inconnu : $type")
            }
        } catch (error: ProtocolException) {
            throw error
        } catch (error: IOException) {
            throw ProtocolException("Message malformé (type $type) : ${error.message}")
        }
    }
}
