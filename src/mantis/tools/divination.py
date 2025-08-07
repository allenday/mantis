"""
Native pydantic-ai divination and randomness tool.
Provides both raw randomness and structured divination methods.
"""

import random
import logging
from typing import List, Optional
from enum import Enum

# Observability imports
try:
    from ..observability import get_structured_logger

    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Observability logger
if OBSERVABILITY_AVAILABLE:
    obs_logger = get_structured_logger("divination")
else:
    obs_logger = None  # type: ignore


class TarotCard(Enum):
    """Major Arcana tarot cards with meanings."""
    
    THE_FOOL = (0, "The Fool", "New beginnings, innocence, spontaneity, free spirit")
    THE_MAGICIAN = (1, "The Magician", "Manifestation, resourcefulness, power, inspired action")
    THE_HIGH_PRIESTESS = (2, "The High Priestess", "Intuition, sacred knowledge, divine feminine, subconscious")
    THE_EMPRESS = (3, "The Empress", "Femininity, beauty, nature, nurturing, abundance")
    THE_EMPEROR = (4, "The Emperor", "Authority, establishment, structure, father figure")
    THE_HIEROPHANT = (5, "The Hierophant", "Spiritual wisdom, religious beliefs, conformity, tradition")
    THE_LOVERS = (6, "The Lovers", "Love, harmony, relationships, values alignment")
    THE_CHARIOT = (7, "The Chariot", "Control, willpower, success, determination")
    STRENGTH = (8, "Strength", "Strength, courage, persuasion, influence, compassion")
    THE_HERMIT = (9, "The Hermit", "Soul searching, introspection, inner guidance")
    WHEEL_OF_FORTUNE = (10, "Wheel of Fortune", "Good luck, karma, life cycles, destiny")
    JUSTICE = (11, "Justice", "Justice, fairness, truth, cause and effect")
    THE_HANGED_MAN = (12, "The Hanged Man", "Suspension, restriction, letting go, sacrifice")
    DEATH = (13, "Death", "Endings, beginnings, change, transformation")
    TEMPERANCE = (14, "Temperance", "Balance, moderation, patience, purpose")
    THE_DEVIL = (15, "The Devil", "Shadow self, attachment, addiction, restriction")
    THE_TOWER = (16, "The Tower", "Sudden change, upheaval, chaos, revelation")
    THE_STAR = (17, "The Star", "Hope, faith, purpose, renewal, spirituality")
    THE_MOON = (18, "The Moon", "Illusion, fear, anxiety, subconscious, intuition")
    THE_SUN = (19, "The Sun", "Positivity, fun, warmth, success, vitality")
    JUDGEMENT = (20, "Judgement", "Judgement, rebirth, inner calling, absolution")
    THE_WORLD = (21, "The World", "Completion, accomplishment, travel, success")

    def __init__(self, number: int, name: str, meaning: str):
        self.number = number
        self.card_name = name
        self.meaning = meaning


class IChing(Enum):
    """I Ching trigrams with meanings."""
    
    HEAVEN = ("☰", "Heaven", "Creative force, leadership, strength, perseverance")
    EARTH = ("☷", "Earth", "Receptive, nurturing, yielding, supportive")
    WATER = ("☵", "Water", "Danger, depth, flowing, adaptability")
    FIRE = ("☲", "Fire", "Clarity, brightness, illumination, passion")
    THUNDER = ("☳", "Thunder", "Arousing, movement, initiative, shock")
    MOUNTAIN = ("☶", "Mountain", "Stillness, meditation, obstruction, waiting")
    WIND = ("☴", "Wind", "Gentle penetration, influence, flexibility")
    LAKE = ("☱", "Lake", "Joyful, communication, reflection, pleasure")

    def __init__(self, symbol: str, name: str, meaning: str):
        self.symbol = symbol
        self.trigram_name = name
        self.meaning = meaning


async def get_random_number(min_value: int = 1, max_value: int = 100) -> str:
    """Generate a random number within the specified range.

    Args:
        min_value: Minimum value (inclusive, default: 1)
        max_value: Maximum value (inclusive, default: 100)

    Returns:
        Random number as a string for LLM interpretation
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: get_random_number({min_value}, {max_value})")

    if min_value > max_value:
        return f"Error: min_value ({min_value}) cannot be greater than max_value ({max_value})"

    try:
        result = random.randint(min_value, max_value)
        
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.info(f"Generated random number: {result}")
        
        return f"Random number between {min_value} and {max_value}: {result}"
    
    except Exception as e:
        error_msg = f"Error generating random number: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Random number generation failed: {e}")
        return error_msg


async def draw_tarot_card() -> str:
    """Draw a random tarot card from the Major Arcana.

    Returns:
        Formatted tarot card with number, name, and meaning
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info("🎯 TOOL_INVOKED: draw_tarot_card")

    try:
        card = random.choice(list(TarotCard))
        
        result = f"🔮 **{card.card_name}** (Card {card.number})\n"
        result += f"**Meaning:** {card.meaning}\n"
        result += f"**Guidance:** This card suggests themes of {card.meaning.lower().split(',')[0].strip()}."
        
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.info(f"Drew tarot card: {card.card_name}")
        
        return result
    
    except Exception as e:
        error_msg = f"Error drawing tarot card: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Tarot card draw failed: {e}")
        return error_msg


async def cast_i_ching_trigram() -> str:
    """Cast an I Ching trigram for divination.

    Returns:
        Formatted I Ching trigram with symbol, name, and meaning
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info("🎯 TOOL_INVOKED: cast_i_ching_trigram")

    try:
        trigram = random.choice(list(IChing))
        
        result = f"☯️ **{trigram.trigram_name}** {trigram.symbol}\n"
        result += f"**Meaning:** {trigram.meaning}\n"
        result += f"**Insight:** The {trigram.trigram_name} trigram indicates {trigram.meaning.lower().split(',')[0].strip()}."
        
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.info(f"Cast I Ching trigram: {trigram.trigram_name}")
        
        return result
    
    except Exception as e:
        error_msg = f"Error casting I Ching trigram: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"I Ching casting failed: {e}")
        return error_msg


async def draw_multiple_tarot_cards(count: int = 3) -> str:
    """Draw multiple tarot cards for complex readings.

    Args:
        count: Number of cards to draw (default: 3, max: 10)

    Returns:
        Formatted multiple card reading
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: draw_multiple_tarot_cards({count})")

    if count < 1 or count > 10:
        return "Error: Card count must be between 1 and 10"

    try:
        # Draw unique cards (no repeats)
        cards = random.sample(list(TarotCard), min(count, len(TarotCard)))
        
        result = f"🔮 **{count}-Card Tarot Reading**\n\n"
        
        positions = ["Past", "Present", "Future", "Challenge", "Outcome", 
                    "Subconscious", "Environment", "Hopes/Fears", "Final Outcome", "Hidden Influence"]
        
        for i, card in enumerate(cards):
            position = positions[i] if i < len(positions) else f"Card {i+1}"
            result += f"**{position}: {card.card_name}** (Card {card.number})\n"
            result += f"   {card.meaning}\n\n"
        
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.info(f"Drew {count} tarot cards for reading")
        
        return result
    
    except Exception as e:
        error_msg = f"Error drawing multiple tarot cards: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Multiple tarot card draw failed: {e}")
        return error_msg


async def flip_coin() -> str:
    """Flip a virtual coin for simple binary decisions.

    Returns:
        Result of coin flip with simple interpretation
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info("🎯 TOOL_INVOKED: flip_coin")

    try:
        result = random.choice(["Heads", "Tails"])
        interpretation = "proceed with confidence" if result == "Heads" else "consider alternatives"
        
        response = f"🪙 **Coin Flip Result: {result}**\n"
        response += f"**Guidance:** The coin suggests to {interpretation}."
        
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.info(f"Coin flip result: {result}")
        
        return response
    
    except Exception as e:
        error_msg = f"Error flipping coin: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Coin flip failed: {e}")
        return error_msg