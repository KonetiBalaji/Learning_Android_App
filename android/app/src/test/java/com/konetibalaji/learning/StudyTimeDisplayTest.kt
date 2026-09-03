package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class StudyTimeDisplayTest {
    @Test fun distinguishesUnavailableZeroAndObservedTime() {
        assertNull(parseWeeklyStudySeconds(null))
        assertEquals("Unavailable", weeklyStudyTimeLabel(null))
        assertEquals("No recorded time", weeklyStudyTimeLabel(parseWeeklyStudySeconds(0)))
        assertEquals("59s", weeklyStudyTimeLabel(parseWeeklyStudySeconds(59L)))
        assertEquals("1m 5s", weeklyStudyTimeLabel(parseWeeklyStudySeconds(65)))
        assertEquals("1h 1m", weeklyStudyTimeLabel(parseWeeklyStudySeconds(3660)))
        assertEquals("168h 0m", weeklyStudyTimeLabel(parseWeeklyStudySeconds(604800)))
    }
    @Test fun rejectsMalformedOrImpossibleWeeklyDurations() {
        listOf(-1, 604801L, Long.MAX_VALUE, 1.5, "30", true).forEach {
            assertThrows(IllegalArgumentException::class.java) { parseWeeklyStudySeconds(it) }
        }
    }
}
