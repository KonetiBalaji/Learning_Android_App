package com.konetibalaji.learning

import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import java.util.Locale

@Composable
fun ReadAloudControls(text: String) {
    val context = LocalContext.current
    var speaker by remember { mutableStateOf<TextToSpeech?>(null) }
    var ready by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("Preparing read-aloud…") }
    DisposableEffect(context) {
        val main = Handler(Looper.getMainLooper())
        var disposed = false
        val engine = TextToSpeech(context) { status ->
            main.post {
                if (!disposed) {
                    val language = if (status == TextToSpeech.SUCCESS) speaker?.setLanguage(Locale.ENGLISH) else null
                    ready = language != null && language >= TextToSpeech.LANG_AVAILABLE
                    message = if (ready) "Read-aloud uses your device's speech service." else "English read-aloud is unavailable. You can still read the lesson below."
                }
            }
        }
        speaker = engine
        engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {}
            override fun onDone(utteranceId: String?) {}
            @Deprecated("Required legacy callback")
            override fun onError(utteranceId: String?) { main.post { if (!disposed) message = "Read-aloud failed. Try again or read the lesson text." } }
            override fun onError(utteranceId: String?, errorCode: Int) { main.post { if (!disposed) message = "Read-aloud failed. Try again or read the lesson text." } }
        })
        onDispose { disposed = true; ready = false; engine.stop(); engine.shutdown(); speaker = null }
    }
    OutlinedButton(enabled = ready && text.isNotBlank(), onClick = {
        val chunks = speechChunks(text, TextToSpeech.getMaxSpeechInputLength())
        speaker?.stop()
        message = "Read-aloud uses your device's speech service."
        for ((index, chunk) in chunks.withIndex()) {
            if (speaker?.speak(chunk, TextToSpeech.QUEUE_ADD, null, "lesson-$index") == TextToSpeech.ERROR) {
                speaker?.stop()
                message = "Read-aloud failed. Try again or read the lesson text."
                break
            }
        }
    }, modifier = Modifier.fillMaxWidth()) { Text("Read explanation aloud") }
    OutlinedButton(enabled = ready, onClick = { speaker?.stop() }, modifier = Modifier.fillMaxWidth()) { Text("Stop reading") }
    Text(message, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
}
