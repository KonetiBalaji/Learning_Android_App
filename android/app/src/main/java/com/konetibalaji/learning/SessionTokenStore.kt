package com.konetibalaji.learning

import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

/** Call on an IO dispatcher. No plaintext fallback; migrations commit atomically. */
class SessionTokenStore(private val preferences: SharedPreferences, private val alias: String = "learn-smart-session-v1") {
    private fun cipher(): TokenCipher {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = store.getKey(alias, null) as? SecretKey
        val key = existing ?: KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").run {
            init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .setKeySize(256)
                .build())
            generateKey()
        }
        return TokenCipher(key)
    }

    @Synchronized fun read(): String? {
        return try {
            val sealed = preferences.getString("session_ciphertext", null)
            if (sealed != null) {
                val token = cipher().decrypt(sealed)
                if (preferences.contains("token")) check(preferences.edit().remove("token").commit())
                token
            } else {
                preferences.getString("token", null)?.also { write(it) }
            }
        } catch (_: Exception) {
            // Missing/invalidated key, altered ciphertext or migration failure => fresh login.
            clear()
            null
        }
    }

    @Synchronized fun write(token: String) {
        val sealed = cipher().encrypt(token)
        check(preferences.edit().putString("session_ciphertext", sealed).remove("token").commit()) {
            "Unable to save the session securely"
        }
    }

    @Synchronized fun clear() {
        check(preferences.edit().remove("session_ciphertext").remove("token").commit()) {
            "Unable to clear the saved session"
        }
    }
}
