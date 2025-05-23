"""
vectorstore_builder.py

A utility module for managing vectorstore persistence in a document retrieval pipeline.
Handles creation, saving, loading, and existence checks for serialized vectorstore objects
using pickle.
"""

from pathlib import Path
from typing import Optional
import pickle
import os
import logging

logger = logging.getLogger(__name__)


class VectorStoreBuilder:
    """
    Manages storage and retrieval of vectorstore objects used for document embeddings.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initializes directory paths for documents and vectorstore files.

        Args:
            base_dir (Optional[Path]): The root directory to use. If None,
                                        defaults to the parent of the current file's parent.
        """
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.docs_dir = self.base_dir / "data" / "medical_docs"
        self.vectorstore_dir = self.base_dir / "vectorstore"

        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.vectorstore_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Base directory set to: {self.base_dir}")
        logger.debug(f"Documents directory: {self.docs_dir}")
        logger.debug(f"Vectorstore directory: {self.vectorstore_dir}")

    def save_vectorstore(self, vectorstore: object, filename: str = "medical_vectorstore.pkl") -> None:
        """
        Saves a vectorstore object to disk using pickle serialization.

        Args:
            vectorstore (object): The object to save (e.g., FAISS index, dictionary, etc.)
            filename (str): The filename to save the object under. Defaults to 'medical_vectorstore.pkl'.
        """
        filepath = self.vectorstore_dir / filename
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(vectorstore, f)
            logger.info(f"Vectorstore saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save vectorstore to {filepath}: {e}")

    def load_vectorstore(self, filename: str = "medical_vectorstore.pkl") -> Optional[object]:
        """
        Loads a previously saved vectorstore object from disk.

        Args:
            filename (str): The filename to load the vectorstore from.

        Returns:
            Optional[object]: The deserialized vectorstore object, or None if the file doesn't exist.
        """
        filepath = self.vectorstore_dir / filename
        if not filepath.exists():
            logger.warning(f"Vectorstore file not found: {filepath}")
            return None
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
                logger.info(f"Vectorstore loaded from {filepath}")
                if isinstance(data, dict) and "vectorstore" in data:
                    logger.debug("Loaded vectorstore from dictionary wrapper.")
                    return data["vectorstore"]
                return data
        except Exception as e:
            logger.error(f"Failed to load vectorstore from {filepath}: {e}")
            return None

    def vectorstore_exists(self, filename: str = "medical_vectorstore.pkl") -> bool:
        """
        Checks whether a vectorstore file exists on disk.

        Args:
            filename (str): The filename to check for.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        filepath = self.vectorstore_dir / filename
        exists = filepath.exists()
        logger.debug(f"Vectorstore exists: {exists} at {filepath}")
        return exists

    def get_docs_path(self) -> Path:
        """
        Returns the path to the directory containing source documents
        that may be used for embedding.

        Returns:
            Path: The path to the document directory.
        """
        return self.docs_dir


if __name__ == "__main__":
    # Configure logging only when the script is run directly
    logging.basicConfig(
        level=logging.DEBUG,  # Change to INFO or WARNING in production
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    logger.info("Starting vectorstore builder...")

    builder = VectorStoreBuilder()

    if builder.vectorstore_exists():
        logger.info("Vectorstore already exists. Skipping creation.")
    else:
        logger.info("Vectorstore does not exist. Creating dummy vectorstore.")
        dummy_vectorstore = {"status": "This is a dummy vectorstore!"}
        builder.save_vectorstore(dummy_vectorstore)

    logger.info("Vectorstore builder finished.")