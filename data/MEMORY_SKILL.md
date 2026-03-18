# NPC Memory Retrieval Skill

This skill guides the model on how to retrieve and use NPC long-term memory stored in the filesystem.

## Directory Structure
- `npc/knowledge/conversations/`: Full dialogue history per scene (`scene_{id}.json`).
- `npc/knowledge/summaries/`: Summaries of each scene (`scene_{id}.txt`).
- `npc/knowledge/npc_memories/`: Individual NPC rolling memories (`{npc_name}.txt`).

## How to Retrieve Memory
1. **Check NPC's Personal Memory**: Read `npc/knowledge/npc_memories/{npc_name}.txt` to get the current state and key past events for a specific NPC.
2. **Review Recent Scenes**: If more context is needed, check `npc/knowledge/summaries/` for the most recent scene summaries.
3. **Deep Dive into Conversations**: If specific details of a past talk are required, locate the scene ID from the summary and read the corresponding file in `npc/knowledge/conversations/`.

## Guidelines for Updating Memory
- When a scene ends, a summary should be generated.
- Each NPC's personal memory should be updated with relevant information from the scene.
- Keep the NPC memory concise (target < 1000 tokens) by summarizing old info when adding new info.
