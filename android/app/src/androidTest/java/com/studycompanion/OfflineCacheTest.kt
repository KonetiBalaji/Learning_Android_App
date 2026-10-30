package com.studycompanion

import androidx.room.Room
import androidx.test.platform.app.InstrumentationRegistry
import com.studycompanion.data.OfflineCache
import com.studycompanion.data.OfflineDatabase
import kotlinx.coroutines.runBlocking
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class OfflineCacheTest {
    @Test fun encryptedCacheSurvivesReopenIsolatesOwnersAndExpires() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        var cache = OfflineCache(context)
        cache.clear()
        val now = System.currentTimeMillis()
        val bundle = JSONObject().put("schema_version", 1).put("owner_id", "fixture-owner")
            .put("cached_at", now / 1000.0).put("expires_at", (now + 60_000) / 1000.0)
            .put("source_fingerprint", "fixture-revision")
            .put("document", JSONObject().put("id", "fixture-document").put("title", "Private Biology Title").put("processing_state", "ready"))
            .put("passages", JSONArray().put(JSONObject().put("text", "Private mitochondria passage")))
        try {
            cache.save("https://fixture.invalid", "fixture-owner", bundle, now)
            cache.close()
            cache = OfflineCache(context)
            assertEquals("Private Biology Title", cache.documents("https://fixture.invalid", "fixture-owner", now).single().getString("title"))
            assertNull(cache.load("https://fixture.invalid", "other-owner", "fixture-document", now))
            assertNull(cache.load("https://other.invalid", "fixture-owner", "fixture-document", now))
            val db = Room.databaseBuilder(context, OfflineDatabase::class.java, "offline-study.db").build()
            try {
                val row = db.records().all(OfflineCache.scope("https://fixture.invalid", "fixture-owner")).single()
                assertFalse(String(row.payload, Charsets.ISO_8859_1).contains("mitochondria"))
                assertFalse(String(row.payload, Charsets.ISO_8859_1).contains("Biology"))
                // Expiry metadata is authenticated, so extending it cannot extend the lease.
                row.expiresAt += 60_000
                db.records().save(row)
                var rejected = false
                try { cache.load("https://fixture.invalid", "fixture-owner", "fixture-document", now) }
                catch (_: java.security.GeneralSecurityException) { rejected = true }
                assertTrue(rejected)
            } finally { db.close() }
            cache.save("https://fixture.invalid", "fixture-owner", bundle, now)
            assertNull(cache.load("https://fixture.invalid", "fixture-owner", "fixture-document", now + 61_000))
            assertTrue(cache.documents("https://fixture.invalid", "fixture-owner", now + 61_000).isEmpty())
            cache.save("https://fixture.invalid", "fixture-owner", bundle, now)
            cache.clear()
            assertNull(cache.load("https://fixture.invalid", "fixture-owner", "fixture-document", now))
        } finally { cache.clear(); cache.close() }
    }

    @Test fun cacheRejectsWrongOwnerUnreviewedSourceAndRollback() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val cache = OfflineCache(context)
        val now = System.currentTimeMillis()
        val bundle = JSONObject().put("schema_version", 1).put("owner_id", "owner")
            .put("cached_at", now / 1000.0).put("expires_at", (now + 60_000) / 1000.0)
            .put("document", JSONObject().put("id", "doc").put("processing_state", "needs_review"))
        try {
            cache.clear()
            for (owner in listOf("owner", "other")) {
                var rejected = false
                try { cache.save("https://fixture.invalid", owner, bundle, now) }
                catch (_: IllegalArgumentException) { rejected = true }
                assertTrue(rejected)
            }
            bundle.getJSONObject("document").put("processing_state", "ready")
            cache.save("https://fixture.invalid", "owner", bundle, now)
            var rejected = false
            try { cache.load("https://fixture.invalid", "owner", "doc", now - 600_000) }
            catch (_: IllegalStateException) { rejected = true }
            assertTrue(rejected)
        } finally { cache.clear(); cache.close() }
    }
}
