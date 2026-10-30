package com.studycompanion.data

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okio.BufferedSink
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.security.KeyStore
import java.util.concurrent.TimeUnit
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class ApiException(val status: Int, message: String) : IOException(message)

/** Token encryption uses a non-exportable Android Keystore key; backups are disabled. */
class SessionStore(context: Context) {
    private val prefs = context.getSharedPreferences("session", Context.MODE_PRIVATE)
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        return store.getKey("study-session", null) as? SecretKey ?: KeyGenerator.getInstance("AES", "AndroidKeyStore").run {
            init(KeyGenParameterSpec.Builder("study-session", KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
            generateKey()
        }
    }
    var token: String
        get() = runCatching {
            val value = prefs.getString("token", null) ?: return ""
            val bytes = Base64.decode(value, Base64.NO_WRAP)
            Cipher.getInstance("AES/GCM/NoPadding").run {
                init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, bytes.copyOfRange(0, 12)))
                String(doFinal(bytes.copyOfRange(12, bytes.size)), Charsets.UTF_8)
            }
        }.getOrDefault("")
        set(value) {
            if (value.isEmpty()) prefs.edit().remove("token").apply()
            else {
                val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, key()) }
                val encrypted = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
                prefs.edit().putString("token", Base64.encodeToString(cipher.iv + encrypted, Base64.NO_WRAP)).apply()
            }
        }
    var server: String
        get() = prefs.getString("server", "http://10.0.2.2:8000")!!
        set(value) { prefs.edit().putString("server", value.trim().trimEnd('/')).apply() }
    var activeQuiz: String
        get() = prefs.getString("quiz", "")!!
        set(value) { prefs.edit().putString("quiz", value).apply() }
    var ownerId: String
        get() = prefs.getString("owner", "")!!
        set(value) { prefs.edit().putString("owner", value).apply() }
}

class StudyRepository(private val context: Context, val session: SessionStore) {
    private val client = OkHttpClient.Builder().connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(210, TimeUnit.SECONDS).writeTimeout(120, TimeUnit.SECONDS).build()

    suspend fun call(path: String, method: String = "GET", body: JSONObject? = null): String = withContext(Dispatchers.IO) {
        val payload = body?.toString()?.toRequestBody("application/json".toMediaType())
            ?: if (method == "POST") "{}".toRequestBody("application/json".toMediaType()) else null
        execute(Request.Builder().url(session.server + path).method(method, payload))
    }

    private fun execute(builder: Request.Builder): String {
        if (session.token.isNotEmpty()) builder.header("Authorization", "Bearer ${session.token}")
        return client.newCall(builder.build()).execute().use { response ->
            val text = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                val detail = runCatching { JSONObject(text).opt("detail") }.getOrNull()
                throw ApiException(response.code, if (detail is String) detail else "Request failed (${response.code}). Check your entries and retry.")
            }
            text
        }
    }

    suspend fun upload(uri: Uri, onProgress: (Int) -> Unit): JSONObject = withContext(Dispatchers.IO) {
        val resolver = context.contentResolver
        var name = if (uri.scheme == "file") uri.lastPathSegment ?: "document.txt" else "document.txt"
        var length = -1L
        resolver.query(uri, null, null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) {
                cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME).takeIf { it >= 0 }?.let { name = cursor.getString(it) }
                cursor.getColumnIndex(OpenableColumns.SIZE).takeIf { it >= 0 && !cursor.isNull(it) }?.let { length = cursor.getLong(it) }
            }
        }
        require(length <= 50L * 1024 * 1024) { "Choose a file up to 50 MB." }
        val fileBody = object : RequestBody() {
            override fun contentType() = "application/octet-stream".toMediaType()
            override fun contentLength() = length
            override fun writeTo(sink: BufferedSink) {
                resolver.openInputStream(uri)?.use { input ->
                    val buffer = ByteArray(8192)
                    var total = 0L
                    var last = -1
                    while (true) {
                        val count = input.read(buffer)
                        if (count < 0) break
                        total += count
                        require(total <= 50L * 1024 * 1024) { "Choose a file up to 50 MB." }
                        sink.write(buffer, 0, count)
                        val progress = if (length > 0) (total * 100 / length).toInt().coerceIn(0, 100) else 0
                        if (progress != last) { onProgress(progress); last = progress }
                    }
                } ?: throw IOException("Cannot read this file. Choose it again.")
            }
        }
        val multipart = okhttp3.MultipartBody.Builder().setType(okhttp3.MultipartBody.FORM)
            .addFormDataPart("file", name, fileBody).build()
        JSONObject(execute(Request.Builder().url(session.server + "/documents").post(multipart)))
    }
}

fun JSONArray.objects(): List<JSONObject> = (0 until length()).map { getJSONObject(it) }
fun JSONArray.strings(): List<String> = (0 until length()).map { getString(it) }
