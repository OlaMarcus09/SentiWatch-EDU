"""
SentiWatch Global Constants

All reputation scoring weights live here.

Changing a value here automatically affects the
entire scoring engine.
"""

# ----------------------------------------------------
# Source credibility weights
# ----------------------------------------------------

SOURCE_WEIGHTS = {
    "google_reviews": 1.5,
    "google_maps": 1.5,

    "vanguard": 3.5,
    "guardian": 3.5,
    "thecable": 3.5,
    "punch": 3.5,
    "premium_times": 3.5,

    "nairaland": 1.2,
    "reddit": 1.4,

    "facebook": 2.0,
    "twitter": 2.4,
    "linkedin": 2.5,

    "blog": 1.3,

    "other": 1.0
}


# ----------------------------------------------------
# Category weights
# ----------------------------------------------------

CATEGORY_WEIGHTS = {

    "fraud": 2.0,

    "legal": 1.9,

    "regulatory": 1.8,

    "cyber": 1.8,

    "security": 1.8,

    "product_quality": 1.5,

    "operations": 1.4,

    "customer_service": 1.2,

    "leadership": 1.5,

    "financial": 1.7,

    "general": 1.0
}


# ----------------------------------------------------
# Risk multipliers
# ----------------------------------------------------

RISK_MULTIPLIERS = {

    "low": 1.0,

    "medium": 1.3,

    "high": 1.6,

    "critical": 2.0
}


# ----------------------------------------------------
# Sentiment base values
# ----------------------------------------------------

SENTIMENT_VALUES = {

    "positive": -8,

    "neutral": 0,

    "negative": 10
}


# ----------------------------------------------------
# Alert thresholds
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
# Maximum risk score
# ----------------------------------------------------

MAX_SCORE = 100


# ----------------------------------------------------
# Volume multipliers
# ----------------------------------------------------

VOLUME_MULTIPLIERS = {

    1: 1.0,

    3: 1.15,

    5: 1.30,

    10: 1.60,

    20: 2.00
}


# ----------------------------------------------------
# AI Categories
# ----------------------------------------------------

VALID_CATEGORIES = {

    "fraud",

    "legal",

    "regulatory",

    "customer_service",

    "product_quality",

    "operations",

    "cyber",

    "security",

    "financial",

    "leadership",

    "general"
}


# ----------------------------------------------------
# Valid sentiments
# ----------------------------------------------------

VALID_SENTIMENTS = {

    "positive",

    "neutral",

    "negative"
}


# ----------------------------------------------------
# Valid risks
# ----------------------------------------------------

VALID_RISKS = {

    "low",

    "medium",

    "high",

    "critical"
}