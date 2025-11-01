"""LangChain-powered conversational agent with memory"""

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


class ChatAgent:
    """Conversational AI agent for travel assistance"""

    def __init__(self):
        self.memory = ConversationBufferMemory(
            return_messages=True, memory_key="history"
        )
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

            self.chain = ConversationChain(
                llm=llm, prompt=prompt, memory=self.memory, verbose=False
            )

    async def chat(self, message: str, user_id: str = None) -> str:
        """Process a chat message and return response"""
        if not self.chain:
            return (
                "I'm currently unavailable. Please configure the OpenAI API key to enable chat."
            )

        response = await self.chain.apredict(input=message)
        return response

    def clear_memory(self):
        """Clear conversation memory"""
        self.memory.clear()

