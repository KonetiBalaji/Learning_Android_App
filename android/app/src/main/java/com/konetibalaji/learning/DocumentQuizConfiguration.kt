package com.konetibalaji.learning

fun validDocumentQuestionCount(input: String): Int? =
    input.trim().toIntOrNull()?.takeIf { it in 5..20 }
