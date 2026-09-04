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
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import java.util.Locale

const val LEARNING_SPEECH_RATE = 0.8f

@Composable
fun ReadAloudControls(text: String, onReadingChanged: (Boolean) -> Unit = {}) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val playback = remember { SpeechPlayback() }
    var reading by remember { mutableStateOf(false) }
    var speaker by remember { mutableStateOf<TextToSpeech?>(null) }
    var ready by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("Preparing read-aloud…") }
    LaunchedEffect(reading) { onReadingChanged(reading) }
    DisposableEffect(context) {
        val main = Handler(Looper.getMainLooper())
        var disposed = false
        val engine = TextToSpeech(context) { status ->
            main.post {
                if (!disposed) {
                    val language = if (status == TextToSpeech.SUCCESS) speaker?.setLanguage(Locale.ENGLISH) else null
                    val rate = if (language != null && language >= TextToSpeech.LANG_AVAILABLE) speaker?.setSpeechRate(LEARNING_SPEECH_RATE) else null
                    ready = rate == TextToSpeech.SUCCESS
                    message = if (ready) "Read-aloud uses your device's speech service." else "English read-aloud is unavailable. You can still read the lesson below."
                }
            }
        }
        speaker = engine
        engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {}
            override fun onDone(utteranceId: String?) { main.post {
                if (!disposed && playback.complete(utteranceId)) {
                    reading = false
                    message = "Finished reading."
                }
            } }
            private fun failed(utteranceId: String?) { main.post {
                if (!disposed && playback.fail(utteranceId)) {
                    engine.stop()
                    reading = false
                    message = "Read-aloud failed. Try again or read the lesson text."
                }
            } }
            @Deprecated("Required legacy callback")
            override fun onError(utteranceId: String?) { failed(utteranceId) }
            override fun onError(utteranceId: String?, errorCode: Int) { failed(utteranceId) }
        })
        onDispose { disposed = true; playback.stop(); reading = false; ready = false; engine.stop(); engine.shutdown(); speaker = null }
    }
    DisposableEffect(lifecycleOwner, text) {
        fun stopReading() {
            if (playback.stop()) {
                reading = false
                speaker?.stop()
                message = "Reading stopped. Tap Read explanation aloud to restart."
            }
        }
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_STOP) stopReading()
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer); stopReading() }
    }
    OutlinedButton(enabled = ready && text.isNotBlank(), onClick = {
        val chunks = speechChunks(text, TextToSpeech.getMaxSpeechInputLength())
        playback.stop()
        speaker?.stop()
        val ids = playback.begin(chunks.size)
        reading = true
        message = "Reading explanation…"
        for ((index, chunk) in chunks.withIndex()) {
            if (speaker?.speak(chunk, TextToSpeech.QUEUE_ADD, null, ids[index]) != TextToSpeech.SUCCESS) {
                playback.stop()
                reading = false
                speaker?.stop()
                message = "Read-aloud failed. Try again or read the lesson text."
                break
            }
        }
    }, modifier = Modifier.fillMaxWidth()) { Text("Read explanation aloud") }
    OutlinedButton(enabled = reading, onClick = {
        playback.stop(); reading = false; speaker?.stop(); message = "Reading stopped."
    }, modifier = Modifier.fillMaxWidth()) { Text("Stop reading") }
    Text(message, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
}
