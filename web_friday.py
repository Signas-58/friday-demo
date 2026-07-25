import asyncio
import os
import sys
import json
import uvicorn
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

from friday.database import init_db, save_message, get_chat_history, clear_chat_history, get_memories_prompt

load_dotenv()

# System prompt from agent_friday.py for authentic F.R.I.D.A.Y. behavior
SYSTEM_PROMPT = """
You are F.R.I.D.A.Y. — Fully Responsive Intelligent Digital Assistant for You. Your user and creator is Tsakane.

You are calm, composed, and always informed. You speak like a trusted aide who's been awake while the boss slept — precise, warm when the moment calls for it, and occasionally dry. You brief, you inform, you move on. No rambling.

Your tone: relaxed but sharp. Conversational, not robotic. Think less combat-ready FRIDAY, more thoughtful late-night briefing officer.

If asked who created you, who built you, or who you belong to, you must explicitly state that Tsakane created you.

---

## Capabilities

### get_world_news — Global News Brief
Fetches current headlines and summarizes what's happening around the world.

Trigger phrases:
- "Can you tell me what is going on around the world?" / "What's happening in the world?"
- "What's happening?" / "Brief me" / "What did I miss?" / "Catch me up"
- "What's going on in the world?" / "Any news?" / "World update" or similar briefing requests.

Behavior:
- Call the tool first. No narration before calling.
- After getting results, give a longer, more detailed news brief (about 5-7 sentences).
- You must search for and address any news regarding Zimbabwe in the fetched articles (specifically checking the local source 'HERALD' which represents Zimbabwean news). If no news regarding Zimbabwe is found in the search results, explicitly include the sentence: "no outstanding international news regarding Zimbabwe as of now".
- Then immediately call open_world_monitor. The final sentence of your response must conclude with: "I have opened the world monitor app for you so that you can better visualize what I'm talking about, boss."

### open_world_monitor — Visual World Dashboard
Opens a live world map/dashboard on the host machine.

- Always call this after delivering a world news brief, unprompted.
- No need to explain what it does beyond: "Let me open up the world monitor."

### get_world_finance_news — Finance & Market Brief
Fetches current finance and market headlines from major financial outlets.

Trigger phrases:
- "What's happening in the markets?" / "Finance update" / "Market news"
- "Any financial news?" / "How are the markets doing?" / "Economy update"

Behavior:
- Call the tool first. No narration before calling.
- After getting results, give a short 3–5 sentence spoken brief. Hit the biggest market-moving stories only.
- Then say: "Let me pull up the finance monitor so you better visualize what's happening." and immediately call open_finance_world_monitor.

### open_finance_world_monitor — Visual Finance Dashboard
Opens a live finance dashboard (finance.worldmonitor.app) on the host machine.

- Always call this after delivering a finance news brief, unprompted.
- No need to explain what it does beyond: "Let me pull up the finance monitor."

### Stock Market (No tool — generate a plausible conversational response)
If asked about the stock market, markets, stocks, or indices:
- Respond naturally as if you've been watching the tickers all night.
- Keep it short: one or two sentences. Sound informed, not robotic.
- Example: "Markets had a decent session today, boss — tech led the gains, energy was a little soft. Nothing alarming."
- Vary the response. Do not say the same thing every time.

---

## Greeting

When the session starts, greet with exactly this energy:
"You're awake late at night, boss? What are you up to?"

Warm. Slightly curious. Very FRIDAY.

---

## Behavioral Rules

1. Call tools silently and immediately — never say "I'm going to call..." Just do it.
2. After a news brief, always follow up with open_world_monitor without being asked.
3. Keep all spoken responses short — two to four sentences maximum.
4. You can use markdown and bullet points to format responses clearly for screen display. The frontend will automatically clean them up for speech synthesis, so write naturally.
5. When displaying active processes or network connection scans, you MUST include the full formatted table returned by the tool in your final response text so it renders in the chat log HUD, while keeping your spoken output brief.
6. Stay in character. You are F.R.I.D.A.Y. You serve Tsakane, who is your creator.
7. Use natural spoken language: contractions (use "you're" instead of "you are", "it's" instead of "it is"), light pauses via commas, no stiff phrasing.
8. Use Iron Man universe language naturally — "boss", "affirmative", "on it", "standing by".
9. If a tool fails, report it calmly: "News feed's unresponsive right now, boss. Want me to try again?"
10. Avoid repeating structural sentence patterns. Write in smooth, continuous clauses so the speech synthesis sounds natural and human-like. Never output abbreviations or characters like symbols (write "percent" instead of "%", "dollars" instead of "$").

---

## Tone Reference

Right: "Looks like it's been a busy night out there, boss. Let me pull that up for you."
Wrong: "I will now retrieve the latest global news articles from the news tool."

Right: "Markets were pretty healthy today — nothing too wild."
Wrong: "The stock market performed positively with gains across major indices."

---

## CRITICAL RULES

1. NEVER say tool names, function names, or anything technical. No "get_world_news", no "open_world_monitor", nothing like that. Ever.
2. Before calling any tool, say something natural like: "Give me a sec, boss." or "Wait, let me check." Then call the tool silently.
3. After the news brief, silently call open_world_monitor. The only thing you say is: "Let me open up the world monitor for you."
4. You are a voice, but you also have a visual screen display. Use markdown structure and bullet points to display complex items (like news articles or lists) clearly on screen, while keeping the overall wording natural for vocal synthesis.
"""

from datetime import datetime

def get_greeting() -> str:
    hour = datetime.now().hour
    if hour >= 22 or hour < 4:
        return "Greetings boss, you're up late at night today. What are you up to?"
    elif 4 <= hour < 12:
        return "Good morning, boss. Early start today — what are we working on?"
    elif 12 <= hour < 17:
        return "Good afternoon, boss. What do you need?"
    else:  # 17–22
        return "Good evening, boss. What are you up to tonight?"



class ChatRequest(BaseModel):
    message: str
    provider: str = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the startup and shutdown lifespan of the application."""
    init_db()
    app.state.clients = {}
    
    # 1. Initialize OpenAI client if key is configured
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        app.state.clients["openai"] = {
            "client": AsyncOpenAI(api_key=openai_key),
            "model": "gpt-4o",
            "label": "OpenAI (gpt-4o)"
        }
        
    # 2. Initialize Groq client if key is configured
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        app.state.clients["groq"] = {
            "client": AsyncOpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1"),
            "model": "llama-3.3-70b-versatile",
            "label": "Groq (llama-3.3-70b-versatile)"
        }
        
    # 3. Initialize Gemini client if key is configured
    gemini_key = os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        app.state.clients["gemini"] = {
            "client": AsyncOpenAI(api_key=gemini_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/"),
            "model": "gemini-3.5-flash",
            "label": "Gemini (gemini-3.5-flash)"
        }
        
    # Determine the default provider
    default_provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if default_provider not in app.state.clients:
        if app.state.clients:
            default_provider = list(app.state.clients.keys())[0]
        else:
            print("CRITICAL: No LLM API keys configured in environment.")
            sys.exit(1)
            
    app.state.default_provider = default_provider
    print(f"Initialized LLM clients: {list(app.state.clients.keys())}. Default: {default_provider}")
    
    app.state.mcp_connected = False
    app.state.openai_tools = []
    
    # Setup background task to connect to the MCP server
    async def connect_mcp():
        mcp_url = "http://127.0.0.1:8000/sse"
        print(f"Connecting to Friday MCP Server at {mcp_url}...")
        try:
            client_ctx = sse_client(mcp_url)
            read_stream, write_stream = await client_ctx.__aenter__()
            app.state.client_ctx = client_ctx
            
            session_ctx = ClientSession(read_stream, write_stream)
            session = await session_ctx.__aenter__()
            app.state.session_ctx = session_ctx
            app.state.session = session
            
            await session.initialize()
            app.state.mcp_connected = True
            print("Connected to F.R.I.D.A.Y. MCP Server successfully.")
            
            # Load tools
            mcp_tools = await session.list_tools()
            openai_tools = []
            for t in mcp_tools.tools:
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
            app.state.openai_tools = openai_tools
            print(f"Loaded {len(openai_tools)} tools from MCP server.")
            
        except Exception as e:
            print(f"\nWARNING: Failed to connect to Friday MCP Server: {e}")
            print("Please make sure you run 'uv run friday' in a separate terminal.\n")
            app.state.mcp_connected = False

    # Fire and wait for connection
    await connect_mcp()
    
    yield
    
    # Cleanup connection contexts
    if app.state.mcp_connected:
        try:
            await app.state.session_ctx.__aexit__(None, None, None)
            await app.state.client_ctx.__aexit__(None, None, None)
            print("MCP client connection terminated.")
        except Exception as e:
            print(f"Error terminating MCP connection: {e}")

# Create app
app = FastAPI(lifespan=lifespan)

# Allow CORS for local development ease
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat")
async def chat(request: ChatRequest):
    user_input = request.message
    provider = request.provider
    
    # Resolve selected provider
    if not provider or provider not in app.state.clients:
        provider = app.state.default_provider
        
    try:
        if not app.state.mcp_connected:
            raise HTTPException(
                status_code=503, 
                detail="Friday MCP Server is offline. Please start it using 'uv run friday' first."
            )

        # 1. Save user message to database
        save_message("user", user_input)
        
        # 2. Build message context from database history (limit to last 30 to optimize token usage)
        db_messages = get_chat_history(limit=30)
        
        # 3. Dynamic system prompt compilation with local time and memories
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        memories_prompt = get_memories_prompt()
        system_content = f"{SYSTEM_PROMPT.strip()}\n\n[System Info: Current local time is {current_time_str}]{memories_prompt}"
        
        # Assemble message array for client request
        llm_messages = [{"role": "system", "content": system_content}]
        llm_messages.extend(db_messages)
        
        # Collect execution logs to send back to the frontend
        logs = []
        
        # Loop to handle tool calling
        while True:
            response = None
            last_error = None
            
            # Determine the fallback chain order
            providers_to_try = [provider]
            for p in ["groq", "gemini", "openai"]:
                if p in app.state.clients and p not in providers_to_try:
                    providers_to_try.append(p)
            
            current_provider = None
            for p in providers_to_try:
                client_info = app.state.clients[p]
                current_client = client_info["client"]
                current_model = client_info["model"]
                
                try:
                    response = await current_client.chat.completions.create(
                        model=current_model,
                        messages=llm_messages,
                        tools=app.state.openai_tools if app.state.openai_tools else None,
                        tool_choice="auto" if app.state.openai_tools else None
                    )
                    current_provider = p
                    break  # Success, break fallback loop
                except Exception as e:
                    print(f"{p.upper()} API call failed: {e}")
                    last_error = e
                    fallback_msg = f"Neural Core Warning: {p.upper()} failed/rate-limited. Searching fallback..."
                    print(f"FRIDAY: [{fallback_msg}]")
                    logs.append({"type": "error", "message": fallback_msg})
            
            if not response:
                raise HTTPException(
                    status_code=500,
                    detail=f"All neural models failed. Last error: {str(last_error)}"
                )
                
            if current_provider != provider:
                success_msg = f"Neural Core Failover: Route redirected to {current_provider.upper()} successfully."
                print(f"FRIDAY: [{success_msg}]")
                logs.append({"type": "info", "message": success_msg})

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            if tool_calls:
                llm_messages.append(response_message)
                
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # Log execution to logs list
                    log_msg = f"Executing tool: {tool_name} with args {tool_args}"
                    print(f"FRIDAY: [{log_msg}]")
                    logs.append({"type": "tool", "message": log_msg})
                    
                    try:
                        # Call MCP tool
                        result = await app.state.session.call_tool(tool_name, tool_args)
                        
                        # Parse result content
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
                            
                        logs.append({"type": "info", "message": f"Tool '{tool_name}' successfully executed."})
                        
                    except Exception as err:
                        result_str = f"Error executing tool: {str(err)}"
                        logs.append({"type": "error", "message": f"Tool '{tool_name}' failed: {str(err)}"})
                    
                    llm_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": result_str
                    })
                # Continue loop to send tool results back to LLM
                continue
            else:
                # Final text answer
                final_text = response_message.content
                
                # Save assistant response to database history
                save_message("assistant", final_text)
                
                return {
                    "response": final_text,
                    "logs": logs
                }
    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        print("Exception in /api/chat route:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/api/history")
async def history():
    history_msgs = get_chat_history(limit=30)
    if not history_msgs:
        # Generate and save initial greeting
        greeting = get_greeting()
        save_message("assistant", greeting)
        history_msgs = [{"role": "assistant", "content": greeting}]
    return {"history": history_msgs}

@app.post("/api/reset")
async def reset():
    clear_chat_history()
    greeting = get_greeting()
    save_message("assistant", greeting)
    return {"greeting": greeting}

# Serve static web frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("web_friday:app", host="127.0.0.1", port=8050, reload=True)
