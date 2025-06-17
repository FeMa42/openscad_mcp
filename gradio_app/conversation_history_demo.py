#!/usr/bin/env python3
"""
Demo script showing improved conversation history management
This demonstrates how system prompts are properly preserved in LangGraph agents
"""

import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool


@tool
def dummy_tool(query: str) -> str:
    """A dummy tool for demonstration"""
    return f"Tool result for: {query}"


class ImprovedConversationManager:
    """Demonstrates proper conversation history management with LangGraph"""
    
    def __init__(self):
        self.system_prompt = "You are a helpful OpenSCAD design assistant. Always remember this context throughout our conversation."
        self.conversation_history = []
        self.agent = None
        
    def initialize(self):
        """Initialize the agent and conversation history"""
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        
        # Use prompt parameter with function for proper system prompt handling
        def _add_system_prompt(state):
            """Add system prompt to the conversation"""
            messages = state.get("messages", [])
            # If no system message exists as first message, add it
            if not messages or not isinstance(messages[0], SystemMessage):
                return [SystemMessage(content=self.system_prompt)] + messages
            return messages
        
        self.agent = create_react_agent(
            llm, 
            [dummy_tool], 
            prompt=_add_system_prompt
        )
        
        # Initialize conversation with system message
        self._initialize_conversation_history()
        
    def _initialize_conversation_history(self):
        """Initialize conversation history with system message"""
        self.conversation_history = [
            SystemMessage(content=self.system_prompt)
        ]
        
    def _get_conversation_messages(self):
        """Get properly formatted conversation messages"""
        # Always ensure system message is first
        if not self.conversation_history or not isinstance(self.conversation_history[0], SystemMessage):
            self._initialize_conversation_history()
            
        return self.conversation_history.copy()
    
    async def send_message(self, message: str) -> str:
        """Send a message and get response with proper history management"""
        # Add user message to history
        self.conversation_history.append(HumanMessage(content=message))
        
        # Get properly formatted messages for the agent
        agent_messages = self._get_conversation_messages()
        
        print(f"📨 Sending {len(agent_messages)} messages to agent:")
        for i, msg in enumerate(agent_messages):
            print(f"  {i+1}. {msg.__class__.__name__}: {msg.content[:100]}...")
        
        # Invoke agent with proper message history
        response = await self.agent.ainvoke({
            "messages": agent_messages
        })
        
        # Extract AI response
        latest_ai_message = None
        for msg in reversed(response["messages"]):
            if isinstance(msg, AIMessage):
                latest_ai_message = msg
                break
        
        if latest_ai_message:
            ai_content = latest_ai_message.content
            # Add AI response to conversation history
            self.conversation_history.append(AIMessage(content=ai_content))
            return ai_content
        else:
            return "No response generated"
    
    def reset_conversation(self):
        """Reset conversation but keep system prompt"""
        self._initialize_conversation_history()
        
    def print_conversation_history(self):
        """Print the current conversation history"""
        print(f"\n📚 Conversation History ({len(self.conversation_history)} messages):")
        for i, msg in enumerate(self.conversation_history):
            print(f"  {i+1}. {msg.__class__.__name__}: {msg.content[:100]}...")


async def main():
    """Demonstrate the improved conversation management"""
    print("🚀 Starting conversation history demonstration...\n")
    
    # Create and initialize the conversation manager
    chat = ImprovedConversationManager()
    chat.initialize()
    
    print("✅ Initialized with system prompt preserved in conversation history")
    chat.print_conversation_history()
    
    # Send first message
    print("\n" + "="*50)
    print("📤 Sending first message...")
    response1 = await chat.send_message("Hello! What can you help me with?")
    print(f"📥 Response: {response1}")
    
    chat.print_conversation_history()
    
    # Send second message
    print("\n" + "="*50)
    print("📤 Sending second message...")
    response2 = await chat.send_message("Create a simple cube in OpenSCAD")
    print(f"📥 Response: {response2}")
    
    chat.print_conversation_history()
    
    # Send third message that references previous conversation
    print("\n" + "="*50)
    print("📤 Sending third message (referencing previous)...")
    response3 = await chat.send_message("Can you make that cube bigger?")
    print(f"📥 Response: {response3}")
    
    chat.print_conversation_history()
    
    # Reset conversation
    print("\n" + "="*50)
    print("🔄 Resetting conversation...")
    chat.reset_conversation()
    chat.print_conversation_history()
    
    # Send message after reset
    print("\n" + "="*50)
    print("📤 Sending message after reset...")
    response4 = await chat.send_message("Who are you?")
    print(f"📥 Response: {response4}")
    
    chat.print_conversation_history()
    
    print("\n✅ Demo completed! System prompt was preserved throughout.")


if __name__ == "__main__":
    asyncio.run(main()) 