# Conversation History & System Prompt Improvements

## Issues Identified

### 1. **System Prompt Not Preserved**
- **Problem**: The system prompt was only passed during agent creation but not maintained in conversation history
- **Impact**: The agent could lose context about its role and instructions over time
- **Solution**: Store system prompt separately and always include it as the first message in conversation history

### 2. **Improper Message History Management**
- **Problem**: Conversation history didn't include the system message, leading to inconsistent context
- **Impact**: Agent responses could drift from intended behavior
- **Solution**: Implement proper message history initialization and management

### 3. **Incorrect LangGraph Agent Usage**
- **Problem**: Using `prompt=SystemMessage(content=instructions)` with `create_react_agent`
- **Impact**: System prompt not properly integrated into conversation flow
- **Solution**: Use `prompt` parameter with a function that properly handles system prompt integration

## Key Improvements

### 1. **Proper System Prompt Preservation**

```python
class PersistentMCPOpenSCADChat:
    def __init__(self, model="gpt-4o"):
        self.system_prompt = None  # Store system prompt separately
        self.conversation_history = []
        
    def _initialize_conversation_history(self):
        """Initialize conversation history with system message"""
        self.conversation_history = [
            SystemMessage(content=self.system_prompt)
        ]
```

### 2. **Correct Agent Creation**

**Before:**
```python
self.agent = create_react_agent(
    llm, tools, prompt=SystemMessage(content=instructions)
)
```

**After:**
```python
def _add_system_prompt(state):
    """Add system prompt to the conversation"""
    messages = state.get("messages", [])
    # If no system message exists as first message, add it
    if not messages or not isinstance(messages[0], SystemMessage):
        return [SystemMessage(content=self.system_prompt)] + messages
    return messages

self.agent = create_react_agent(
    llm, 
    tools, 
    prompt=_add_system_prompt  # Proper system prompt handling
)
```

### 3. **Conversation History Validation**

```python
def _get_conversation_messages(self):
    """Get properly formatted conversation messages for the agent"""
    # Always ensure system message is first
    if not self.conversation_history or not isinstance(self.conversation_history[0], SystemMessage):
        self._initialize_conversation_history()
        
    return self.conversation_history.copy()
```

### 4. **Proper Message Flow**

```python
async def handle_message(self, message: str) -> str:
    # Add user message to conversation history
    self.conversation_history.append(HumanMessage(content=message))
    
    # Get properly formatted messages for the agent
    agent_messages = self._get_conversation_messages()
    
    # Invoke agent with proper message history
    response = await self.agent.ainvoke({
        "messages": agent_messages
    })
    
    # Extract and store AI response
    if latest_ai_message:
        ai_content = latest_ai_message.content
        self.conversation_history.append(AIMessage(content=ai_content))
```

## LangGraph Best Practices Applied

### 1. **Use `prompt` Function for System Prompts**
- Using a function with `prompt` parameter properly integrates system prompts into the conversation flow
- Ensures system context is maintained throughout the conversation
- Works correctly with LangGraph's message processing pipeline

### 2. **Maintain Proper Message Order**
- System message should always be first
- Conversation should follow: System → Human → AI → Human → AI pattern
- Tool messages should be properly handled within the flow

### 3. **Conversation History Management**
- Always validate message history before sending to agent
- Implement proper reset functionality that preserves system context
- Store conversation state separately from UI state

### 4. **Memory Management for Long Conversations**
- For production use, consider implementing message trimming or summarization
- Use LangGraph's built-in memory management features
- Monitor token usage and implement conversation length limits

## Example Usage

```python
# Demo the improved conversation management
chat = PersistentMCPOpenSCADChat()
await chat.initialize()

# System prompt is now properly preserved
response1 = await chat.send_message("Create a cube")
response2 = await chat.send_message("Make it bigger")  # Context preserved

# Reset maintains system prompt
chat.reset_conversation()
response3 = await chat.send_message("Who are you?")  # System context maintained
```

## Additional Considerations

### 1. **Token Management**
For long conversations, implement message trimming:

```python
from langchain_core.messages.utils import trim_messages

def _get_conversation_messages(self, max_tokens=4000):
    if len(self.conversation_history) > 10:  # Simple length check
        trimmed = trim_messages(
            self.conversation_history,
            strategy="last",
            max_tokens=max_tokens,
            start_on="human",
            end_on=("human", "tool"),
        )
        # Ensure system message is preserved
        if not isinstance(trimmed[0], SystemMessage):
            trimmed.insert(0, SystemMessage(content=self.system_prompt))
        return trimmed
    return self.conversation_history.copy()
```

### 2. **Error Handling**
Always validate conversation state:

```python
def _validate_conversation_state(self):
    """Validate and repair conversation state if needed"""
    if not self.conversation_history:
        self._initialize_conversation_history()
        return
        
    if not isinstance(self.conversation_history[0], SystemMessage):
        # Repair: Insert system message at the beginning
        self.conversation_history.insert(0, SystemMessage(content=self.system_prompt))
```

### 3. **Gradio Integration**
- UI chat history and agent conversation history are separate concerns
- Always sync agent responses back to both histories
- Handle edge cases like page refresh or component reloading

## Testing the Improvements

Run the demo script to see the improvements in action:

```bash
cd gradio_app
python conversation_history_demo.py
```

This will demonstrate:
- System prompt preservation across conversations
- Proper message history management
- Context retention through multiple exchanges
- Correct behavior after conversation reset

## References

- [LangGraph Conversation History Management](https://langchain-ai.github.io/langgraph/how-tos/create-react-agent-manage-message-history/)
- [LangChain Chat History Best Practices](https://python.langchain.com/docs/concepts/chat_history/)
- [Gradio ChatInterface Documentation](https://www.gradio.app/guides/creating-a-chatbot-fast) 