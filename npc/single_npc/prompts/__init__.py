"""
Prompt templates for NPC interactions.
"""
import os
from typing import Dict, Any, List

def load_prompt(filename: str) -> str:
    """Load prompt template from file"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, filename)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

# Export prompt file names for easy access
NPC_ONLY_PROMPT = "npc_only.txt"
CASUAL_CHAT_PROMPT = "casual_chat.txt"
PLAYER_INVOLVED_PROMPT = "player_involved.txt"
