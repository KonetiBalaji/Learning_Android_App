package com.konetibalaji.learning

data class FractionModel(val denominator: Int = 4, val left: Int = 3, val right: Int = 1) {
    init { require(denominator in 2..12 && left in 0..denominator && right in 0..denominator) }
    val numerator: Int get() = left + right
    val wholeParts: Int get() = numerator / denominator
    val remainder: Int get() = numerator % denominator
    val simplified: String get() {
        var a = numerator
        var b = denominator
        while (b != 0) { val next = a % b; a = b; b = next }
        val top = numerator / a
        val bottom = denominator / a
        return if (bottom == 1) top.toString() else "$top/$bottom"
    }
    fun withDenominator(value: Int) = FractionModel(value, left.coerceAtMost(value), right.coerceAtMost(value))
}
