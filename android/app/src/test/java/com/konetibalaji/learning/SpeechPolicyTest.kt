package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class SpeechPolicyTest {
    @Test fun learning_voice_uses_a_clearer_than_default_pace() {
        assertTrue(LEARNING_SPEECH_RATE in 0.7f..0.9f)
    }
    @Test fun cancelledOrMissingSpeechDoesNotReplaceTypedText() {
        assertNull(acceptedSpeech(false, listOf("unexpected result")))
        assertNull(acceptedSpeech(true, null))
        assertNull(acceptedSpeech(true, listOf("  ")))
    }
    @Test fun acceptedSpeechIsTrimmedAndBounded() {
        assertEquals("my explanation", acceptedSpeech(true, listOf("", " my explanation ")))
        assertEquals(6000, acceptedSpeech(true, listOf("a".repeat(7000)))!!.length)
    }
    @Test fun acceptedSpeechNormalizesWhitespaceAndDropsControls() {
        assertEquals("my spoken answer", acceptedSpeech(true,
            listOf("\u0000\t my\r\n spoken\u0007   answer \u001f")))
        assertEquals("two words", acceptedSpeech(true, listOf("two\u0007words")))
        assertNull(acceptedSpeech(true, listOf("\u0000\u0007\u001f")))
    }
    @Test fun acceptedSpeechTruncationDoesNotSplitUnicodePairs() {
        val result = acceptedSpeech(true, listOf("a".repeat(5999) + "😀" + "tail"))!!
        assertEquals(5999, result.length)
        assertFalse(result.last().isHighSurrogate())
        assertFalse(result.last().isLowSurrogate())
    }
    @Test fun acceptedSpeechSkipsAlternativesThatNormalizeToEmpty() {
        assertEquals("usable result", acceptedSpeech(true,
            listOf("\u0000\u0007", "  usable\nresult  ")))
    }
    @Test fun chunksRespectEngineLimitWithoutBreakingUnicodePairs() {
        val text = "abc😀def😀ghi"
        val chunks = speechChunks(text, 4)
        assertEquals(text, chunks.joinToString(""))
        assertTrue(chunks.all { it.length <= 4 && !it.last().isHighSurrogate() && !it.first().isLowSurrogate() })
        assertEquals(emptyList<String>(), speechChunks("", 4))
    }
}
