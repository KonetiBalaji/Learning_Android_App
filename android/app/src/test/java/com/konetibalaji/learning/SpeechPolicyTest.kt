package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class SpeechPolicyTest {
    @Test fun cancelledOrMissingSpeechDoesNotReplaceTypedText() {
        assertNull(acceptedSpeech(false, listOf("unexpected result")))
        assertNull(acceptedSpeech(true, null))
        assertNull(acceptedSpeech(true, listOf("  ")))
    }
    @Test fun acceptedSpeechIsTrimmedAndBounded() {
        assertEquals("my explanation", acceptedSpeech(true, listOf("", " my explanation ")))
        assertEquals(6000, acceptedSpeech(true, listOf("a".repeat(7000)))!!.length)
    }
    @Test fun chunksRespectEngineLimitWithoutBreakingUnicodePairs() {
        val text = "abc😀def😀ghi"
        val chunks = speechChunks(text, 4)
        assertEquals(text, chunks.joinToString(""))
        assertTrue(chunks.all { it.length <= 4 && !it.last().isHighSurrogate() && !it.first().isLowSurrogate() })
        assertEquals(emptyList<String>(), speechChunks("", 4))
    }
}
