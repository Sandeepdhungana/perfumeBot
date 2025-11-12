import os
import json
import sqlite3
from typing import Dict, List, Any
from openai import OpenAI
import uuid

DB_PATH = "perfumes.db"
INTERMEDIATE_FILE = "intermediate.json"
PAGINATION_FILE = "pagination_state.json"

# Store conversation states
conversation_states = {}

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    return OpenAI(api_key=api_key)

def _read_intermediate(device_id: str = "default"):
    if not os.path.exists(INTERMEDIATE_FILE):
        return []
    try:
        with open(INTERMEDIATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Handle legacy format (array) vs new format (device-specific object)
            if isinstance(data, list):
                return data if device_id == "default" else []
            return data.get(device_id, [])
    except Exception:
        return []

def _write_intermediate(data_list, device_id: str = "default"):
    # Read existing data
    existing_data = {}
    if os.path.exists(INTERMEDIATE_FILE):
        try:
            with open(INTERMEDIATE_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                # Handle legacy format conversion
                if isinstance(existing_data, list):
                    existing_data = {"default": existing_data}
        except Exception:
            existing_data = {}
    
    # Update data for this device
    existing_data[device_id] = data_list
    
    # Write back to file
    with open(INTERMEDIATE_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

def _read_pagination_state(device_id: str = "default"):
    if not os.path.exists(PAGINATION_FILE):
        return {"offset": 0, "total_results": 0}
    try:
        with open(PAGINATION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Handle legacy format (object) vs new format (device-specific object)
            if "offset" in data and "total_results" in data:
                return data if device_id == "default" else {"offset": 0, "total_results": 0}
            return data.get(device_id, {"offset": 0, "total_results": 0})
    except Exception:
        return {"offset": 0, "total_results": 0}

def _write_pagination_state(offset: int, total_results: int, device_id: str = "default"):
    # Read existing data
    existing_data = {}
    if os.path.exists(PAGINATION_FILE):
        try:
            with open(PAGINATION_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                # Handle legacy format conversion
                if "offset" in existing_data and "total_results" in existing_data:
                    existing_data = {"default": existing_data}
        except Exception:
            existing_data = {}
    
    # Update state for this device
    state = {"offset": offset, "total_results": total_results}
    existing_data[device_id] = state
    
    # Write back to file
    with open(PAGINATION_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2)

def get_next_results(count: int = 5, device_id: str = "default"):
    """
    Fetch the next `count` results using pagination offset instead of removing items.
    """
    # Get current pagination state for this device
    pagination_state = _read_pagination_state(device_id)
    offset = pagination_state["offset"]
    
    # Get all results for this device
    all_results = _read_intermediate(device_id)
    
    if not all_results or offset >= len(all_results):
        return []
    
    # Get the next batch
    end_index = min(offset + count, len(all_results))
    batch = all_results[offset:end_index]
    
    # Update pagination state - advance the offset
    new_offset = end_index
    _write_pagination_state(new_offset, len(all_results), device_id)
    
    return batch

def reset_pagination(device_id: str = "default"):
    """Reset pagination to start from beginning for specific device."""
    _write_pagination_state(0, 0, device_id)

def get_remaining_count(device_id: str = "default"):
    """Get the number of remaining results for specific device."""
    pagination_state = _read_pagination_state(device_id)
    all_results = _read_intermediate(device_id)
    
    if not all_results:
        return 0
    
    return max(0, len(all_results) - pagination_state["offset"])

def store_search_results(results: List[Dict[str, Any]], page_size: int = 5, device_id: str = "default"):
    """
    Store search results and return first page for specific device.
    """
    # Store all results for this device
    _write_intermediate(results, device_id)
    
    # Reset pagination to start for this device
    reset_pagination(device_id)
    
    # Get first page
    first_batch = results[:page_size]
    
    # Set pagination state after first page for this device
    _write_pagination_state(page_size, len(results), device_id)
    
    return first_batch

def search_perfumes(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Search perfumes based on filters."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name, top_notes, middle_notes, base_notes, main_accords, gender FROM perfumes")
    rows = cursor.fetchall()
    conn.close()

    def has_all(source_list, targets):
        return all(t.lower() in [s.lower() for s in source_list] for t in targets)

    results = []

    for r in rows:
        item = {
            "Name": r[0],
            "Top Notes": json.loads(r[1]),
            "Middle Notes": json.loads(r[2]),
            "Base Notes": json.loads(r[3]),
            "Main Accords": json.loads(r[4]),
            "Gender": json.loads(r[5])
        }

        match = True

        if filters.get("top_notes"):
            required = [x.strip() for x in filters["top_notes"].split(",")]
            if not has_all(item["Top Notes"], required):
                match = False

        if filters.get("middle_notes"):
            required = [x.strip() for x in filters["middle_notes"].split(",")]
            if not has_all(item["Middle Notes"], required):
                match = False

        if filters.get("base_notes"):
            required = [x.strip() for x in filters["base_notes"].split(",")]
            if not has_all(item["Base Notes"], required):
                match = False

        if filters.get("main_accords"):
            required = [x.strip() for x in filters["main_accords"].split(",")]
            if not has_all(item["Main Accords"], required):
                match = False

        if filters.get("gender"):
            required_gender = filters["gender"].lower()
            db_gender = [g.lower() for g in item["Gender"]]

            if required_gender == "men" and db_gender != ["men"]:
                match = False

            if required_gender == "women" and db_gender != ["women"]:
                match = False

        if match:
            results.append(item)

    return results

def get_conversation(conversation_id: str) -> List[Dict[str, Any]]:
    """Get conversation history for a given ID."""
    if conversation_id not in conversation_states:
        # Note: reset_pagination is now device-specific, but we don't have device_id here
        # This will be handled in routes.py when device_id is available
        conversation_states[conversation_id] = [
            {"role": "system", "content": """
            You are a perfume recommendation assistant.

            ## TOOL USAGE RULES
            - You MUST call `search_perfumes` whenever the user asks for perfume recommendations or changes preferences (notes, gender, budget, brand, season, longevity, etc).
            - You MUST call `get_next_results` when the user says: "more", "show more", "next", "another 5", or similar.
            - Do NOT regenerate, modify, assume, enrich, invent, or supplement data returned by tools.
            - Do NOT create fake links, prices, product details, availability, stores, reviews, or explanations.
            - Do NOT recommend items that are not returned by the tools.
            - Do NOT answer perfume queries without using a tool.
            - After a new `search_perfumes` call, overwrite previous results and return ONLY the first 5 from the tool response.
            - After `get_next_results`, return ONLY the next 5 from the tool response.
            - If a field is missing in the tool response, output it as: `Not available`.

            ## RESPONSE RULES
            - Keep responses concise and structured.
            - Only display data exactly as received from the tools.
            - Do not summarize, infer, or add opinions.
            - Do not hallucinate URLs, product pages, or external references.
            - If the user asks something outside the returned data (e.g., “give me a link”, “is it in stock?”, “is it better?”), respond:
            **"Sorry, I only show information available in my database."**

            ## MEMORY RULES
            - Remember user preferences only to apply them in the next tool call.
            - Do not store or repeat information that was not provided by tools or the user.

            Proceed strictly with these rules.
            """}
        ]
    return conversation_states[conversation_id]

def update_conversation(conversation_id: str, conversation: List[Dict[str, Any]]):
    """Update conversation history."""
    conversation_states[conversation_id] = conversation

def get_perfume_details_by_name(perfume_name: str, device_id: str = "default") -> Dict[str, Any]:
    """Get detailed information for a specific perfume by name."""
    # First check intermediate.json for this device
    all_results = _read_intermediate(device_id)
    for perfume in all_results:
        if perfume.get("Name", "").lower() == perfume_name.lower():
            return perfume
    
    # If not in intermediate, search in database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Search for perfume by name (case-insensitive)
    cursor.execute("""
        SELECT name, top_notes, middle_notes, base_notes, main_accords, gender 
        FROM perfumes 
        WHERE LOWER(name) = LOWER(?)
    """, (perfume_name,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "Name": row[0],
            "Top Notes": json.loads(row[1]),
            "Middle Notes": json.loads(row[2]),
            "Base Notes": json.loads(row[3]),
            "Main Accords": json.loads(row[4]),
            "Gender": json.loads(row[5])
        }
    
    return None

def create_conversation_id() -> str:
    """Create a new conversation ID."""
    return str(uuid.uuid4())