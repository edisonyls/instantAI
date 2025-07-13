# InstantAI - AI-Powered Document Intelligence Platform

InstantAI is a full-stack AI application that makes creating intelligent document assistants as simple as drag-and-drop. No coding, no AI expertise, no complex setup required - just upload your documents and get a trained AI agent ready to answer questions.

## The Scenario

### The Problem It's Solving

Imagine: Your have been asked to create a RAG system to help new employees get answers about company policies, procedures, and knowledge without needing someone to sit next to them all day explaining everything.

Traditionally, this would mean you will need to:

- Learn complex AI and machine learning concepts
- Set up vector databases and embedding models
- Write code to process documents and handle queries
- Manage infrastructure and deployment
- Spend weeks or months building something from scratch

### What if there was a better way?

InstantAI was born from this exact scenario. I created a centralized platform where anyone - technical or not - can simply drag and drop their documents and instantly get a trained AI assistant.

## Quick Demo

See InstantAI in action - from document upload to intelligent conversations in under a minute:

![Quick Demo](quick-demo.mov)

## Docker Compose Configuration

The application uses a sophisticated Docker Compose setup with three interconnected services:

#### Backend Service

- **Base**: FastAPI container
- **Ports**: 8000
- **Volumes**:
  - `./backend:/app` (hot reload development)
  - `./data:/app/data` (persistent data storage)
- **Environment**:
  - `OLLAMA_HOST=http://ollama:11434` (service discovery)
  - `CHROMA_DB_PATH=/app/data/chroma_db` (vector database path)

#### Frontend Service

- **Base**: Node.js React development server
- **Ports**: 3000
- **Environment**: `REACT_APP_API_URL=http://localhost:8000`

#### Ollama Service

- **Base**: `ollama/ollama:latest` official image
- **Ports**: 11434
- **Volumes**: `ollama_data:/root/.ollama` (persistent model storage)
- **Health Check**: Validates service readiness before backend startup
- **Entry Point**: Custom script for model initialization

## Model Selection: Gemma2:2b

**Why Gemma2:2b?**
To be honest, there isn't actually a valid answer for this choice. I selected Gemma2:2b based on my preference and practical considerations. Any complex reasoning model would be overkill for this small demonstration, and response generation takes longer time which doesn't fit the "quick answer" scenario. Two billion parameters is generally what a normal laptop can run comfortably. To make the agent more smart and efficient, a model with larger parameters would always be better, but it also means more hardware requirements and higher $$. Ideally, this application would allow users to customize their model based on their needs, but for demonstration purposes, this feature is not implemented and Gemma2:2b is the default choice.

## Getting Started

#### 1. Clone the Repository

```bash
git clone https://github.com/edisonyls/instantAI.git
cd instantAI
```

#### 2. Launch the Application

```bash
# Start all services with automatic model download
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

#### 3. Wait for Initialization

The first startup downloads the Gemma2:2b model (~1.6GB). This process happens automatically but can take several minutes depending on your internet connection.

**Monitor the installation progress:**

```bash
# Check logs to see download progress
docker-compose logs -f ollama
```

**Visual Status Indicators:**

When you check the Ollama service status at <http://localhost:11434>, you'll see different responses:

- **Not Ready** (Model still downloading):
  ![Ollama Not Ready](Ollama-not-ready.png)

- **Ready** (Model downloaded and loaded):
  ![Ollama Ready](Ollama-ready.png)

**Alternative verification methods:**

```bash
# Verify model is ready via API
curl http://localhost:11434/api/tags

# Check if Gemma2:2b is listed in the response
curl http://localhost:11434/api/show -d '{"name": "gemma2:2b"}'
```

⚠️ **Important**: Don't proceed to the next step until Ollama shows the "Ready" status. The backend service depends on the model being fully loaded.

#### 4. Access the Application

- **Frontend**: <http://localhost:3000>
- **Backend API**: <http://localhost:8000>
- **API Documentation**: <http://localhost:8000/docs>

#### 5. Upload and Chat

1. Navigate to <http://localhost:3000>
2. Upload .docx files
3. Wait for processing completion
4. Start chatting with your document in <http://localhost:3000/chat>!

#### 6. Generate API Keys (Optional)

You can integrate your trained AI assistant into your own applications. To do this, you will need to:

1. Create a new knowledge base through the web interface (this automatically generates an API key)
2. Find your API key in the knowledge base details page
3. Use the API key to build custom chatbots, integrate into websites, or create mobile apps

**Example API Usage:**

```bash
# Chat with your documents via API
curl -X POST http://localhost:8000/api/public/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is our company policy on remote work?",
    "api_key": "your-api-key-here"
  }'
```
