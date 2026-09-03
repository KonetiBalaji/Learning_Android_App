package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test
import javax.crypto.AEADBadTagException
import javax.crypto.spec.SecretKeySpec
import java.util.Base64

class TokenCipherTest {
    private fun cipher(value: Byte = 1) = TokenCipher(SecretKeySpec(ByteArray(32) { value }, "AES"))

    @Test fun encryptedSessionsRoundTripWithUniqueNonces() {
        val token = "synthetic-session-token"
        val first = cipher().encrypt(token)
        val second = cipher().encrypt(token)
        assertNotEquals(first, second)
        assertFalse(first.contains(token))
        assertEquals(token, cipher().decrypt(first))
        assertEquals(token, cipher().decrypt(second))
    }

    @Test(expected = AEADBadTagException::class)
    fun wrongKeyCannotDecrypt() { cipher(2).decrypt(cipher().encrypt("synthetic-token")) }

    @Test(expected = AEADBadTagException::class)
    fun modifiedCiphertextCannotDecrypt() {
        val parts = cipher().encrypt("synthetic-token").split(':').toMutableList()
        val bytes = Base64.getDecoder().decode(parts[2])
        bytes[0] = (bytes[0].toInt() xor 1).toByte()
        parts[2] = Base64.getEncoder().encodeToString(bytes)
        cipher().decrypt(parts.joinToString(":"))
    }

    @Test fun rejectsInvalidEnvelopesAndEmptyTokens() {
        listOf("", "plaintext-token", "v2:a:b", "v1:!:?", "v1:YQ==:Yg==").forEach {
            assertThrows(IllegalArgumentException::class.java) { cipher().decrypt(it) }
        }
        assertThrows(IllegalArgumentException::class.java) { cipher().encrypt(" ") }
    }
}
