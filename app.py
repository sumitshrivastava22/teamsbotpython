import logging
from flask import Flask, request, jsonify
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext, MessageFactory, ConversationState, MemoryStorage, CardFactory
from botbuilder.schema import Activity, HeroCard, CardAction, ActionTypes
import asyncio
import os
import json
from typing import Optional, List, Dict

class ConversationData:
    def __init__(self):
        self.active_question: int = 0
        self.active_section: int = 0
        self.section_template: Optional[SectionTemplate] = None
        self.conversation_template: Optional[ConversationTemplate] = None
        self.conversation_response: ConversationResponse = ConversationResponse()
        self.section_response: SectionResponse = SectionResponse()

app = Flask(__name__)


class ConversationResponse:
    def __init__(self):
        self.template_name: Optional[str] = None
        self.section_responses: Optional[List[SectionResponse]] = None


class SectionResponse:
    def __init__(self):
        self.section_name: Optional[str] = None
        self.question_responses: Optional[List[QuestionResponse]] = None


class QuestionResponse:
    def __init__(self):
        self.id: Optional[str] = None
        self.response: Optional[str] = None


class ConversationTemplate:
    def __init__(self):
        self.template_name: Optional[str] = None
        self.sections: Optional[List[SectionTemplate]] = None


class SectionTemplate:
    def __init__(self):
        self.section_name: Optional[str] = None
        self.questions: Optional[List[QuestionTemplate]] = None


class QuestionTemplate:
    def __init__(self):
        self.question_text: Optional[str] = None
        self.id: Optional[str] = None
        self.response_type: Optional[str] = None
        self.options: Optional[List[str]] = None

class Templates:
    TEMPLATES_DICT: dict[str, ConversationTemplate] = {}
    TEMPLATES_LIST: list[str] = []

    @classmethod
    def load_templates(cls):
        templates = os.listdir("./Templates")
        cls.TEMPLATES_DICT = {}
        cls.TEMPLATES_LIST = []

        for template_file in templates:
            template_path = os.path.join("./Templates", template_file)
            with open(template_path, "r") as f:
                template_data = f.read()
                data = json.loads(template_data)                
                cls.TEMPLATES_DICT[data["TemplateName"]] = data
                cls.TEMPLATES_LIST.append(data["TemplateName"])

def deserialize_conversation_template(data: Dict) -> ConversationTemplate:
    conversation_template = ConversationTemplate()
    conversation_template.template_name = data.get("TemplateName")
    
    conversation_template.sections = []
    for section_data in data.get("Sections", []):
        section = SectionTemplate()
        section.section_name = section_data.get("SectionName")
        
        section.questions = []
        for question_data in section_data.get("Questions", []):
            question = QuestionTemplate()
            question.question_text = question_data.get("QuestionText")
            question.id = question_data.get("Id")
            question.response_type = question_data.get("ResponseType")
            question.options = question_data.get("Options", [])
            section.questions.append(question)
        
        conversation_template.sections.append(section)
    
    return conversation_template

def handle_active_conversation(user_message: str, conversation_data: ConversationData) -> None:
    # Record the user's response
    response = {
        "Id": conversation_data.section_template["Questions"][conversation_data.active_question]["Id"],
        "Response": user_message
    }
    conversation_data.section_response["QuestionResponses"].append(response)

def get_next_message(conversation_data: ConversationData) -> MessageFactory:
    section_template = conversation_data.section_template

    # Check if there are more questions
    if conversation_data.active_question + 1 < len(section_template["Questions"]):
        conversation_data.active_question = conversation_data.active_question + 1
        next_question = section_template["Questions"][conversation_data.active_question]
        return create_message(title = next_question["QuestionText"],subtitle= conversation_data.conversation_template["Sections"][conversation_data.active_section]["SectionName"], options= next_question.get("Options", []))

    # No more questions, finalize the conversation
    return finalize_section(conversation_data)

def finalize_section(conversation_data: ConversationData) -> MessageFactory:
    conversation_data.conversation_response["SectionResponses"].append(conversation_data.section_response)    

    if conversation_data.active_section + 1 < len(conversation_data.conversation_template["Sections"]):
        conversation_data.active_section = conversation_data.active_section + 1
        conversation_data.section_template = conversation_data.conversation_template["Sections"][conversation_data.active_section]
        conversation_data.section_response = {
        "SectionName": conversation_data.section_template["SectionName"],
        "QuestionResponses": []
    }
        conversation_data.active_question = 0
        next_question = conversation_data.section_template["Questions"][conversation_data.active_question]
        return create_message(title= next_question["QuestionText"],subtitle= conversation_data.conversation_template["Sections"][conversation_data.active_section]["SectionName"],options= next_question["Options"])
    else:
        return finalize_conversation(conversation_data)

def finalize_conversation(conversation_data: ConversationData) -> MessageFactory:
    import json

    response_data = json.dumps(conversation_data.conversation_response)
    file_path = f"./Responses/{conversation_data.conversation_template['TemplateName']}.json"
    with open(file_path, "w") as f:
        f.write(response_data)

    template_name = conversation_data.conversation_template["TemplateName"]
    # Reset conversation data
    conversation_data.conversation_template = None
    conversation_data.active_question = 0
    return create_message(f"Conversation completed for template {template_name}")

def create_message(title: str, subtitle: Optional[str] = None, text: Optional[str] = None, options: Optional[List[str]] = None) -> MessageFactory:
    if options is None or len(options) == 0:
        hero_card = HeroCard(title=title, subtitle=subtitle)            
        return MessageFactory.attachment(CardFactory.hero_card(hero_card))
    else:
        actions_list = [CardAction(type=ActionTypes.message_back, text=option, value=option, display_text=option, title=option) for option in options]
        hero_card = HeroCard(title=title, subtitle=subtitle, buttons=actions_list)               
        return MessageFactory.attachment(CardFactory.hero_card(hero_card))


def initialize_conversation(user_message: str, conversation_data: ConversationData) -> MessageFactory:
    conversation_template = Templates.TEMPLATES_DICT[user_message]
    conversation_data.conversation_template = conversation_template
    conversation_data.conversation_response = {
        "TemplateName": user_message,
        "SectionResponses": []
    }

    return initialize_section(user_message, conversation_data)

def initialize_section(user_message: str, conversation_data: ConversationData) -> MessageFactory:
    conversation_data.active_section = 0
    conversation_data.section_template = conversation_data.conversation_template["Sections"][0]

    conversation_data.section_response = {
        "SectionName": conversation_data.section_template["SectionName"],
        "QuestionResponses": []
    }

    conversation_data.active_question = 0
    next_question = conversation_data.section_template["Questions"][conversation_data.active_question]
    return create_message(title= next_question["QuestionText"], subtitle=conversation_data.conversation_template["Sections"][conversation_data.active_section]["SectionName"], options= next_question.get("Options", []))

def run_template_conversation(turn_context: TurnContext, user_message: str, conversation_data: ConversationData) -> MessageFactory:
    message: Optional[MessageFactory] = None

    # Handle active conversation template
    if conversation_data.conversation_template is not None:
        handle_active_conversation(user_message, conversation_data)
        message = get_next_message(conversation_data)
    elif Templates.TEMPLATES_LIST.count(user_message) > 0:  # User selects a valid template
        message = initialize_conversation(user_message, conversation_data)
    else:
        message = create_message("Please select the Template", options=Templates.TEMPLATES_LIST)

    return message

async def send_response(turn_context: TurnContext, user_message: str, conversation_data: ConversationData) -> MessageFactory:
    message: Optional[MessageFactory] = None

    if (conversation_data.conversation_template is not None or
            Templates.TEMPLATES_LIST.count(user_message) > 0):
        message = run_template_conversation(turn_context, user_message, conversation_data)
    else:
        match user_message:
            case "Create Excel":
                message = create_message("Functionality to be implemented")
            case "Go To Dashboard":
                message = create_message("Functionality to be implemented")
            case "Add new survey Data":
                message = create_message("Please Select Template", options=Templates.TEMPLATES_LIST)
            case _:
                message = create_message(
                    title="Welcome Card", subtitle="Please Select an Option", options=["Add new survey Data", "Create Excel", "Go To Dashboard"]
                )

    return message

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
