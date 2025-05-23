# DiagnoAI

DiagnoAI is an intelligent medical assistant designed to streamline symptom triage and patient interviews by leveraging advanced machine learning models and retrieval-augmented generation (RAG). This project automates the collection of patient information and generates comprehensive reports for medical professionals, ensuring clarity, efficiency, and accuracy.

---

## Table of Contents
- [Introduction](#introduction)
- [Project Overview](#project-overview)
- [Modules Summary](#modules-summary)
  - [1. Chat Engine](#1-chat-engine)
  - [2. Report Generator](#2-report-generator)
  - [3. Vector Store Builder](#3-vector-store-builder)
  - [4. Logger](#4-logger)
  - [5. LLM Integration](#5-llm-integration)
- [Architecture](#architecture)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
- [Future Enhancements](#future-enhancements)
- [License](#license)

---

## Introduction

DiagnoAI serves as a professional medical assistant powered by large language models (LLMs) and FAISS-based RAG to collect, process, and structure patient symptoms effectively. Its goal is to facilitate preliminary data collection without providing diagnoses, assisting doctors with detailed patient reports for better clinical decision-making.

---

## Project Overview

The project combines the capabilities of natural language processing, vector search, and document embedding to automate patient interviews. It connects with external medical data sources like PubMed to enrich responses and leverages a custom-built pipeline for report generation.

---

## Modules Summary

### 1. Chat Engine
- Core conversational logic handling user interactions.
- Uses a system prompt to guide the assistant’s behavior.
- Interfaces with the LLM (LLaMA 3.1 via Groq client) to generate context-aware replies.
- Maintains conversation history and ensures follow-up questions are clear and focused.

### 2. Report Generator
- Summarizes gathered patient information into a structured medical report.
- Covers diagnosis, treatment options, and prevention guidelines.
- Generates outputs in JSON format for easy consumption and further integration.

### 3. Vector Store Builder
- Creates and manages a persistent vector store for document embeddings.
- Supports saving/loading vector stores using Pickle serialization.
- Enables efficient similarity search for relevant medical documents.

### 4. Logger
- Centralized logging setup for the entire application.
- Logs are written to `logs/app.log` and optionally to the console.
- Supports different log levels (`DEBUG`, `INFO`, `ERROR`) for development and production.

### 5. LLM Integration
- Connects to the Groq API to access advanced language models.
- Supports retrieval-augmented generation using FAISS for relevant document search.
- Ensures responses are informative, clear, and medically appropriate.

---

## Architecture

DiagnoAI is structured as a modular backend service:

- **Input Layer**: User symptom input via chat interface.
- **Processing Layer**: Chat engine processes input, interacts with the LLM, and gathers data.
- **Data Layer**: Vector store manages embeddings and retrieves relevant medical documents.
- **Output Layer**: Report generator compiles the final medical report.

The RAG pipeline enhances the system by fetching real-time data from the PubMed API and integrating it into the conversational flow.

---

## Setup and Installation

1. Clone the repository:
   ```bash
Clone the repository
git clone https://github.com/anoshandrews/DiagnoAI-Fast-API-
cd DiagnoAI-Fast-API-

Create and activate virtual environment

python -m venv venv

source venv/bin/activate    # Linux/macOS
OR
venv\Scripts\activate       # Windows

Install dependencies

pip install -r requirements.txt

Configure environment variables

(Add your Groq API credentials and other configs to .env or export them)

Run the app

uvicorn app.main:app --reload