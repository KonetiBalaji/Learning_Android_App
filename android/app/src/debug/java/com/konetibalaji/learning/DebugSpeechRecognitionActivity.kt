package com.konetibalaji.learning

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent

/** Debug-only activity-result fixture. It is disabled in the merged manifest by default. */
class DebugSpeechRecognitionActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setResult(
            RESULT_OK,
            Intent().putStringArrayListExtra(
                RecognizerIntent.EXTRA_RESULTS,
                arrayListOf("\u0001\u0002", "  Why\u0001   does the denominator stay?  "),
            ),
        )
        finish()
    }
}
