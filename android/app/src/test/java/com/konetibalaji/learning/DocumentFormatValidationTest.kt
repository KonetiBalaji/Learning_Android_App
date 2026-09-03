package com.konetibalaji.learning

import org.junit.Assert.assertThrows
import org.junit.Test

class DocumentFormatValidationTest {
    @Test fun requestedFormatMustBeConfirmedExceptLegacyMultipleChoice() {
        documentQuestionTypes.keys.forEach { validateDocumentFormat(it, it) }
        validateDocumentFormat("multiple_choice", null)
        listOf("true_false", "yes_no").forEach { requested ->
            assertThrows(IllegalArgumentException::class.java) { validateDocumentFormat(requested, null) }
            assertThrows(IllegalArgumentException::class.java) { validateDocumentFormat(requested, "multiple_choice") }
        }
        assertThrows(IllegalArgumentException::class.java) { validateDocumentFormat("true_false", "yes_no") }
        assertThrows(IllegalArgumentException::class.java) { validateDocumentFormat("essay", "essay") }
    }

    @Test fun canonicalChoicesAndLegacyFourOptionsRemainValid() {
        validateDocumentOptions("true_false", listOf("True", "False"))
        validateDocumentOptions("yes_no", listOf("Yes", "No"))
        validateDocumentOptions("multiple_choice", listOf("A", "B", "C", "D"))
        validateDocumentOptions(null, listOf("A", "B", "C", "D"))
    }

    @Test fun malformedOrMismatchedChoicesAreRejected() {
        val invalid = listOf(
            "true_false" to listOf("False", "True"),
            "yes_no" to listOf("Yes", "Maybe"),
            "yes_no" to listOf("True", "False"),
            "multiple_choice" to listOf("A", "B", "C"),
            "multiple_choice" to listOf("A", " a ", "C", "D"),
            "multiple_choice" to listOf("A", "", "C", "D"),
            "unknown" to listOf("A", "B", "C", "D"),
            null to listOf("Yes", "No"),
        )
        invalid.forEach { (type, options) ->
            assertThrows(IllegalArgumentException::class.java) { validateDocumentOptions(type, options) }
        }
    }
}
