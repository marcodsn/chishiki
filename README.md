# Chishiki Document Search Engine

## Overview
Chishiki is a modern document search engine that combines semantic search capabilities with traditional lexical matching. Built with Next.js, Flask, and PostgreSQL with pgvector, it provides an efficient and user-friendly solution for searching through document collections.

## Features
- Semantic search using BGE-M3 embedding model
- Support for multiple document formats (PDF, TXT, DOCX, etc.)
- Hybrid search combining dense embeddings and lexical matching, with adjustable weights
- Document tagging and metadata management
- Light/Dark mode support
- Real-time file system synchronization
- User-friendly web interface
- Docker support (CPU & GPU versions)

## Tech Stack
- **Frontend**: Next.js with [Radix UI](https://www.radix-ui.com/) and [Shadcn](https://ui.shadcn.com/)
- **Backend**: Flask (Python)
- **Database**: PostgreSQL with pgvector
- **Embedding Model**: [BGE-M3](https://huggingface.co/BAAI/bge-m3) from BAAI
- **Text Extraction**: [docling](https://github.com/DS4SD/docling)
- **Containerization**: Docker & Docker Compose

## Prerequisites
- Docker and Docker Compose
- NVIDIA GPU (optional, for GPU acceleration)

## Installation
1. Clone the repository:
```bash
git clone https://github.com/marcodsn/chishiki.git
cd chishiki
```

2. Start the application:
```bash
# For CPU-based deployment
docker-compose up -d

# For GPU-accelerated deployment
docker-compose -f docker-compose.cuda.yml up -d
```

## Usage
1. Access the web interface at `http://localhost:3010`
2. Upload documents through the file management interface (check notes below)
3. Use the search bar to perform semantic searches
4. Manage documents, tags and search settings through the UI

NOTE 1: The first time you start the application, it may take a few minutes to download the BGE-M3 model and set up the database.
NOTE 2: The upload functionality is currently broken, and documents must be manually placed in the `data` directory.

## License
This project is not yet licensed, and as such, all rights are reserved at this time.
A license will be added in the future to clarify the terms of use.

## Acknowledgments
- [BAAI for the BGE-M3 embedding model](https://huggingface.co/BAAI/bge-m3)
- [docling](https://github.com/DS4SD/docling) for their great text extraction tool
- PostgreSQL and pgvector teams for building such amazing tools
