package com.studycompanion.data

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import androidx.room.Room
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.security.KeyStore
import java.security.MessageDigest
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Explicit, bounded downloads. No source text or document title is stored in SQLite plaintext. */
class OfflineCache(context: Context) {
    private val database = Room.databaseBuilder(context.applicationContext, OfflineDatabase::class.java, "offline-study.db").build()
    private val records = database.records()

    companion object {
        private val keyLock = Any()
        private const val PREFIX = "study-offline-"
        private const val MAX_BYTES = 12 * 1024 * 1024
        fun scope(server: String, owner: String): String {
            require(owner.isNotBlank()) { "Sign in online before saving offline material." }
            return digest(server.trimEnd('/') + "\n" + owner)
        }
        private fun digest(value: String) = MessageDigest.getInstance("SHA-256").digest(value.toByteArray()).joinToString("") { "%02x".format(it) }
    }

    private fun key(scope: String, create: Boolean): SecretKey = synchronized(keyLock) {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(PREFIX + scope, null) as? SecretKey) ?: run {
            check(create) { "Offline encryption key is unavailable. Save the material again while online." }
            KeyGenerator.getInstance("AES", "AndroidKeyStore").run {
                init(KeyGenParameterSpec.Builder(PREFIX + scope, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
                generateKey()
            }
        }
    }

    private fun aad(record: OfflineRecord) = "${record.scope}\n${record.id}\n${record.expiresAt}".toByteArray()
    private fun recordId(scope: String, document: String) = digest(scope + "\n" + document)

    suspend fun save(server: String, owner: String, bundle: JSONObject, now: Long = System.currentTimeMillis()) = withContext(Dispatchers.IO) {
        require(bundle.getInt("schema_version") == 1 && bundle.getString("owner_id") == owner) { "Offline material belongs to a different account or version." }
        require(bundle.getJSONObject("document").optString("processing_state", "ready") == "ready") { "Review uncertain scanned text before saving offline." }
        val scope = scope(server, owner)
        val id = recordId(scope, bundle.getJSONObject("document").getString("id"))
        val created = (bundle.getDouble("cached_at") * 1000).toLong()
        val expires = (bundle.getDouble("expires_at") * 1000).toLong()
        require(created <= now + 300_000 && expires > now && expires <= created + 30L * 86400_000) { "Offline material has expired or its timestamps are invalid. Download it again." }
        val bytes = bundle.toString().toByteArray(Charsets.UTF_8)
        require(bytes.size <= MAX_BYTES) { "This document is too large for the offline cache (12 MB)." }
        records.purge(now)
        require(records.get(scope, id) != null || records.all(scope).size < 5) { "Five documents are already saved offline. Remove one before saving another." }
        val record = OfflineRecord().also { it.id = id; it.scope = scope; it.expiresAt = expires }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, key(scope, true)); updateAAD(aad(record)) }
        record.payload = cipher.iv + cipher.doFinal(bytes)
        records.save(record)
    }

    private fun decode(record: OfflineRecord, now: Long): JSONObject {
        check(record.expiresAt > now) { "Offline material expired. Download it again." }
        val bytes = record.payload
        require(bytes.size in 29..MAX_BYTES + 28) { "Offline material is damaged. Download it again." }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply {
            init(Cipher.DECRYPT_MODE, key(record.scope, false), GCMParameterSpec(128, bytes.copyOfRange(0, 12)))
            updateAAD(aad(record))
        }
        val bundle = JSONObject(String(cipher.doFinal(bytes.copyOfRange(12, bytes.size)), Charsets.UTF_8))
        check(now + 300_000 >= (bundle.getDouble("cached_at") * 1000).toLong()) { "Device clock moved backwards. Reconnect before studying offline." }
        return bundle
    }

    suspend fun load(server: String, owner: String, document: String, now: Long = System.currentTimeMillis()): JSONObject? = withContext(Dispatchers.IO) {
        records.purge(now)
        val scope = scope(server, owner)
        records.get(scope, recordId(scope, document))?.let { decode(it, now) }
    }

    suspend fun documents(server: String, owner: String, now: Long = System.currentTimeMillis()): List<JSONObject> = withContext(Dispatchers.IO) {
        records.purge(now)
        records.all(scope(server, owner)).map { decode(it, now).getJSONObject("document") }
    }

    suspend fun remove(server: String, owner: String, document: String) = withContext(Dispatchers.IO) {
        val scope = scope(server, owner)
        records.delete(scope, recordId(scope, document))
    }

    suspend fun clear() = withContext(Dispatchers.IO) {
        records.clear()
        synchronized(keyLock) {
            val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
            store.aliases().toList().filter { it.startsWith(PREFIX) }.forEach(store::deleteEntry)
        }
    }

    fun close() = database.close()
}
