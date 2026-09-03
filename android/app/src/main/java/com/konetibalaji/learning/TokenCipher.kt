package com.konetibalaji.learning

import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Versioned authenticated envelope. Production keys come exclusively from AndroidKeyStore. */
class TokenCipher(private val key: SecretKey) {
    private val context = "learn-smart.session.v1".toByteArray(Charsets.UTF_8)

    fun encrypt(token: String): String {
        require(token.isNotBlank() && token.length <= 8192) { "Invalid session value" }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key)
        cipher.updateAAD(context)
        val encrypted = cipher.doFinal(token.toByteArray(Charsets.UTF_8))
        return "v1:${Base64.getEncoder().encodeToString(cipher.iv)}:${Base64.getEncoder().encodeToString(encrypted)}"
    }

    fun decrypt(envelope: String): String {
        require(envelope.length <= 16384) { "Invalid session envelope" }
        val parts = envelope.split(':')
        require(parts.size == 3 && parts[0] == "v1") { "Unsupported session envelope" }
        val iv = Base64.getDecoder().decode(parts[1])
        val encrypted = Base64.getDecoder().decode(parts[2])
        require(iv.size == 12 && encrypted.size > 16) { "Invalid session envelope" }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, iv))
        cipher.updateAAD(context)
        return cipher.doFinal(encrypted).toString(Charsets.UTF_8).also {
            require(it.isNotBlank() && it.length <= 8192) { "Invalid session value" }
        }
    }
}
