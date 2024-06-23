# Chishiki: Advanced Document Search Engine

Chishiki is a sophisticated document search engine built with Python and Redis, leveraging state-of-the-art machine learning models for efficient search and document management. It offers a user-friendly web interface for seamless interaction, allowing users to upload, search, and manage their documents with ease.

## Key Features

### Multi-Modal Search
Chishiki combines dense vector search with lexical matching to deliver highly relevant results. It utilizes the BGE-M3 model to generate dense vector representations of text passages, capturing semantic meaning. This approach, coupled with lexical matching, ensures both semantically relevant and lexically accurate search results.

### Comprehensive Metadata Search
Users can refine their searches using document metadata, including tags, file names, paths, and size filters. This granular control allows for precise document retrieval based on specific criteria.

### Robust Document Management
Chishiki provides a full-featured document management system, supporting various file formats (PDF, TXT, WAV, MP3, OGG, MP4). Users can:
- Upload and organize documents
- View and edit document metadata
- Manage document tags
- Download original files
- View extracted text content
- Discover semantically similar documents

### Customizable Search Settings
Fine-tune your search experience with advanced settings:
- Adjust window size for text passage analysis
- Set the number of results to display
- Balance dense retrieval weight vs. lexical matching
- Toggle query highlighting in search results

### Intuitive User Interface
The web UI, built with React and Tailwind CSS, offers a seamless experience for document management and search operations.

### Extensible Architecture
Chishiki's modular design allows for easy integration of new machine learning models and support for additional document formats.

## Technical Architecture

### Backend
- Powered by Python and Flask
- Utilizes Redis for high-performance data storage
- Integrates advanced ML models:
  - BGE-M3 for dense vector representations
  - Nougat for accurate PDF text extraction
  - Custom ASR model combining Whisper and PyAnnote for audio/video transcription

### Frontend
- Built with React and Next.js
- Styled using Tailwind CSS for responsive and efficient design

## Getting Started

### Prerequisites
- Docker
- Node.js and npm

### Installation
1. Clone the repository:

```bash
git clone https://github.com/your-username/chishiki.git
cd chishiki
```

2. Start the application using Docker Compose:

```bash
docker-compose up -d
```

3. Access the web UI at `http://localhost:3010`
