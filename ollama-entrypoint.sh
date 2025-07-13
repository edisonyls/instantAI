#!/bin/sh

# Start Ollama in the background
echo "Starting Ollama server..."
/bin/ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama server to be ready..."
while ! /bin/ollama list >/dev/null 2>&1; do
  echo "Ollama not ready yet, waiting 5 seconds..."
  sleep 5
done

echo "Ollama server is ready!"

# Check and pull the model if needed
echo "Checking if gemma2:2b model exists..."
if /bin/ollama list | grep -q 'gemma2:2b'; then
  echo "Model gemma2:2b already exists!"
else
  echo "Pulling gemma2:2b model... This may take several minutes."
  /bin/ollama pull gemma2:2b
fi

# Verify model is ready
echo "Verifying model is ready..."
if /bin/ollama list | grep -q 'gemma2:2b'; then
  echo "READY: gemma2:2b model is available for use!"
else
  echo "ERROR: Failed to pull gemma2:2b model"
  exit 1
fi

# Keep the Ollama server running in the foreground
wait $OLLAMA_PID 