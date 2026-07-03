"""
SentiWatch Global Constants

All reputation scoring weights live here.

Changing a value here automatically affects the
entire scoring engine.
"""

# ----------------------------------------------------
# Source credibility weights
# FIX: Added "nigerian_news" key to match the normalised
# source string from _normalise_source() in risk_engine.py.
# Previously, Google News RSS mentions fell through to
# "other" (weight 1.0) because no key matched.
# ----------------------------------------------------

SOURCE_WEIGHTS = {
    "google_reviews": 1.5,
    "google_maps": 1.5,

    "vanguard": 3.5,
    "guardian": 3.5,
    "thecable": 3.5,
    "punch": 3.5,
    "premium_times": 3.5,

    # Google News RSS aggregating Nigerian outlets
    "nigerian_news": 2.5,

    "nairaland": 1.2,
    "reddit": 1.4,

    "facebook": 2.0,
    "twitter": 2.4,
    "linkedin": 2.5,

    "blog": 1.3,

    "other": 1.0,
}


# ----------------------------------------------------
# --- CATEGORY WEIGHTS (EDU) ---

CATEGORY_WEIGHTS = {
    "exams": 1.7,
    "portal_issues": 1.8,
    "lecturers": 1.5,
    "fees": 1.8,
    "hostels": 1.6,
    "admissions": 1.6,
    "scholarships": 1.7,
    "campus_life": 1.4,
}

# --- ALLOWED CATEGORIES (EDU) ---

ALLOWED_CATEGORIES = [
    "exams",
    "portal_issues",
    "lecturers",
    "fees",
    "hostels",
    "admissions",
    "scholarships",
    "campus_life",
]

# ----------------------------------------------------
# Risk multipliers
# ----------------------------------------------------

RISK_MULTIPLIERS = {
    "low": 1.0,
    "medium": 1.3,
    "high": 1.6,
    "critical": 2.0,
}


# ----------------------------------------------------
# Sentiment base values
# ----------------------------------------------------

SENTIMENT_VALUES = {
    "positive": -8,
    "neutral": 0,
    "negative": 10,
}


# ----------------------------------------------------
# Score band thresholds
# ----------------------------------------------------

LOW_THRESHOLD = 20
MEDIUM_THRESHOLD = 40
HIGH_THRESHOLD = 60
CRITICAL_THRESHOLD = 80


# ----------------------------------------------------
# Email alert threshold
# ----------------------------------------------------

EMAIL_ALERT_THRESHOLD = 60


# ----------------------------------------------------
# Maximum risk score cap
# ----------------------------------------------------

MAX_SCORE = 100


# ----------------------------------------------------
# Volume multipliers (keyed by negative mention count)
# ----------------------------------------------------

VOLUME_MULTIPLIERS = {
    1: 1.0,
    3: 1.15,
    5: 1.30,
    10: 1.60,
    20: 2.00,
}


# ----------------------------------------------------
# AI output validation sets
# ----------------------------------------------------

# replace the old ALLOWED_CATEGORIES block with:
ALLOWED_CATEGORIES = [
    "exams",
    "portal_issues",
    "lecturers",
    "fees",
    "hostels",
    "admissions",
    "scholarships",
    "campus_life",
]

VALID_SENTIMENTS = {
    "positive",
    "neutral",
    "negative",
}

VALID_RISKS = {
    "low",
    "medium",
    "high",
    "critical",
}
