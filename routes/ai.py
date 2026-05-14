from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import os

ai_bp = Blueprint('ai', __name__)

llm = ChatGroq(
    api_key=os.environ.get('GROQ_API_KEY'),
    model_name="llama-3.3-70b-versatile",
    temperature=0.7
)

# In-memory conversation store per user
# { user_id: [messages] }
conversation_store = {}

@ai_bp.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or not data.get('message'):
        return jsonify({'error': 'Message is required'}), 400

    # Initialize conversation for this user if first time
    if user_id not in conversation_store:
        conversation_store[user_id] = [
            SystemMessage(content="You are a helpful assistant.")
        ]

    # Add user message to history
    conversation_store[user_id].append(
        HumanMessage(content=data['message'])
    )

    # Send full conversation history to LLM
    response = llm.invoke(conversation_store[user_id])

    # Save AI response to history
    conversation_store[user_id].append(
        AIMessage(content=response.content)
    )

    return jsonify({
        'response': response.content,
        'message_count': len(conversation_store[user_id])
    })

# Clear conversation history
@ai_bp.route('/chat/clear', methods=['POST'])
@jwt_required()
def clear_chat():
    user_id = get_jwt_identity()
    conversation_store[user_id] = [
        SystemMessage(content="You are a helpful assistant.")
    ]
    return jsonify({'message': 'Conversation cleared'})

# Get conversation history
@ai_bp.route('/chat/history', methods=['GET'])
@jwt_required()
def chat_history():
    user_id = get_jwt_identity()
    history = conversation_store.get(user_id, [])

    formatted = []
    for msg in history:
        if isinstance(msg, HumanMessage):
            formatted.append({'role': 'user', 'content': msg.content})
        elif isinstance(msg, AIMessage):
            formatted.append({'role': 'assistant', 'content': msg.content})

    return jsonify({'history': formatted})

@ai_bp.route('/chat/custom', methods=['POST'])
@jwt_required()
def custom_chat():
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({'error': 'Message is required'}), 400

    system_prompt = data.get('system_prompt', 'You are a helpful assistant.')
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=data['message'])
    ]

    response = llm.invoke(messages)
    return jsonify({'response': response.content})
