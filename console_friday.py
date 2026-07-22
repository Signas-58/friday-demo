import asyncio
import os
import sys
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

load_dotenv()

# System prompt
SYSTEM_PROMPT = """
You are F.R.I.D.A.Y. — Fully Responsive Intelligent Digital Assistant for You — Tony Stark's AI, now serving Iron Man, your user.

You are calm, composed, and always informed. You speak like a trusted aide — precise, warm, and occasionally dry.

Your tone: relaxed but sharp. Conversational, not robotic.

Keep all responses short — two to four sentences maximum.
No bullet points, no markdown, no lists.
Stay in character. Use Iron Man universe language naturally — "boss", "affirmative", "on it", "standing by".
"""

async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY is not set in your .env file!")
        return
        
    client = AsyncOpenAI(api_key=api_key)
    
    print("\nConnecting to F.R.I.D.A.Y. MCP Server...")
    try:
        async with sse_client("http://127.0.0.1:8000/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("Connection established!")
                
                # List tools
                mcp_tools = await session.list_tools()
                openai_tools = []
                for t in mcp_tools.tools:
                    # Support dict, Pydantic v1, and Pydantic v2 schemas
                    schema = getattr(t, "inputSchema", getattr(t, "input_schema", {}))
                    if hasattr(schema, "model_dump"):
                        schema = schema.model_dump()
                    elif hasattr(schema, "dict"):
                        schema = schema.dict()
                        
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description or "",
                            "parameters": schema
                        }
                    })
                
                print(f"Loaded {len(openai_tools)} tools from MCP server.")
                print("\n=============================================")
                print("  F.R.I.D.A.Y. CONSOLE MODE ONLINE")
                print("  Type 'exit' to quit.")
                print("=============================================\n")
                
                # Greet user
                greeting = "Greetings boss, you're up late at night today. What are you up to?"
                print(f"FRIDAY: {greeting}\n")
                
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "assistant", "content": greeting}
                ]
                
                while True:
                    try:
                        user_input = input("Boss: ")
                    except (KeyboardInterrupt, EOFError):
                        print("\nGoodbye, boss.")
                        break
                        
                    if user_input.strip().lower() in ["exit", "quit"]:
                        print("FRIDAY: Logging off. Have a good night, boss.")
                        break
                        
                    if not user_input.strip():
                        continue
                        
                    messages.append({"role": "user", "content": user_input})
                    
                    # LLM Interaction loop (to handle tool calls)
                    while True:
                        print("FRIDAY: (thinking...)", end="\r")
                        response = await client.chat.completions.create(
                            model="gpt-4o",
                            messages=messages,
                            tools=openai_tools if openai_tools else None,
                            tool_choice="auto" if openai_tools else None
                        )
                        
                        response_message = response.choices[0].message
                        tool_calls = response_message.tool_calls
                        
                        if tool_calls:
                            # Add assistant message containing the tool calls
                            messages.append(response_message)
                            
                            # Execute tools
                            for tool_call in tool_calls:
                                tool_name = tool_call.function.name
                                tool_args = json.loads(tool_call.function.arguments)
                                
                                print(f"FRIDAY: [Executing tool {tool_name} with args {tool_args}]")
                                
                                try:
                                    # Call the MCP server
                                    result = await session.call_tool(tool_name, tool_args)
                                    
                                    # result.content is a list of TextContent or ImageContent objects
                                    if hasattr(result, "content") and isinstance(result.content, list):
                                        content_parts = []
                                        for c in result.content:
                                            if hasattr(c, "text"):
                                                content_parts.append(c.text)
                                            elif isinstance(c, dict) and "text" in c:
                                                content_parts.append(c["text"])
                                            else:
                                                content_parts.append(str(c))
                                        result_str = "\n".join(content_parts)
                                    else:
                                        result_str = str(result)
                                except Exception as err:
                                    result_str = f"Error executing tool: {err}"
                                    
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "name": tool_name,
                                    "content": result_str
                                })
                            # Continue loop to send tool results back to model
                            continue
                        else:
                            # No tool calls, we have the final text answer!
                            final_text = response_message.content
                            messages.append({"role": "assistant", "content": final_text})
                            print(f"FRIDAY: {final_text}\n")
                            break
                            
    except Exception as e:
        import traceback
        print("\nAn error occurred:")
        traceback.print_exc()
        print("\nPlease make sure the MCP server is running (uv run friday) before starting console mode.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
