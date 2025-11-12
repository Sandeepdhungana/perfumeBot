from fastapi import APIRouter, HTTPException
import json
from .models import ChatRequest, ChatResponse, PerfumeDetails
from .utils import (
    get_openai_client, 
    search_perfumes, 
    get_next_results, 
    get_conversation, 
    update_conversation, 
    create_conversation_id,
    store_search_results,
    get_remaining_count,
    reset_pagination,
    get_perfume_details_by_name
)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chat endpoint that processes user input and returns chatbot response."""
    try:
        # Create conversation ID if not provided
        conversation_id = request.conversation_id or create_conversation_id()
        
        # Get conversation history
        conversation = get_conversation(conversation_id)
        
        # Add user message
        conversation.append({"role": "user", "content": request.message})
        
        # Define tools for OpenAI
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_perfumes",
                    "description": "Search perfumes by notes, accords, or gender",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "top_notes": {"type": "string"},
                            "middle_notes": {"type": "string"},
                            "base_notes": {"type": "string"},
                            "main_accords": {"type": "string"},
                            "gender": {"type": "string", "enum":["men","women"],"description":"Gender category for the perfume"},
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_next_results",
                    "description": "Fetch the next N perfumes (default 5) from the rolling buffer",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "count": {"type": "integer", "description": "How many results to fetch", "default": 5}
                        }
                    }
                }
            }
        ]
        
        client = get_openai_client()
        
        # Get initial response from OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=conversation,
            tools=tools,
            tool_choice="auto"
        )
        print(response)
        
        msg = response.choices[0].message
        conversation.append(msg)
        
        matched_perfumes = None
        returned_count = None
        remaining_count = None
        
        # Handle tool calls
        if msg.tool_calls:
            tool_call = msg.tool_calls[0]
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
            
            if func_name == "search_perfumes":
                results = search_perfumes(args)
                
                # Use new pagination system - store results and get first page
                first_batch = store_search_results(results, page_size=5)
                remaining_count = get_remaining_count()
                
                matched_perfumes = [p["Name"] for p in first_batch]
                returned_count = len(first_batch)
                
                tool_response = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({
                        "matched_perfumes": matched_perfumes,
                        "returned_count": returned_count,
                        "remaining_count": remaining_count
                    })
                }
                conversation.append(tool_response)
                
            elif func_name == "get_next_results":
                count = int(args.get("count", 5))
                next_batch = get_next_results(count)
                matched_perfumes = [p["Name"] for p in next_batch]
                returned_count = len(next_batch)
                remaining_count = get_remaining_count()
                
                tool_response = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({
                        "matched_perfumes": matched_perfumes,
                        "returned_count": returned_count,
                        "remaining_count": remaining_count
                    })
                }
                conversation.append(tool_response)
            
            else:
                tool_response = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({
                        "matched_perfumes": [], 
                        "returned_count": 0, 
                        "remaining_count": get_remaining_count()
                    })
                }
                conversation.append(tool_response)
            # print(tool_response)
            
            # Get final response from OpenAI
            final_resp = client.chat.completions.create(
                model="gpt-4",
                messages=conversation
            )
            
            reply = final_resp.choices[0].message.content
            conversation.append({"role": "assistant", "content": reply})
            
        else:
            reply = msg.content
        
        # Update conversation state
        update_conversation(conversation_id, conversation)
        
        return ChatResponse(
            response=reply,
            conversation_id=conversation_id,
            matched_perfumes=matched_perfumes,
            returned_count=returned_count,
            remaining_count=remaining_count
        )
        
    except ValueError as ve:
        if "OPENAI_API_KEY" in str(ve):
            raise HTTPException(status_code=500, detail="OpenAI API key not configured. Please check your .env file.")
        else:
            raise HTTPException(status_code=500, detail=f"Configuration error: {str(ve)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@router.get("/perfume/{perfume_name}", response_model=PerfumeDetails)
async def get_perfume_details(perfume_name: str):
    """Get detailed information for a specific perfume by name."""
    try:
        details = get_perfume_details_by_name(perfume_name)
        if not details:
            raise HTTPException(status_code=404, detail=f"Perfume '{perfume_name}' not found")
        
        return PerfumeDetails(
            name=details["Name"],
            top_notes=details.get("Top Notes", []),
            middle_notes=details.get("Middle Notes", []),
            base_notes=details.get("Base Notes", []),
            main_accords=details.get("Main Accords", []),
            gender=details.get("Gender", [])
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving perfume details: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@router.get("/test-openai")
async def test_openai():
    """Test OpenAI connection."""
    try:
        client = get_openai_client()
        # Simple test to verify the client works
        test_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, this is a test. Please respond with 'OK'."}],
            max_tokens=10
        )
        return {"status": "OpenAI connection successful", "test_response": test_response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI connection failed: {str(e)}")