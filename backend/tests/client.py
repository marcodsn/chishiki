import requests

def test_create_index():
    response = requests.post("http://localhost:7710/create_index")
    assert response.status_code == 200
    
def test_flush_datastore():
    response = requests.post("http://localhost:7710/flush_datastore")
    print(response.json())
    assert response.status_code == 200
    
def test_save_index():
    response = requests.post("http://localhost:7710/save_index")
    assert response.status_code == 200
    
def test_load_index():
    response = requests.post("http://localhost:7710/load_index")
    assert response.status_code == 200
    
def test_insert_passage():
    response = requests.post("http://localhost:7710/insert_passage", json={"text": "Hello world", "doc_path": "test.txt"})
    response = requests.post("http://localhost:7710/insert_passage", json={"text": "Hello universe", "doc_path": "test_2.txt"})
    print(response.json())
    assert response.status_code == 200
    
def test_search(query_text="Hello world"):
    response = requests.post("http://localhost:7710/search", json={"query_text": query_text, "window_size": 512})
    print(response.json())
    print(response.json()["results"][0]["text"])
    print(response.json()["results"][0]["doc_path"])
    print(response.json()["results"][0]["scores"])
    assert response.status_code == 200
    
def test_insert_document(doc_path="test.txt"):
    print(doc_path)
    response = requests.post("http://localhost:7710/insert_document", json={"doc_path": doc_path, "window_size": 512})
    assert response.status_code == 200
    
def test_get_document_count():
    response = requests.get("http://localhost:7710/get_document_count")
    print(response.json())
    assert response.status_code == 200
    
def test_get_passage_count():
    response = requests.get("http://localhost:7710/get_passage_count")
    print(response.json())
    assert response.status_code == 200
    
def test_get_document_by_path(doc_path="test.txt"):
    response = requests.get("http://localhost:7710/get_document_by_path", params={"doc_path": doc_path})
    try:
        response_json = response.json()
        print(response_json)
    except requests.exceptions.JSONDecodeError as e:
        print("Failed to decode JSON from response:")
        print(f"Response status code: {response.status_code}")
        print(f"Response text: {response.text}")
    assert response.status_code == 200
    
# # Pipeline 1:
# try:
#     test_flush_datastore()
# except:
#     pass
# try:
#     test_create_index()
# except:
#     pass
# test_insert_passage()
# test_search()

# Pipeline 2:
# try:
#     test_flush_datastore()
# except:
#     print("Error")
#     pass
# try:
#     test_create_index()
# except:
#     pass
# test_insert_document("/Users/marco/Documents/tirocinio/data/papers/RetNet.pdf")
# test_search("RetNet")
# test_search("Inference Cost Scaling Curve")
# test_get_document_count()
# test_get_passage_count()

# Pipeline 3:
# try:
#     test_flush_datastore()
# except:
#     print("Error flushing datastore")
#     pass
# try:
#     test_create_index()
# except:
#     print("Error creating index")
#     pass
# # test_insert_document("/mnt/data/chishiki/data/papers/Hyena.pdf")
# test_insert_document("/mnt/data/chishiki/data/papers/RetNet.pdf")
# # test_insert_document("/mnt/data/chishiki/data/papers/RETRO.pdf")
test_get_document_count()
test_get_passage_count()
test_get_document_by_path("data/papers/RetNet.pdf")
