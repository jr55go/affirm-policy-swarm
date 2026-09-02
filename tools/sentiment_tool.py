"""
Sentiment Analysis Tool for Affirm Policy Swarm.

Provides a simple rule-based sentiment analysis function that can be
extended to use LLM-based analysis in the future.
"""

import re
from typing import Dict, List


# Simple lexicons for rule-based sentiment analysis
# In a production system, these would be much more comprehensive
POSITIVE_WORDS = {
    'good', 'great', 'excellent', 'positive', 'favorable', 'benefit', 'beneficial',
    'approve', 'approval', 'support', 'supportive', 'encourage', 'encouraging',
    'win', 'winner', 'winning', 'success', 'successful', 'strength', 'strong',
    'improve', 'improvement', 'effective', 'efficiency', 'efficient', 'innovate',
    'innovation', 'innovative', 'growth', 'grow', 'expansion', 'expanding',
    'opportunity', 'opportunities', 'promote', 'promoting', 'promoted', 'aid',
    'helps', 'helpful', 'advantage', 'advantageous', 'welcome', 'welcomed',
    'encourage', 'encouraged', 'boost', 'boosted', 'upside', 'upside-down'
}

NEGATIVE_WORDS = {
    'bad', 'poor', 'negative', 'unfavorable', 'harm', 'harmful', 'hurt', 'hurting',
    'oppose', 'opposition', 'opposing', 'reject', 'rejection', 'rejecting',
    'discourage', 'discouraging', 'discouraged', 'lose', 'loser', 'losing',
    'failure', 'fail', 'failing', 'weak', 'weakness', 'decline', 'declining',
    'ineffective', 'inefficiency', 'inefficient', 'restrict', 'restriction',
    'restrictive', 'limitation', 'limited', 'constrain', 'constraining',
    'burden', 'burdensome', 'concern', 'concerning', 'worrisome', 'worry',
    'worried', 'risk', 'risky', 'danger', 'dangerous', 'threat', 'threatening',
    'problem', 'problems', 'problematic', 'issue', 'issues', 'criticize',
    'criticism', 'criticizing', 'blame', 'blaming', 'fault', 'flaw', 'flawed',
    'penalty', 'penalize', 'punish', 'punishment', 'sanction', 'sanctioning'
}


def _load_lexicons() -> Dict[str, set]:
    """
    Load sentiment lexicons. In a more advanced implementation, this could
    load from files or databases.
    """
    return {
        'positive': POSITIVE_WORDS,
        'negative': NEGATIVE_WORDS
    }


def analyze_sentiment(text: str) -> float:
    """
    Analyze sentiment of text and return a score between -1.0 (very negative) and +1.0 (very positive).
    
    Uses a simple rule-based approach based on word matching. Returns 0.0 for neutral or empty text.
    
    Args:
        text: Input text to analyze
        
    Returns:
        Float sentiment score between -1.0 and 1.0
    """
    if not text or not isinstance(text, str):
        return 0.0
    
    # Convert to lowercase and split into words
    words = re.findall(r'\b\w+\b', text.lower())
    
    if not words:
        return 0.0
    
    lexicons = _load_lexicons()
    positive_set = lexicons['positive']
    negative_set = lexicons['negative']
    
    positive_count = sum(1 for word in words if word in positive_set)
    negative_count = sum(1 for word in words if word in negative_set)
    
    total = len(words)
    
    # Calculate sentiment as (positive - negative) / total, clamped to [-1, 1]
    if total == 0:
        return 0.0
    
    raw_score = (positive_count - negative_count) / total
    
    # Apply a sigmoid-like scaling to make extreme scores less common
    # This helps prevent scores from being too close to +/-1 unless strongly biased
    import math
    scaled_score = 2 / (1 + math.exp(-raw_score * 3)) - 1  # tanh-like but using exp
    
    # Ensure we stay within bounds
    return max(-1.0, min(1.0, scaled_score))


# Example usage and testing
if __name__ == "__main__":
    test_cases = [
        ("This is a great and wonderful improvement!", 0.5),  # Should be positive
        ("This is terrible and harmful, we oppose it.", -0.5),  # Should be negative
        ("The report discusses regulations.", 0.0),  # Neutral
        ("", 0.0),  # Empty
        ("Good good good great excellent!", 0.8),  # Strong positive
        ("Bad bad bad terrible awful.", -0.8),  # Strong negative
    ]
    
    print("Testing sentiment analysis:")
    for text, expected in test_cases:
        score = analyze_sentiment(text)
        print(f"Text: '{text}'")
        print(f"  Expected: {expected:.2f}, Got: {score:.2f}")
        print()