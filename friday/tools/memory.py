"""
Memory tools — let F.R.I.D.A.Y. save and recall information about the user.
"""

from friday.database import save_memory, list_memories, delete_memory

def register(mcp):
    
    @mcp.tool()
    async def save_user_memory(key: str, fact: str) -> str:
        """
        Saves a key fact or preference about the user Tsakane to the long-term database.
        Use this whenever the user shares something personal, preferences, hobbies, or rules.
        Args:
            key: Category name (e.g. "interests", "hobbies", "name_pronunciation", "favorite_languages")
            fact: The statement/fact to remember (e.g. "Tsakane's favorite programming language is Python")
        """
        try:
            mem_id = save_memory(key.strip(), fact.strip())
            return f"Fact successfully committed to core neural memory under ID {mem_id}, sir."
        except Exception as e:
            return f"Failed to commit memory: {str(e)}"

    @mcp.tool()
    async def list_user_memories() -> str:
        """
        Retrieves all committed long-term memories regarding the user Tsakane.
        Use this when the user asks what you know about them, or if you need to inspect core memories.
        """
        try:
            memories = list_memories()
            if not memories:
                return "Your long-term memory logs are currently empty, sir."
            
            lines = ["### Stored Memories (Tsakane)"]
            for m in memories:
                lines.append(f"- **ID {m['id']}** [{m['key']}]: {m['fact']}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error listing memories: {str(e)}"

    @mcp.tool()
    async def delete_user_memory(memory_id: int) -> str:
        """
        Deletes a specific user memory entry by its ID.
        Use this when the user tells you to forget a specific fact or correct a memory.
        """
        try:
            success = delete_memory(memory_id)
            if success:
                return f"Memory entry ID {memory_id} has been permanently purged, sir."
            else:
                return f"No memory found with ID {memory_id}, sir."
        except Exception as e:
            return f"Error purging memory: {str(e)}"
