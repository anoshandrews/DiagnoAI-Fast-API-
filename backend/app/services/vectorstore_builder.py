from pathlib import Path
from typing import Optional
import pickle
import os

class VectorStoreBuilder:
    """
    Handles creation, saving, and loading of a vectorstore for document embeddings.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initializes the VectorStoreBuilder with paths for documents and vectorstore.

        Args:
            base_dir (Optional[Path]): The base directory to resolve all relative paths.
                                      Defaults to the parent of the current file's parent.
        """
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.docs_dir = self.base_dir / "data" / "medical_docs"
        self.vectorstore_dir = self.base_dir / "vectorstore"

        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.vectorstore_dir.mkdir(parents=True, exist_ok=True)

    def save_vectorstore(self, vectorstore: object, filename: str = "medical_vectorstore.pkl") -> None:
        """
        Saves the vectorstore object to a file using pickle.

        Args:
            vectorstore (object): The object to serialize and save.
            filename (str): Name of the file to save the vectorstore to.
        """
        filepath = self.vectorstore_dir / filename
        with open(filepath, 'wb') as f:
            pickle.dump(vectorstore, f)

    def load_vectorstore(self, filename: str = "medical_vectorstore.pkl") -> Optional[object]:
        """
        Loads the vectorstore object from a file if it exists.

        Args:
            filename (str): Name of the file to load the vectorstore from.

        Returns:
            Optional[object]: The loaded vectorstore object, or None if file doesn't exist.
        """
        filepath = self.vectorstore_dir / filename
        if not filepath.exists():
            return None
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            if isinstance(data, dict) and "vectorstore" in data:
                return data["vectorstore"]
            return data  # fallback: maybe it's a raw vectorstore object

    def vectorstore_exists(self, filename: str = "medical_vectorstore.pkl") -> bool:
        """
        Checks if the vectorstore file exists.

        Args:
            filename (str): Name of the vectorstore file.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        filepath = self.vectorstore_dir / filename
        return filepath.exists()

    def get_docs_path(self) -> Path:
        """
        Returns the path to the directory containing medical documents.

        Returns:
            Path: Path to medical documents folder.
        """
        return self.docs_dir
if __name__ == "__main__":
    print("Building vectorstore...")

    builder = VectorStoreBuilder()

    # Check if vectorstore already exists
    if builder.vectorstore_exists():
        print("Vectorstore already exists. Skipping creation.")
    else:
        # 🚧 Here's where you add actual vectorstore creation logic.
        # For now, let's just simulate with a dummy object:
        dummy_vectorstore = {"status": "This is a dummy vectorstore!"}
        builder.save_vectorstore(dummy_vectorstore)
        print("Vectorstore saved!")

    print("Done building vectorstore.")