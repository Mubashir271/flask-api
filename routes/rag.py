from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FakeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

rag_bp = Blueprint('rag', __name__)

llm = ChatGroq(
    api_key=os.environ.get('GROQ_API_KEY'),
    model_name="llama-3.3-70b-versatile",
    temperature=0.3
)

# Global vector store
vector_store = None

def load_document(file_path: str):
    global vector_store

    # Load document
    if file_path.endswith('.pdf'):
        loader = PyPDFLoader(file_path)
    else:
        loader = TextLoader(file_path)

    documents = loader.load()

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(documents)

    # Create vector store with fake embeddings (no torch needed)
    embeddings = FakeEmbeddings(size=512)
    vector_store = FAISS.from_documents(chunks, embeddings)

    return len(chunks)

# Load document endpoint
@rag_bp.route('/rag/load', methods=['POST'])
@jwt_required()
def load_doc():
    data = request.get_json()
    if not data or not data.get('file_path'):
        return jsonify({'error': 'file_path is required'}), 400

    file_path = data['file_path']
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404

    chunks = load_document(file_path)
    return jsonify({
        'message': 'Document loaded successfully',
        'chunks': chunks
    })

# Ask question about document
@rag_bp.route('/rag/ask', methods=['POST'])
@jwt_required()
def ask():
    global vector_store

    if not vector_store:
        return jsonify({'error': 'No document loaded. Call /api/rag/load first'}), 400

    data = request.get_json()
    if not data or not data.get('question'):
        return jsonify({'error': 'question is required'}), 400

    question = data['question']

    # Search similar chunks
    docs = vector_store.similarity_search(question, k=3)
    context = '\n'.join([doc.page_content for doc in docs])

    # Ask LLM with context
    messages = [
        SystemMessage(content=f"""You are a helpful assistant. 
Answer questions based on the following context only.
If the answer is not in the context, say you don't know.

Context:
{context}"""),
        HumanMessage(content=question)
    ]

    response = llm.invoke(messages)

    return jsonify({
        'answer': response.content,
        'context_used': context
    })
