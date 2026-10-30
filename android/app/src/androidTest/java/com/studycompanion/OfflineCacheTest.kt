package com.studycompanion

import androidx.room.Room
import androidx.test.platform.app.InstrumentationRegistry
import com.studycompanion.data.OfflineCache
import com.studycompanion.data.OfflineDatabase
import com.studycompanion.data.OfflineStudyRepository
import com.studycompanion.data.SessionStore
import kotlinx.coroutines.runBlocking
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class OfflineCacheTest {
    @Test fun localSessionsRespectScopePersistAndRejectConflictingAnswers() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val cache = OfflineCache(context)
        val session = SessionStore(context)
        val previousServer = session.server
        val previousOwner = session.ownerId
        session.server = "https://offline-fixture.invalid"
        session.ownerId = "session-fixture"
        val repository = OfflineStudyRepository(cache, session)
        val now = System.currentTimeMillis()
        val sections = JSONArray().put(JSONObject().put("id", "parent").put("title", "Cells"))
            .put(JSONObject().put("id", "child").put("title", "Energy").put("parent_id", "parent"))
            .put(JSONObject().put("id", "other").put("title", "Ecology"))
        val bundle = JSONObject().put("schema_version", 1).put("owner_id", session.ownerId)
            .put("cached_at", now / 1000.0).put("expires_at", (now + 3600_000) / 1000.0)
            .put("source_fingerprint", "fixture-source")
            .put("document", JSONObject().put("id", "doc").put("processing_state", "ready").put("sections", sections).put("has_real_pages", true).put("page_count", 3))
            .put("passages", JSONArray()
                .put(JSONObject().put("id", "energy").put("section_id", "child").put("page", 2).put("text", "Mitochondria produce usable energy through cellular respiration inside living cells."))
                .put(JSONObject().put("id", "ecology").put("section_id", "other").put("page", 3).put("text", "Decomposers break down dead material and recycle essential nutrients.")))
        try {
            cache.clear()
            cache.save(session.server, session.ownerId, bundle)
            var rejected = false
            try { repository.create("doc", setOf("missing"), null, null, 1, "multiple_choice") }
            catch (_: IllegalArgumentException) { rejected = true }
            assertTrue(rejected)
            val created = repository.create("doc", setOf("parent"), 2, 2, 1, "multiple_choice")
            val quiz = created.getJSONArray("local_quizzes").getJSONObject(0)
            val id = quiz.getString("id")
            val question = quiz.getJSONArray("questions").getJSONObject(0)
            assertEquals("energy", question.getString("source_id"))
            assertEquals(2, question.getInt("page"))
            rejected = false
            try { repository.next("doc", id, 0) } catch (_: IllegalArgumentException) { rejected = true }
            assertTrue(rejected)
            val wrong = (question.getInt("answer") + 1) % 4
            repository.answer("doc", id, 0, wrong)
            repository.answer("doc", id, 0, wrong)
            rejected = false
            try { repository.answer("doc", id, 0, question.getInt("answer")) } catch (_: IllegalArgumentException) { rejected = true }
            assertTrue(rejected)
            repository.next("doc", id, 0)
            repository.next("doc", id, 0)
            assertEquals(1, repository.open("doc").getJSONArray("local_quizzes").getJSONObject(0).getInt("index"))
            val retried = repository.retry("doc", id).getJSONArray("local_quizzes").getJSONObject(1)
            assertEquals("energy", retried.getJSONArray("questions").getJSONObject(0).getString("source_id"))
            assertFalse(retried.getBoolean("synced"))
            val reopened = OfflineCache(context)
            try {
                assertEquals(2, reopened.load(session.server, session.ownerId, "doc")!!.getJSONArray("local_quizzes").length())
            } finally { reopened.close() }
        } finally {
            cache.clear(); cache.close()
            session.server = previousServer; session.ownerId = previousOwner
        }
    }

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
