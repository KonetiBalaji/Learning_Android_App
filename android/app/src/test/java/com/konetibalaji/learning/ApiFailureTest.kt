package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

class ApiFailureTest {
    private class Response(private val code: Int, body: String = "", private val broken: Boolean = false) : HttpURLConnection(URL("https://example.invalid")) {
        var disconnected = false
        var closed = false
        val stream = object : ByteArrayInputStream(body.toByteArray()) { override fun close() { closed = true; super.close() } }
        override fun getResponseCode(): Int { if (broken) throw IOException("synthetic network failure"); return code }
        override fun getInputStream() = stream
        override fun getErrorStream() = stream
        override fun disconnect() { disconnected = true }
        override fun connect() {}
        override fun usingProxy() = false
    }

    @Test fun protectedUnauthorizedRequiresFreshLoginButBadCredentialsDoNot() {
        assertTrue(apiFailure(401).sessionExpired)
        assertFalse(apiFailure(401, authenticationRequest = true).sessionExpired)
        assertTrue(apiFailure(401, true).message!!.contains("Email or password"))
        listOf(403, 404, 409, 422, 429, 500, 503).forEach { assertFalse(apiFailure(it).sessionExpired) }
    }

    @Test fun successReadsBodyAndClosesConnection() {
        val response = Response(200, "{\"ok\":true}")
        assertEquals("{\"ok\":true}", readApiResponse(response))
        assertTrue(response.closed)
        assertTrue(response.disconnected)
    }

    @Test fun validationBodiesNeverBecomeUserMessages() {
        val response = Response(422, "{\"detail\":[{\"input\":\"synthetic-secret-password\"}]}")
        val failure = assertThrows(ApiFailure::class.java) { readApiResponse(response) }
        assertEquals(422, failure.status)
        assertFalse(failure.message!!.contains("synthetic-secret-password"))
        assertTrue(response.closed)
        assertTrue(response.disconnected)
    }

    @Test fun htmlAndEmptyErrorsAreHandledWithoutJsonParsing() {
        listOf("<html>private upstream error</html>", "").forEach { body ->
            val response = Response(503, body)
            assertEquals(503, assertThrows(ApiFailure::class.java) { readApiResponse(response) }.status)
            assertTrue(response.disconnected)
        }
    }

    @Test fun deleteUnauthorizedAndRedirectsUseSameErrorPolicy() {
        assertTrue(assertThrows(ApiFailure::class.java) { readApiResponse(Response(401)) }.sessionExpired)
        assertEquals(302, assertThrows(ApiFailure::class.java) { readApiResponse(Response(302)) }.status)
        val response = Response(204)
        assertEquals("", readApiResponse(response))
        assertTrue(response.disconnected)
    }

    @Test fun networkFailureStillDisconnects() {
        val response = Response(200, broken = true)
        assertThrows(IOException::class.java) { readApiResponse(response) }
        assertTrue(response.disconnected)
    }
}
