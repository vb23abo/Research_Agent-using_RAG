"""Shared fixtures for the agent unit tests."""

from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


@pytest.fixture
def mock_opensearch_client():
    """OpenSearch client that returns two paper chunks."""
    client = Mock()
    client.search_unified = Mock(
        return_value={
            "hits": [
                {
                    "chunk_text": "Transformers are neural network architectures based on self-attention mechanisms.",
                    "arxiv_id": "1706.03762",
                    "title": "Attention Is All You Need",
                    "authors": "Vaswani et al.",
                    "score": 0.95,
                    "section_name": "Introduction",
                },
                {
                    "chunk_text": "BERT pretrains deep bidirectional transformers for language understanding.",
                    "arxiv_id": "1810.04805",
                    "title": "BERT",
                    "authors": "Devlin et al.",
                    "score": 0.88,
                    "section_name": "Introduction",
                },
            ]
        }
    )
    return client


@pytest.fixture
def mock_jina_embeddings_client():
    """Embeddings client that returns a fixed query vector."""
    client = Mock()
    client.embed_query = AsyncMock(return_value=[0.1] * 8)
    return client


@pytest.fixture
def mock_ollama_client():
    """Ollama client stand-in. Nodes that need a model replace this in the test."""
    return Mock()


@pytest.fixture
def test_context(mock_ollama_client, mock_opensearch_client, mock_jina_embeddings_client):
    """Runtime context the node tests pass through a mocked Runtime."""
    context = Mock()
    context.ollama_client = mock_ollama_client
    context.opensearch_client = mock_opensearch_client
    context.embeddings_client = mock_jina_embeddings_client
    context.langfuse_tracer = None
    context.trace = None
    context.langfuse_enabled = False
    context.model_name = "llama3.2:1b"
    context.temperature = 0.0
    context.top_k = 3
    context.max_retrieval_attempts = 2
    context.guardrail_threshold = 60
    return context


@pytest.fixture
def sample_human_message():
    return HumanMessage(content="What is machine learning?")


@pytest.fixture
def sample_ai_message():
    return AIMessage(content="Machine learning is a field of computer science.")


@pytest.fixture
def sample_tool_message():
    return ToolMessage(
        content="Transformers are neural network architectures based on self-attention mechanisms.",
        tool_call_id="call-1",
        name="retrieve_papers",
    )
