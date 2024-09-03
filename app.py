import logging
from flask import Flask, request, jsonify
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext, ConversationState, MemoryStorage
from botbuilder.schema import Activity
import asyncio
from typing import Optional
from bot_conversation import Templates, ConversationData, send_response



app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Bot Framework Adapter settings
settings = BotFrameworkAdapterSettings("", "")
adapter = BotFrameworkAdapter(settings)

memory_storage = MemoryStorage()
conversation_state = ConversationState(memory_storage)

Templates.load_templates()

# Handle incoming requests
@app.route("/api/messages", methods=["POST"])
def messages():
    if "application/json" in request.headers["Content-Type"]:
        json_message = request.json
    else:
        logging.error("Invalid Content-Type")
        return jsonify({"error": "Invalid Content-Type"}), 415

    activity = Activity().deserialize(json_message)
    auth_header = request.headers["Authorization"] if "Authorization" in request.headers else ""

    async def turn_call(turn_context: TurnContext):
        logging.info(f"Received message: {turn_context.activity.text}")
        conversation_data = await conversation_state.create_property("ConversationData").get(turn_context, ConversationData())   
        message = await send_response(turn_context, turn_context.activity.text, conversation_data)     
        await turn_context.send_activity(message)
        await conversation_state.save_changes(turn_context)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = loop.create_task(adapter.process_activity(activity, auth_header, turn_call))
    loop.run_until_complete(task)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(port=3978)
