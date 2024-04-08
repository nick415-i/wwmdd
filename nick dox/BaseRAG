"""Base interface that all RAG examples should implement."""

from abc import ABC, abstractmethod
from typing import Generator

class BaseExample(ABC):

    @abstractmethod
    def llm_chain(self, context: str, question: str, num_tokens: int) -> Generator[str, None, None]:
        pass

    @abstractmethod
    def rag_chain(self, prompt: str, num_tokens: int) -> Generator[str, None, None]:
        pass

    @abstractmethod
    def ingest_docs(self, data_dir: str, filename: str) -> None:
        pass