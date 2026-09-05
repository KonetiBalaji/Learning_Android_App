package com.konetibalaji.learning

import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager

/** Explicit debug-only control for the otherwise disabled recognition fixture. */
class DebugSpeechFixtureReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val enabled = intent.action == ENABLE
        val state = if (enabled) PackageManager.COMPONENT_ENABLED_STATE_ENABLED
        else PackageManager.COMPONENT_ENABLED_STATE_DISABLED
        context.packageManager.setComponentEnabledSetting(
            ComponentName(context, DebugSpeechRecognitionActivity::class.java),
            state,
            PackageManager.DONT_KILL_APP,
        )
    }

    companion object {
        const val ENABLE = "com.konetibalaji.learning.debug.ENABLE_SPEECH_FIXTURE"
        const val DISABLE = "com.konetibalaji.learning.debug.DISABLE_SPEECH_FIXTURE"
    }
}
