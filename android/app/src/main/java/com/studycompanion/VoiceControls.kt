package com.studycompanion

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import java.util.Locale

@Composable
fun DictateButton(enabled: Boolean, onTranscript: (String) -> Unit) {
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val deliver by rememberUpdatedState(onTranscript)
    val available by rememberUpdatedState(enabled)
    var recognizer by remember { mutableStateOf<SpeechRecognizer?>(null) }
    var status by remember { mutableStateOf<String?>(null) }

    fun stop() {
        val previous = recognizer
        recognizer = null
        previous?.cancel()
        previous?.destroy()
    }

    val hasMicrophone = context.packageManager.hasSystemFeature(PackageManager.FEATURE_MICROPHONE)

    fun begin() {
        if (!hasMicrophone || Build.VERSION.SDK_INT < 31 || !SpeechRecognizer.isOnDeviceRecognitionAvailable(context)) {
            status = "On-device dictation is unavailable. You can type your response."
            return
        }
        if (recognizer != null) return
        try {
            val session = SpeechRecognizer.createOnDeviceSpeechRecognizer(context)
            recognizer = session
            session.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) { if (recognizer === session) status = "Listening…" }
                override fun onBeginningOfSpeech() = Unit
                override fun onRmsChanged(rmsdB: Float) = Unit
                override fun onBufferReceived(buffer: ByteArray?) = Unit
                override fun onEndOfSpeech() { if (recognizer === session) status = "Preparing transcript…" }
                override fun onPartialResults(partialResults: Bundle?) = Unit
                override fun onEvent(eventType: Int, params: Bundle?) = Unit

                override fun onError(error: Int) {
                    if (recognizer !== session) return
                    stop()
                    status = "Could not transcribe on this device. Try again or type your response."
                }

                override fun onResults(results: Bundle?) {
                    if (recognizer !== session) return
                    val transcript = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        ?.firstOrNull()?.trim().orEmpty()
                    stop()
                    status = if (transcript.isBlank()) "No speech recognized. Try again or type your response."
                        else "Review the transcript before submitting."
                    if (transcript.isNotBlank() && available) deliver(transcript)
                }
            })
            status = "Starting dictation…"
            session.startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.ENGLISH.toLanguageTag())
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
                putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
            })
        } catch (_: RuntimeException) {
            stop()
            status = "Could not start on-device dictation. You can type your response."
        }
    }

    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted && available && lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED)) begin()
        else if (!granted) status = "Microphone access was declined. You can type your response."
    }
    LaunchedEffect(enabled) {
        if (!enabled && recognizer != null) {
            stop()
            status = null
        }
    }
    DisposableEffect(lifecycle) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_STOP && recognizer != null) {
                stop()
                status = null
            }
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer); stop() }
    }
    OutlinedButton(enabled = enabled, onClick = {
        when {
            recognizer != null -> { stop(); status = null }
            !hasMicrophone || Build.VERSION.SDK_INT < 31 || !SpeechRecognizer.isOnDeviceRecognitionAvailable(context) -> begin()
            ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED -> begin()
            else -> permission.launch(Manifest.permission.RECORD_AUDIO)
        }
    }) { Text(if (recognizer == null) "Dictate response" else "Cancel dictation") }
    status?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
}

@Composable
fun ReadAloudButton(text: String, label: String, onSpeakingChanged: (Boolean) -> Unit) {
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val mainHandler = remember { Handler(Looper.getMainLooper()) }
    var engine by remember { mutableStateOf<TextToSpeech?>(null) }
    var generation by remember { mutableStateOf(0) }
    var speaking by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf<String?>(null) }

    fun stop() {
        generation += 1
        speaking = false
        onSpeakingChanged(false)
        val previous = engine
        engine = null
        previous?.stop()
        previous?.shutdown()
    }

    DisposableEffect(lifecycle, text) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_STOP) stop()
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer); stop() }
    }

    TextButton(onClick = {
        if (speaking) {
            stop()
        } else {
            val request = ++generation
            speaking = true
            status = null
            engine = TextToSpeech(context.applicationContext) { initialized ->
                mainHandler.post {
                    if (generation == request) {
                        val voiceEngine = engine
                        val voice = if (initialized == TextToSpeech.SUCCESS)
                            voiceEngine?.voices?.firstOrNull {
                                it.locale.language == "en" && !it.isNetworkConnectionRequired &&
                                    "notInstalled" !in it.features.orEmpty()
                            } else null
                        if (voiceEngine == null || voice == null || voiceEngine.setVoice(voice) != TextToSpeech.SUCCESS) {
                            stop()
                            status = "An offline English voice is unavailable. You can read the text on screen."
                        } else {
                            voiceEngine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                                override fun onStart(utteranceId: String?) {
                                    mainHandler.post {
                                        if (generation == request) onSpeakingChanged(true)
                                    }
                                }
                                override fun onDone(utteranceId: String?) = finish(false)
                                @Deprecated("Required by the Android speech API")
                                override fun onError(utteranceId: String?) = finish(true)

                                private fun finish(failed: Boolean) {
                                    ContextCompat.getMainExecutor(context).execute {
                                        if (generation == request) {
                                            stop()
                                            if (failed) status = "Could not read this text aloud."
                                        }
                                    }
                                }
                            })
                            val spoken = voiceEngine.speak(text.take(TextToSpeech.getMaxSpeechInputLength()),
                                TextToSpeech.QUEUE_FLUSH, null, "saras-read-aloud")
                            if (spoken != TextToSpeech.SUCCESS) {
                                stop()
                                status = "Could not read this text aloud."
                            }
                        }
                    }
                }
            }
        }
    }) { Text(if (speaking) "Stop reading" else label) }
    status?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
}
