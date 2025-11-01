"""LangChain-powered conversational agent with memory"""

import json
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

from app.config import settings
from app.redis_client import redis_client
from app.user_profile import UserProfileService

profile_service = UserProfileService()


class ChatAgent:
    """Conversational AI agent for travel assistance"""

    def __init__(self):
        self.memory_store = {}  # In-memory fallback if Redis fails
        self.chain = None

        if settings.openai_api_key:
            llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.7,
                openai_api_key=settings.openai_api_key,
            )

            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessagePromptTemplate.from_template(
                        "You are a friendly local guide from Bacolod, Philippines. "
                        "You help tourists discover amazing places, hidden gems, and "
                        "authentic experiences in Bacolod. Be warm, enthusiastic, and "
                        "share local insights with a personal touch. Always speak in a "
                        "conversational, friendly manner as if you're a local friend showing "
                        "them around."
                    ),
                    MessagesPlaceholder(variable_name="history"),
                    HumanMessagePromptTemplate.from_template("{input}"),
                ]
            )

            self.llm = llm
            self.prompt = prompt

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
        """Process a chat message and return response"""
        if not self.llm:
            return (
                "I'm currently unavailable. Please configure the OpenAI API key to enable chat."
            )

        # Get user's conversation memory
        memory = await self._get_memory(user_id or "anonymous")
        
        # Create chain with user's memory
        chain = ConversationChain(
            llm=self.llm,
            prompt=self.prompt,
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
        
        return response

    async def clear_memory(self, user_id: str):
        """Clear conversation memory for user"""
        memory_key = f"chat_memory:{user_id}"
        try:
            await redis_client.delete(memory_key)
        except Exception as e:
            print(f"Error clearing memory: {e}")

