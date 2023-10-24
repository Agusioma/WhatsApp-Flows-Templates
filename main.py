import os
import random
import re
import string
import requests
from dotenv import load_dotenv
from flask import Flask, request, make_response, json
from llama_cpp import Llama

app = Flask(__name__)

load_dotenv()

TOKEN = os.getenv('TOKEN')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')
url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
message_from_user = "Hello".lower()
code_prompt_texts = ["Book an appointment", "Contact us", "Chat with our chatbot"]


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == TOKEN:
            return make_response(request.args.get("hub.challenge"), 200)
        else:
            return make_response("Success", 403)
    elif request.method == 'POST':
        message_payload = request.get_data()
        print(json.loads(message_payload))

    try:
        name = json.loads(request.get_data())["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
        message = json.loads(request.get_data())["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
        user_phone_number = json.loads(request.get_data())["entry"][0]["changes"][0]["value"]["contacts"][0][
            "wa_id"]
        print(f"PHONE NO: {user_phone_number}")
        print(f"NAME: {name}")
        print(f"Message: {message}")
        user_message_processor(message, user_phone_number, name)
    except:
        print("AN EXCEPTION OCCURRED")

    return make_response("PROCESSED", 200)


def extract_string_from_reply(argument):
    global message_from_user
    match argument:
        case "1":
            message_from_user = code_prompt_texts[0].lower()
        case "2":
            message_from_user = code_prompt_texts[1].lower()
        case "3":
            message_from_user = code_prompt_texts[2].lower()
        case default:
            message_from_user = str(argument).lower()


def user_message_processor(message, phonenumber, name):
    extract_string_from_reply(message)
    if re.search('appointment|book', message_from_user):
        send_message(message, phonenumber, "BOOK_APPOINTMENT", name)
    elif re.search('help|contact|reach|email|problem|issue|more|information', message_from_user):
        send_message(message, phonenumber, "CONTACT_US", name)
    elif re.search('hello|hi|greetings', message_from_user):

        if re.search('this', message_from_user):
            send_message(message, phonenumber, "CHATBOT", name)
        else:
            send_message(message, phonenumber, "SEND_GREETINGS_AND_PROMPT", name)
    else:
        send_message(message, phonenumber, "CHATBOT", name)


def send_message(message, phone_number, message_option, name):
    greetings_text_body = f"\nHello {name}. Welcome to our shop. What would you like us to help you with?\nPlease reply with the digit prompts, for example, *1*.\n\n1. {code_prompt_texts[0]}\n2. {code_prompt_texts[1]}\n3. {code_prompt_texts[2]}\n\nAny other reply will be assumed to be prompt 3."

    contact_flow_payload = flow_details(flow_header="Contact Us",
                                        flow_body="As per your previous message, you indicated that you would like to contact us",
                                        flow_footer="Click the button below to proceed",
                                        flow_id=str(<FLOW-ID>),
                                        flow_cta="Proceed",
                                        recipient_phone_number=phone_number)

    appointment_flow_payload = flow_details(flow_header="Book Appointment",
                                            flow_body="As per your previous message, you indicated that you would like to book an appointment",
                                            flow_footer="Click the button below to proceed",
                                            flow_id=str((<FLOW-ID>),
                                            flow_cta="Proceed",
                                            recipient_phone_number=phone_number)

    match message_option:
        case "SEND_GREETINGS_AND_PROMPT":
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "to": str(phone_number),
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": greetings_text_body
                }
            })
        case "CHATBOT":
            LLM = Llama(model_path="/home/incognito/Downloads/llama-2-7b-chat.ggmlv3.q8_0.gguf.bin")
            # create a text prompt
            prompt = message
            # generate a response (takes several seconds)
            response = LLM(prompt)
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "to": str(phone_number),
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": response["choices"][0]["text"]
                }
            })

        case "CONTACT_US":
            payload = contact_flow_payload
        case "BOOK_APPOINTMENT":
            payload = appointment_flow_payload

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {ACCESS_TOKEN}'
    }

    requests.request("POST", url, headers=headers, data=payload)


def flow_details(flow_header, flow_body, flow_footer, flow_id, flow_cta, recipient_phone_number):
    # Generate the random string
    generated_flow_token = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))

    flow_payload = json.dumps({
        "type": "flow",
        "header": {
            "type": "text",
            "text": flow_header
        },
        "body": {
            "text": flow_body
        },
        "footer": {
            "text": flow_footer
        },
        "action": {
            "name": "flow",
            "parameters": {
                "flow_message_version": "3",
                "flow_token": generated_flow_token,
                "flow_id": flow_id,
                "flow_cta": flow_cta,
                "flow_action": "navigate",
                "flow_action_payload": {
                    "screen": "SCREEN_ONE"
                }
            }
        }
    })

    payload = json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": str(recipient_phone_number),
        "type": "interactive",
        "interactive": json.loads(flow_payload)
    })
    return payload

