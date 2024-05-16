import { NextApiRequest, NextApiResponse } from 'next';

const BACKEND_URL = 'http://backend:7710';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { method, body, query } = req;

  try {
    let response;

    switch (method) {
      case 'GET':
        if (query.doc_path && query.action === 'download_file') {
          response = await fetch(`${BACKEND_URL}/download_file?doc_path=${encodeURIComponent(query.doc_path as string)}`, {
            method: 'GET',
          });

          if (!response.ok) {
            throw new Error(`Backend request failed with status ${response.status}`);
          }

          const fileBuffer = await response.arrayBuffer();
          res.status(response.status).send(Buffer.from(fileBuffer));
          return;
        } else if (query.action === 'get_doc_text') {
          response = await fetch(`${BACKEND_URL}/get_doc_text?doc_path=${encodeURIComponent(query.doc_path as string)}`, {
            method: 'GET',
          });
        } else if (query.action === 'get_doc_metadata') {
          response = await fetch(`${BACKEND_URL}/get_doc_metadata?doc_path=${encodeURIComponent(query.doc_path as string)}`, {
            method: 'GET',
          });
        } else {
          throw new Error('Invalid GET action');
        }
        break;

      case 'POST':
        if (body.action === 'ml_search') {
          response = await fetch(`${BACKEND_URL}/search`, {
            method: 'POST',
            body: JSON.stringify(body),
            headers: {
              'Content-Type': 'application/json',
            },
          });
        } else if (body.action === 'search_by_metadata') {
          response = await fetch(`${BACKEND_URL}/search_by_metadata`, {
            method: 'POST',
            body: JSON.stringify(body),
            headers: {
              'Content-Type': 'application/json',
            },
          });
        } else if (body.action === 'delete_doc') {
          response = await fetch(`${BACKEND_URL}/delete_doc`, {
            method: 'POST',
            body: JSON.stringify(body),
            headers: {
              'Content-Type': 'application/json',
            },
          });
        } else if (body.action === 'upload_file') {
          const formData = new FormData();
          formData.append('file', body.file);
          response = await fetch(`${BACKEND_URL}/upload_file`, {
            method: 'POST',
            body: formData,
          });
        } else if (body.action === 'insert_documents') {
          response = await fetch(`${BACKEND_URL}/insert_documents`, {
            method: 'POST',
            body: JSON.stringify(body),
            headers: {
              'Content-Type': 'application/json',
            },
          });
        } else if (body.action === 'create_index') {
          response = await fetch(`${BACKEND_URL}/create_index`, {
            method: 'POST',
          });
        } else if (body.action === 'flush_datastore') {
          response = await fetch(`${BACKEND_URL}/flush_datastore`, {
            method: 'POST',
          });
        } else if (body.action === 'save_datastore') {
          response = await fetch(`${BACKEND_URL}/save_datastore`, {
            method: 'POST',
          });
        } else if (body.action === 'search_similar_docs') {
          response = await fetch(`${BACKEND_URL}/search_similar_docs`, {
            method: 'POST',
            body: JSON.stringify(body),
            headers: {
              'Content-Type': 'application/json',
            },
          });
        } else {
          throw new Error('Invalid POST action');
        }
        break;

      default:
        throw new Error('Invalid request method');
    }

    if (!response.ok) {
      throw new Error(`Backend request failed with status ${response.status}`);
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json();
      res.status(response.status).json(data);
    } else {
      const data = await response.blob();
      res.status(response.status).send(data);
    }
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: error });
  }
}