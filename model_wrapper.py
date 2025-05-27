from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class FunctionCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

class Message(BaseModel):
    role: str
    content: Optional[str] = None
    function_call: Optional[FunctionCall] = None
    name: Optional[str] = None # For role 'function'

class ModelWrapper(ABC):
    @abstractmethod
    async def generate(self, messages: List[Message], functions: List[Dict[str, Any]]) -> Message:
        """Generate response using the underlying model.
        
        Args:
            messages: List of messages in the conversation.
            functions: List of available function definitions for the model.
            
        Returns:
            A Message object, which might contain text content or a function_call.
        """
        pass

class OpenAIWrapper(ModelWrapper):
    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model_name = model_name
        # In a real scenario, you'd initialize the OpenAI client here
        # import openai
        # openai.api_key = self.api_key
        print(f"OpenAIWrapper initialized for model {self.model_name}")

    async def generate(self, messages: List[Message], functions: List[Dict[str, Any]]) -> Message:
        print("OpenAIWrapper.generate called")
        # This is a mock implementation. 
        # A real implementation would call openai.ChatCompletion.create()
        
        # Simulate model deciding to call a function
        if any(msg.role == "user" and "notion" in msg.content.lower() for msg in messages):
            return Message(
                role="assistant",
                function_call=FunctionCall(
                    name="notion_read",
                    arguments={"page_id": "example_page_123"}
                )
            )
        # Simulate model providing a text response after a function call
        elif any(msg.role == "function" for msg in messages):
            return Message(
                role="assistant",
                content="I have processed the information from the tool."
            )
        # Default text response
        return Message(
            role="assistant",
            content="This is a mock response from OpenAIWrapper."
        )

class LocalLLMWrapper(ModelWrapper):
    async def generate(self, messages: List[Message], functions: List[Dict[str, Any]]) -> Message:
        print("LocalLLMWrapper.generate called")
        # This is a mock implementation
        if any(msg.role == "user" and "file" in msg.content.lower() for msg in messages):
            return Message(
                role="assistant",
                function_call=FunctionCall(
                    name="fs_read",
                    arguments={"path": "/example/file.txt"}
                )
            )
        return Message(
            role="assistant",
            content="This is a mock response from LocalLLMWrapper."
        )
