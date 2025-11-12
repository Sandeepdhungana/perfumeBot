import os
from dotenv import load_dotenv
import sqlite3
import json
from openai import OpenAI

# Load API Key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")
client = OpenAI(api_key=api_key)

DB_PATH = "perfumes.db"
INTERMEDIATE_FILE = "intermediate.json"  # Rolling buffer for paginated results


def _read_intermediate():
    if not os.path.exists(INTERMEDIATE_FILE):
        return []
    try:
        with open(INTERMEDIATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write_intermediate(data_list):
    with open(INTERMEDIATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data_list, f, indent=2, ensure_ascii=False)


def _read_pagination_state():
    pagination_file = "pagination_state.json"
    if not os.path.exists(pagination_file):
        return {"offset": 0, "total_results": 0}
    try:
        with open(pagination_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"offset": 0, "total_results": 0}


def _write_pagination_state(offset: int, total_results: int):
    pagination_file = "pagination_state.json"
    state = {"offset": offset, "total_results": total_results}
    with open(pagination_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_next_results(count: int = 5):
    """
    Fetch the next `count` results using pagination offset instead of removing items.
    """
    # Get current pagination state
    pagination_state = _read_pagination_state()
    offset = pagination_state["offset"]
    
    # Get all results
    all_results = _read_intermediate()
    
    if not all_results or offset >= len(all_results):
        return []
    
    # Get the next batch
    end_index = min(offset + count, len(all_results))
    batch = all_results[offset:end_index]
    
    # Update pagination state - advance the offset
    new_offset = end_index
    _write_pagination_state(new_offset, len(all_results))
    
    return batch


def get_remaining_count():
    """Get the number of remaining results."""
    pagination_state = _read_pagination_state()
    all_results = _read_intermediate()
    
    if not all_results:
        return 0
    
    return max(0, len(all_results) - pagination_state["offset"])


def store_search_results(results, page_size=5):
    """
    Store search results and return first page.
    """
    # Store all results
    _write_intermediate(results)
    
    # Reset pagination to start
    _write_pagination_state(0, len(results))
    
    # Get first page
    first_batch = results[:page_size]
    
    # Set pagination state after first page
    _write_pagination_state(page_size, len(results))
    
    return first_batch

def search_perfumes(filters):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name, top_notes, middle_notes, base_notes, main_accords, gender FROM perfumes")
    rows = cursor.fetchall()
    conn.close()

    def has_all(source_list, targets):
        # check if ALL items in targets exist in source_list
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


def run_chatbot():
    conversation = [
        {"role": "system", "content": """
        You are a perfume recommendation assistant.
        Use the search_perfumes tool whenever the user asks about perfumes or changes their preferences.
        If the user asks to see more results from the last query (e.g., "more", "show more", "next"), call the get_next_results tool to fetch the next 5 and remove them from the buffer.
        When a new search is performed, overwrite the buffer with the new results and then return only the first 5.
        Remember previous conversation context. Be concise and give only the information coming from tools. Don't make up any information.
        """}
    ]

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
                        "gender": {"type": "string"},
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_next_results",
                "description": "Fetch the next N perfumes (default 5) from the rolling buffer and remove them from there.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "description": "How many results to fetch", "default": 5}
                    }
                }
            }
        }
    ]

    print("\nPerfume chatbot ready!\n")

    while True:
        user_input = input("You: ")
        conversation.append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model="gpt-4",
            messages=conversation,
            tools=tools,
            tool_choice="auto"
        )

        msg = response.choices[0].message
        conversation.append(msg)  # Always store assistant msg first

        # If model called a tool
        if msg.tool_calls:
            tool_call = msg.tool_calls[0]
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            if func_name == "search_perfumes":
                print("\nSearching database...\n")
                results = search_perfumes(args)

                # Use new pagination system - store results and get first page
                first_batch = store_search_results(results, page_size=5)
                remaining_count = get_remaining_count()
                
                perfume_names = [p["Name"] for p in first_batch]
                print(f"Stored {len(results)} total results, showing first {len(first_batch)}")
                print(f"Remaining results: {remaining_count}")

                tool_response = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({
                        "matched_perfumes": perfume_names,
                        "returned_count": len(first_batch),
                        "remaining_count": remaining_count
                    })
                }
                conversation.append(tool_response)

            elif func_name == "get_next_results":
                count = int(args.get("count", 5))
                print(f"\nFetching next {count} results from pagination...\n")
                next_batch = get_next_results(count)
                perfume_names = [p["Name"] for p in next_batch]

                # Get remaining count after this batch
                remaining_after = get_remaining_count()
                print(f"Returned {len(next_batch)} results, {remaining_after} remaining")

                tool_response = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({
                        "matched_perfumes": perfume_names,
                        "returned_count": len(next_batch),
                        "remaining_count": remaining_after
                    })
                }
                conversation.append(tool_response)

            else:
                # Unknown tool; respond with empty result set to keep flow
                tool_response = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"matched_perfumes": [], "returned_count": 0, "remaining_count": get_remaining_count()})
                }
                conversation.append(tool_response)

            # Now ask GPT to summarize answer using only names
            final_resp = client.chat.completions.create(
                model="gpt-4",
                messages=conversation
            )

            reply = final_resp.choices[0].message.content
            conversation.append({"role": "assistant", "content": reply})

            print("\n:", reply)

        else:
            # Normal chat response
            print("\n:", msg.content)


if __name__ == "__main__":
    run_chatbot()
