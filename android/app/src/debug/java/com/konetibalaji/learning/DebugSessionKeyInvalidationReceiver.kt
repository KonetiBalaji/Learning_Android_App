package com.konetibalaji.learning

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import java.security.KeyStore

/** Debug-only device-QA hook. It is absent from every release APK. */
class DebugSessionKeyInvalidationReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (!BuildConfig.DEBUG || intent.action != INVALIDATE_SESSION_KEY_ACTION) return
        val preferences = context.getSharedPreferences("learn-smart", Context.MODE_PRIVATE)
        check(preferences.contains("session_ciphertext")) {
            "A persisted encrypted session is required before invalidation"
        }
        KeyStore.getInstance("AndroidKeyStore").apply {
            load(null)
            check(containsAlias(SESSION_KEY_ALIAS)) { "Session key is missing" }
            deleteEntry(SESSION_KEY_ALIAS)
        }
    }
}

const val INVALIDATE_SESSION_KEY_ACTION =
    "com.konetibalaji.learning.debug.INVALIDATE_SESSION_KEY"
