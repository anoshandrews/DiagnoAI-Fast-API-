import os
import json
import torch
import logging
from datetime import datetime
from typing import List, Dict
from pathlib import Path
from Bio import Entrez
import streamlit as st

from PIL import Image
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from groq import Groq
from transformers import BlipProcessor, BlipForConditionalGeneration
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.docstore.document import Document
from .vectorstore_builder import VectorStoreBuilder 
from langchain_community.document_loaders import DirectoryLoader # Import the new VectorStoreBuilder class


logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)

# Global constants and initializations
REPORT_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
VECTORSTORE_PATH = os.path.join(WORKING_DIR, '../../../vectorstore')

# Load API key and set environment variables
config_data = json.load(open(os.path.join(WORKING_DIR,'..','..','config.json')))
os.environ['GROQ_API_KEY'] = config_data['GROQ_API_KEY']
os.environ["TOKENIZERS_PARALLELISM"] = "false"

logging.basicConfig(
    format = "%(asctime)s - %(levelname) - %(message)s",
    level = logging.DEBUG
)

# Initialize models
client = Groq()
embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2').to('cpu')
blip_model = BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-base')
blip_processor = BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-base', use_fast=True)

# Function to generate embeddings and store them in FAISS vector store
def load_or_generate_vectorstore() -> FAISS:
    """
    Checks if the vector store exists, and if not, generates it by loading documents
    and creating embeddings.

    Returns:
        FAISS: Loaded or newly created FAISS vectorstore object.
    """
    # Initialize VectorStoreBuilder to manage vector store paths
    vs_builder = VectorStoreBuilder()

    # Check if the vector store exists, else generate it
    if vs_builder.vectorstore_exists():
        logging.info("Vector store found, loading...")
        store = vs_builder.load_vectorstore()
    else:
        logging.info("Vector store not found, generating embeddings from documents...")

        # Set up document loader (loading medical documents from the directory)
        loader = DirectoryLoader(vs_builder.get_docs_path(), glob="**/*.txt")  # Assuming text files, adjust as needed
        documents = loader.load()

        if not documents:
            logging.warning('No documents found in the specified directory. Vector store will not be generated.')
            # Return an empty FAISS store or handle this case in the calling function
            embeddings = HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')
            return FAISS.from_texts(["No documents found."], embeddings)

        # Create OpenAI Embeddings (replace with your model if needed)
        embeddings = HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')

        # Generate the vector store using FAISS
        store = FAISS.from_documents(documents, embeddings)

        # Save the vector store
        vs_builder.save_vectorstore(store)
        logging.debug(f"Vectorstore generated and saved with {len(documents)} documents.")

    return store

def summarize_symptom_chat(chat_history: List[Dict[str, str]]) -> str:
    """
    Summarizes user-reported symptoms from a chat history.

    Args:
        chat_history (List[Dict[str, str]]): List of chat messages containing 'role' and 'content'.

    Returns:
        str: Symptom summary including description, duration, severity, and associated symptoms.
    """
    user_inputs = "\n".join([msg["content"] for msg in chat_history if msg["role"] == "user"])
    summary_prompt = (
        f"Based on the following conversation, summarize the user's reported symptoms:\n\n"
        f"{user_inputs}\n\n"
        "Respond with a clear summary of:\n"
        "- Symptom description\n- Duration\n- Severity\n- Triggers\n- Associated symptoms"
    )

    response = client.chat.completions.create(
        model='llama-3.1-8b-instant',
        messages=[
            {"role": "system", "content": "You are a medical assistant summarizing patient symptom inputs."},
            {"role": "user", "content": summary_prompt}
        ]
    )
    return response.choices[0].message.content.strip()


def download_medical_report_pdf(content: str, filename: str = "medical_report.pdf"):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)

    styles = getSampleStyleSheet()
    story = []

    # Add support for Markdown-style bold (**text**)
    for line in content.split('\n'):
        while '**' in line:
            line = line.replace('**', '<b>', 1).replace('**', '</b>', 1)
        para = Paragraph(line, styles["Normal"])
        story.append(para)
        story.append(Spacer(1, 0.08 * inch))

    doc.build(story)
    buffer.seek(0)

    return buffer

def retrieve_medical_context(symptom_summary: str, top_k: int = 3) -> str:
    
    """
    Retrieves relevant medical context from the vectorstore based on the symptom summary.

    Args:
        symptom_summary (str): Summary of symptoms to query the vectorstore.
        top_k (int, optional): Number of top similar documents to retrieve. Defaults to 3.

    Returns:
        str: Concatenated medical context documents.
    """
    vectorstore = load_or_generate_vectorstore()
    docs = vectorstore.similarity_search(symptom_summary, k=top_k)

    if not docs:
        logging.warning('No relevant document found in the local vectorstore')
        pubmed_docs = query_pubmed(symptom_summary)

        if not pubmed_docs:
            return "No relevant medical context found." # More informative message

        embedded_docs = embed_and_store(pubmed_docs, vectorstore)
        docs = embedded_docs

    if not docs:
        return "No relevant medical context could be retrieved."

    return "\n\n".join([doc.page_content for doc in docs])

def query_pubmed(query: str, max_results: int = 5) -> list:
    """
    Queries the PubMed database using the provided search term.

    Args:
        query (str): The search query to send to PubMed.
        max_results (int): Maximum number of articles to retrieve.

    Returns:
        list: A list of retrieved document texts (e.g., abstracts or full text snippets).
              Each item corresponds to a PubMed article related to the query.
    """
    Entrez.email = "anoshandrews@email.com"  # Required by NCBI
    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        record = Entrez.read(handle)
        ids = record["IdList"]

        abstracts = []
        if ids:
            fetch_handle = Entrez.efetch(db="pubmed", id=",".join(ids), rettype="abstract", retmode="text")
            data = fetch_handle.read().strip()
            abstracts = [{"page_content": abstract.strip()} for abstract in data.split("\n\n") if abstract.strip()]
        
        if not abstracts:
            logging.warning(f"No relevant abstracts found for query: {query}")
        return abstracts
    except Exception as e:
        logging.error(f'Error while querying PubMed: {e}')
        return []

def embed_and_store(raw_docs: list, vectorstore) -> list:
    """
    Embeds a list of documents and adds them to the existing vectorstore.

    Args:
        docs (list): A list of strings representing the documents to embed.
        vectorstore: A vector store instance that supports `.add_documents()` or similar.
        embedding_function (callable): A function or model to convert text to embeddings.

    Returns:
        None: Modifies the vectorstore in-place by adding new embeddings.
    """
    if not raw_docs:
        logging.warning("No new documents to embed and store.")
        return []

    # Wrap raw text into LangChain Document objects
    docs = [Document(page_content=d["page_content"]) for d in raw_docs]

    # Embed and add to FAISS store
    logging.debug(f"Embedding {len(docs)} documents.")
    vectorstore.add_documents(docs)

    # Save updated vectorstore
    builder = VectorStoreBuilder()
    builder.save_vectorstore(vectorstore)

    logging.debug(f"Stored {len(docs)} documents in the vectorstore.")

    return docs

def generate_medical_report(symptom_summary: str, medical_context: str) -> str:
    """
    Generates a structured medical report using a language model.

    Args:
        symptom_summary (str): Summarized patient symptoms.
        medical_context (str): Retrieved medical knowledge for context.

    Returns:
        str: Final formatted medical report.
    """
    final_prompt = (
        f"Generate a medical report using the symptom summary and relevant medical knowledge below.\n\n"
        f"Symptom Summary:\n{symptom_summary}\n\n"
        f"Medical Knowledge:\n{medical_context}\n\n"
        f"Format the report with:\n"
        f"- Patient Summary (include date/time: {REPORT_TIME})\n"
        f"- Possible Conditions\n"
        f"- Recommendations"
    )

    response = client.chat.completions.create(
        model='llama-3.1-8b-instant',
        messages=[
            {"role": "system", "content": "You are a doctor writing a preliminary patient diagnosis report."},
            {"role": "user", "content": final_prompt}
        ]
    )
    return response.choices[0].message.content.strip()


def infer_image_description(image_file_path: str) -> str:
    """
    Generates a description of the medical condition in the image using a vision-language model.

    Args:
        image_file_path (str): Path to the input image file.

    Returns:
        str: Textual description of the condition shown in the image.
    """
    image = Image.open(image_file_path).convert("RGB")
    prompt = (
        "Describe the condition shown in this image. "
        "Does this look medically serious, or is it something that will heal on its own? "
        "Should the person visit a doctor?"
    )
    inputs = blip_processor(text=prompt, images=image, return_tensors="pt")

    with torch.no_grad():
        output = blip_model.generate(**inputs, max_new_tokens=50)

    return blip_processor.decode(output[0], skip_special_tokens=True)

