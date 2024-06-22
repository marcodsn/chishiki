# Chishiki: Document Search Engine

Chishiki is a document search engine that leverages machine learning to provide a comprehensive and intuitive search experience for your personal document collection. It combines semantic understanding with keyword matching to deliver highly relevant results and offers a user-friendly interface for managing and exploring your documents.

## Features

* **ML-powered Search:** Uses embedding models for semantic search to provide relevant results for complex queries.
* **Dense and Sparse Retrieval:** Combines semantic understanding with keyword matching for comprehensive results.
* **Metadata Filtering:** Allows searches to be refined by file type, (creation/modification dates, file size, available soon), and custom tags.
* **Similar Document Discovery:** Identifies related documents based on semantic similarity.
* **User Interface:** Provides a web interface for document exploration and management.
* **Document Text Extraction:** Extracts text from PDFs using the Nougat model and from audio/video files using Whisper.
* **Persistent Indexing:** Stores document embeddings and metadata in Redis for efficient retrieval.
* **Automatic Synchronization:** Keeps the index up-to-date with changes in the document collection using watchdog monitoring.

## Architecture

Chishiki's architecture consists of two main components:

### Backend (Flask Application)

* **Document Processing:** 
    * **Text Extraction:** Utilizes specialized libraries to extract text from various document formats:
        * **PDF:** Uses the Nougat model for accurate text extraction from PDF files.
        * **Audio/Video:** Extracts text from audio/video files using the Whisper model.
        * **Plain Text:** Directly reads text from plain text files.
    * **Passage Chunking:** Divides extracted text into smaller passages using a sliding window approach for granular indexing and retrieval.
    * **Embedding Generation:** Computes dense vector embeddings for each passage using the BGE (BAAI General Embedding Model).
    * **Lexical Weight Calculation:** Calculates sparse vector representations (lexical weights) for each passage.
* **Redis Datastore:**
    * **Passage Storage:** Stores passage embeddings, lexical weights, and metadata (document path, start/end positions, window size) in Redis.
    * **Document Metadata Storage:** Stores metadata for each document, including file hash, filename, tags, creation/modification times, file size, and ML synced status.
    * **Raw Text Storage:** Stores the raw text of each document for retrieval and display.
* **Search API:**
    * **Search Endpoint:** Handles search queries from the web UI, performing both dense and sparse retrieval.
    * **Similar Document Search:** Finds similar documents based on the cosine similarity of their mean dense vector embeddings.
    * **Metadata Search:** Allows filtering of documents based on various metadata attributes.
* **Synchronization:**
    * **Boot-time Synchronization:** Indexes all documents in the configured directory on startup.
    * **Watchdog Monitoring:** Detects changes in the document directory and automatically updates the index in real time.

### Web UI (Next.js Application)

* **Search Interface:**
    * **Search Bar:** Allows users to enter search queries.
    * **Metadata Filters:** Enables users to refine searches by file type, (creation/modification dates, file size, available soon), and custom tags.
    * **Advanced Settings:** Provides options to adjust search parameters like window size, number of results, and dense/sparse retrieval weights.
* **Document Management:**
    * **File Manager:** Displays the file tree of the configured document directory. Allows users to upload, download, and manage tags for their documents.
* **Result Display:**
    * **Passage Display:** Presents relevant passages from documents, highlighting matching keywords if enabled.
    * **Document Information:** Provides options to open, download, or find similar documents.

## Getting Started

### Prerequisites

* Docker: Ensure that Docker is installed and running on your system.

### Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/marcodsn/chishiki.git
   ```
2. **Build and Start the Docker Containers:**
   ```bash
   cd chishiki
   docker compose up -d
   ```
Or if you have a compatible GPU (tested on NVIDIA Ampere and Turing architectures):
   ```bash
   cd chishiki
   docker compose -f docker-compose.cuda.yml up -d
   ```

### Usage

1. **Access the Web UI:** Open your web browser and navigate to `http://localhost:3000`.
2. **Sync Your Documents:** Upon startup, Chishiki will automatically index the documents in your specified directory (data/ by default). Any subsequent changes to your document collection will be detected and synchronized in real time.
3. **Start Searching:** Enter your search queries in the search bar and explore the results. Use the sidebar to apply metadata filters and access advanced settings.

## Configuration

Chishiki's behavior can be customized by modifying the `config.json` file in the backend directory. Key configuration options include:

* **Redis Connection:** Specify the host and port for connecting to your Redis instance.
* **Backend Server:** Configure the host, port, and debug mode for the Flask application.
* **Window Sizes:** Define the window sizes for passage embedding computation.
* **Supported File Extensions:** Specify the file extensions of documents that Chishiki should index.
* **ML Service Settings:** Enable or disable ML services like BGE and Nougat, and configure their unload intervals.

## How It Works

1. **Document Indexing:** When a document is added or modified, the backend extracts its text, chunks it into passages, computes embeddings and lexical weights, and stores them in Redis along with relevant metadata.
2. **Search Query Processing:** When a user submits a search query, the web UI sends it to the backend's search endpoint.
3. **Combined Retrieval:** The backend performs both dense and sparse retrieval using the query embeddings and lexical weights. Dense retrieval finds semantically similar passages based on cosine similarity, while sparse retrieval matches keywords.
4. **Result Ranking:** Results from both retrieval methods are combined and ranked based on configurable weights.
5. **Result Display:** The web UI presents the ranked passages to the user, highlighting matching keywords if enabled. Users can then explore the relevant documents and discover similar documents.

## Advantages

* **Semantic Search:** Captures the meaning of search queries, not just keywords, leading to more accurate and relevant results.
* **Comprehensive Retrieval:** Combines dense and sparse retrieval methods to cover a wider range of search scenarios.
* **User-Friendly Interface:** Provides an intuitive and easy-to-use interface for managing and exploring documents.
* **Automatic Synchronization:** Ensures the index is always up-to-date with changes in your document collection.

## Contributing

Contributions to Chishiki are welcome. If you encounter any issues, have feature requests, or would like to contribute code, please open an issue or submit a pull request.

## License

Chishiki is licensed under the MIT License.