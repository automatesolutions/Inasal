"""LangChain-powered conversational agent with memory"""

import json
from typing import Optional

from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

from app.config import settings
from app.llm_factory import get_chat_llm
from app.redis_client import redis_client
from app.user_profile import UserProfileService, PersonalityTraits
from app.mogi_persona import build_mogi_system_prompt

profile_service = UserProfileService()


class ChatAgent:
    """Conversational AI agent for travel assistance with MOGI persona"""

    def __init__(self):
        self.memory_store = {}  # In-memory fallback if Redis fails
        self.chain = None

        # Use LLM factory (supports Ollama, OpenAI, Groq)
        self.llm = get_chat_llm(temperature=0.7)
        # Prompt will be built dynamically based on user personality
        self.prompt = None

    async def _get_memory(self, user_id: str) -> ConversationBufferMemory:
        """Get or create conversation memory for user"""
        memory_key = f"chat_memory:{user_id}"
        
        # Try to load from Redis
        try:
            memory_data = await redis_client.get(memory_key)
            if memory_data:
                memory = ConversationBufferMemory(
                    return_messages=True, memory_key="history"
                )
                # Restore conversation history
                history = json.loads(memory_data)
                for msg in history:
                    memory.chat_memory.add_message(msg)
                return memory
        except Exception as e:
            print(f"Error loading memory from Redis: {e}")
        
        # Create new memory
        return ConversationBufferMemory(
            return_messages=True, memory_key="history"
        )

    async def _save_memory(self, user_id: str, memory: ConversationBufferMemory):
        """Save conversation memory to Redis"""
        memory_key = f"chat_memory:{user_id}"
        try:
            # Get conversation history
            history = memory.chat_memory.messages
            history_dict = [{"type": msg.__class__.__name__, "content": msg.content} for msg in history]
            # Store with 24 hour expiration
            await redis_client.set(memory_key, json.dumps(history_dict), expire=86400)
        except Exception as e:
            print(f"Error saving memory to Redis: {e}")

    async def chat(self, message: str, user_id: str = None) -> str:
        """Process a chat message and return response with MOGI persona"""
        if not self.llm:
            return (
                "I'm currently unavailable. Please configure the OpenAI API key to enable chat."
            )

        # Load user profile with personality
        profile = None
        personality = PersonalityTraits()
        user_name = "friend"
        
        if user_id:
            profile = await profile_service.get_profile(user_id)
            if profile:
                personality = profile.personality
                user_name = profile.name or user_name

        # Build MOGI prompt with personality context
        mogi_prompt = build_mogi_system_prompt(
            personality,
            user_name,
            profile.preferences.model_dump() if profile and profile.preferences else {}
        )

        # Create prompt template with MOGI persona
        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(mogi_prompt),
                MessagesPlaceholder(variable_name="history"),
                HumanMessagePromptTemplate.from_template("{input}"),
            ]
        )

        # Get user's conversation memory
        memory = await self._get_memory(user_id or "anonymous")
        
        # Create chain with user's memory and MOGI persona
        chain = ConversationChain(
            llm=self.llm,
            prompt=prompt,
            memory=memory,
            verbose=False
        )

        response = await chain.apredict(input=message)
        
        # Save updated memory
        if user_id:
            await self._save_memory(user_id, memory)
        
        # Log interaction if user_id is provided
        if user_id:
            from app.models.interaction_log import InteractionLogCreate
            await profile_service.log_interaction(
                InteractionLogCreate(
                    user_id=user_id,
                    interaction_type="chat",
                    content={"message": message, "response": response}
                )
            )
            
            # Save chat log to BigQuery
            try:
                from app.bigquery_client import bigquery_client
                await bigquery_client.save_chat_log(
                    user_id=user_id,
                    message=message,
                    response=response,
                    message_type="text",
                    metadata={
                        "personality": profile.personality.model_dump() if profile else {},
                        "user_name": user_name
                    }
                )
            except Exception as e:
                print(f"Error saving chat log to BigQuery: {e}")
        
        return response

    async def clear_memory(self, user_id: str):
        """Clear conversation memory for user"""
        memory_key = f"chat_memory:{user_id}"
        try:
            await redis_client.delete(memory_key)
        except Exception as e:
            print(f"Error clearing memory: {e}")

