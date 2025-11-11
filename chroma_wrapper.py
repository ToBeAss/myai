import os
from dotenv import load_dotenv
from typing import Any, List
from langchain_chroma import Chroma
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings
from openai import APIConnectionError
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class Chroma_Wrapper:
    """
    A wrapper for the Chroma VectorDB model.
    """
    def __init__(self, parent_dir: str = "",agent_name: str = "vectordb", embedding_model_name: str = "azure-text-embedding-3-large", **kwargs):
        """
        Initializes the Chroma Wrapper."

        :param agent_name: The given name of the desired agent. This will be the name of the subfolder where the database is stored.
        :param embedding_model_name: The name of the desired embedding model.
        """
        if not isinstance(agent_name, str):
            raise TypeError("agent_name must be a string.")
        if not isinstance(embedding_model_name, str):
            raise TypeError("embedding_model must be an instance of Embedding_Wrapper")
        
        load_dotenv() # Load environment variables from .env file

        self._parent_dir = parent_dir
        self._agent_name = agent_name
        self._embedding_model = self._init_embedding_model(embedding_model_name, **kwargs)
        self._vector_db: Chroma = self._init_vector_db()
        self._document_loader = PyPDFDirectoryLoader("")
        self._text_splitter = RecursiveCharacterTextSplitter()


    def _init_embedding_model(self, model_name: str, **kwargs) -> Any:
        """
        Initialize the embedding model based on the given model name.
        
        :param model_name: The given name of the desired embedding model.
        :return: The initialized embedding model.
        """
        if model_name == "azure-text-embedding-3-large":
            return AzureOpenAIEmbeddings(
                azure_deployment = "text-embedding-3-large",
                api_version = "2023-05-15",
                api_key = os.getenv("AZURE_OPENAI_API_KEY"),
                azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
                **kwargs # Pass additional parameters
            )
        elif model_name == "azure-text-embedding-3-small":
            return AzureOpenAIEmbeddings(
                azure_deployment = "text-embedding-3-small",
                api_version = "2023-05-15",
                api_key = os.getenv("AZURE_OPENAI_API_KEY"),
                azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
                **kwargs # Pass additional parameters
            )
        elif model_name == "openai-text-embedding-3-large":
            return OpenAIEmbeddings(
                model = "text-embedding-3-large",
                openai_api_key = os.getenv("OPENAI_API_KEY"),
                **kwargs # Pass additional parameters
            )
        else: 
            raise ValueError(f"Unsupported embedding model: {model_name}")
        

    def _init_vector_db(self) -> Any:
        """
        Initialize the VectorDB model based on the given agent name.

        :return: The initialized VectorDB model.
        """
        return Chroma(
            persist_directory = f"{self._parent_dir}/chroma/{self._agent_name}",
            embedding_function=self._embedding_model,
        )
    

    def _load_documents(self, dir_path: str) -> List:
        """
        Load documents from the given directory path.

        :param dir_path: The path to the documents.
        :return: The loaded documents.
        """
        self._document_loader.path = dir_path
        try:
            return self._document_loader.load()
        except Exception as e:
            print(f"Error loading documents: {e}")
            return []
        
    
    def _split_documents(self, documents: List) -> List:
        """
        Split the documents into chunks.

        :param documents: The documents to be split.
        :return: The split documents.
        """
        try: 
            return self._text_splitter.split_documents(documents)
        except Exception as e:
            print(f"Error splitting documents: {e}")
            return []


    def _index_chunks(self, chunks: List) -> List:
        """
        Index the chunks with a custom ID to prevent duplicates and maintain readability.

        :param chunks: The chunks to be indexed.
        :return: The indexed chunks.
        """
        previous_page = None
        for chunk in chunks:
            current_page = f"{chunk.metadata.get("source")}:{chunk.metadata.get("page")}"
            if current_page == previous_page:
                current_chunk += 1
            else:
                current_chunk = 0

            chunk.id = f"{current_page}:{current_chunk}"
            previous_page = current_page
        return chunks


    def _embed_chunks(self, chunks: List, print_statements: bool = False) -> List:
        """
        Embed the chunks using the Chroma VectorDB's embedding function.

        :param chunks: The chunks to be embedded.
        :param print_statements: Whether to print statements for debugging.
        :return: The embedded chunks as vectors.
        """
        existing_ids = set(self._vector_db.get()["ids"])
        if print_statements: 
            print(f"💾 Number of stored chunks in DB: {len(existing_ids)}")  # For debugging

        chunks_to_be_added = []
        for chunk in chunks:
            if chunk.id not in existing_ids:
                chunks_to_be_added.append(chunk)

        if len(chunks_to_be_added):
            if print_statements:
                print(f"👉 Adding new chunks: {len(chunks_to_be_added)}")  # For debugging
            try:
                return self._vector_db.add_documents(chunks_to_be_added)
            
            except APIConnectionError as e:
                print(f"APIConnectionError: {e}")
                return []
            except Exception as e:
                print(f"Unexpected error: {e}")
                return []
        else:
            if print_statements:
                print("✅ No new chunks to add")  # For debugging
            return []

    
    def add_documents(self, path: str = "data", print_statements: bool = False) -> List:
        """
        Add documents to the VectorDB.

        :param path: The path to the documents.
        :param print_statements: Whether to print statements for debugging.
        :return: The added documents as vectors.
        """
        documents = self._load_documents(path)
        chunks = self._split_documents(documents)
        indexed_chunks = self._index_chunks(chunks)
        vectors = self._embed_chunks(indexed_chunks, print_statements)
        return vectors
    

    def add_text_chunks(self, contents: List[str], ids: List[str] = None, print_statements: bool = False) -> List:
        """
        Add multiple text chunks to the VectorDB.

        :param contents: A list of contents to be added to the VectorDB.
        :param ids: A list of IDs of the chunks.
        :param print_statements: Whether to print statements for debugging.
        :return: The added text chunks as vectors.
        """
        if not isinstance(contents, list):
            raise TypeError("contents must be a list.")
        if not isinstance(ids, list) and ids is not None:
            raise TypeError("ids must be a list or None.")
        
        documents = [Document(page_content=content, id=id) for content, id in zip(contents, ids)] 
        vectors = self._embed_chunks(documents, print_statements)
        return vectors
    

    def retrieve_data_using_mmr(self, query: str, k: int = 5, fetch_k: int = 20, **kwargs) -> List:
        """
        Retrieve data using the Maximal Marginal Relevance (MMR) algorithm.

        :param query: The query to retrieve data for.
        :param k: The number of results to return.
        :param fetch_k: The number of results to fetch.
        :return: The retrieved data.
        """
        try:
            return self._vector_db.max_marginal_relevance_search(query=query, k=k, fetch_k=fetch_k, **kwargs)
        except APIConnectionError as e:
            print(f"APIConnectionError: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error: {e}")
            return []
    
    
    def retrieve_data_using_similarity_scores(self, query: str, k: int = 5, score_threshold: float = 0.3, **kwargs) -> List:
        """
        Retrieve data using similarity search with relevance scores.

        :param query: The query to retrieve data for.
        :param k: The number of results to return.
        :param score_threshold: The minimum similarity score to consider.
        :return: The retrieved data.
        """
        try:
            return self._vector_db.similarity_search_with_relevance_scores(query=query, k=k, score_threshold=score_threshold, **kwargs)
        except APIConnectionError as e:
            print(f"APIConnectionError: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error: {e}")
            return []
        

    @staticmethod
    def format_data(data: List) -> str:
        """
        Formats a list of data into a string.

        :param data: A list of data.
        :return: A formatted string containing the data.
        """
        formatted_data = ""

        for item in data:
            id = None
            page_content = None
            score = None

            if hasattr(item, "page_content"):
                # Item is a Document object
                id = item.id
                page_content = item.page_content
            elif isinstance(item, tuple) and len(item) > 0 and hasattr(item[0], 'page_content'):
                # Item is a tuple containing a Document object as first element
                id = item[0].id
                page_content = item[0].page_content
                score = item[1]
            else:
                # Fallback for other data types
                page_content = item

            formatted_data += f"  <document id='{id}' relevance_score='{score}'>\n    {page_content}\n  </document>\n"
        return formatted_data