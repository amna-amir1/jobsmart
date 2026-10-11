# """
# Yeh file RAG ka asal kaam karti hai:
# 1. Text ko chunks mein todna
# 2. Chunks ko embeddings mein convert karna
# 3. Chroma (local vector store) mein save karna
# 4. Query ke hisaab se relevant chunks retrieve karna

# Abhi ke liye hum Chroma (local, free) use kar rahe hain.
# Baad mein Postgres/Supabase pe migrate karenge.
# """
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_community.vectorstores import Chroma
# from langchain_community.embeddings import HuggingFaceEmbeddings


# def split_text_into_chunks(text: str):
#     """
#     Bara text lo aur chote chote chunks mein todo,
#     taake matching aur retrieval better ho.
#     """
#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=500,      # har chunk mein kitne characters honge
#         chunk_overlap=50     # chunks ke beech thora overlap (context na tootay)
#     )
#     chunks = splitter.split_text(text)
#     return chunks


# def get_embedding_model():
#     """
#     Free, local embedding model use kar rahe hain
#     (koi API cost nahi lagti).
#     """
#     return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


# def store_chunks(chunks: list, collection_name: str = "cv_store"):
#     """
#     Chunks ko embeddings mein convert kar ke Chroma mein save karta hai.
#     """
#     embedding_model = get_embedding_model()

#     vectorstore = Chroma.from_texts(
#         texts=chunks,
#         embedding=embedding_model,
#         collection_name=collection_name,
#         persist_directory="./chroma_db"
#     )
#     return vectorstore


# def retrieve_relevant_chunks(vectorstore, query: str, k: int = 5):
#     """
#     Query (jaise JD ki requirements) ke hisaab se
#     sabse relevant chunks CV se nikalta hai.
#     """
#     results = vectorstore.similarity_search(query, k=k)
#     return [doc.page_content for doc in results]


# if __name__ == "__main__":
#     # Quick test
#     sample_text = """
#     Experienced Python developer with 3 years of experience in backend development.
#     Skilled in Django, FastAPI, and REST API design.
#     Worked on cloud deployment using AWS and Docker.
#     """

#     chunks = split_text_into_chunks(sample_text)
#     print(f"Total chunks: {len(chunks)}")

#     vectorstore = store_chunks(chunks)
#     results = retrieve_relevant_chunks(vectorstore, "backend development experience")

#     print("\nRelevant chunks found:")
#     for r in results:
#         print("-", r)
"""
Yeh file RAG ka asal kaam karti hai:
1. Text ko chunks mein todna
2. Chunks ko embeddings mein convert karna
3. Chroma (vector store) mein save karna — permanent ya temporary (ephemeral)
4. Query (jaise JD) ke hisaab se relevant chunks retrieve karna

Server (server.py) ke liye hum "ephemeral" mode use karte hain — matlab
har analyze request ke liye ek naya, temporary vector store banta hai jo
sirf memory mein rehta hai aur request khatam hote hi khud-ba-khud gayab
ho jata hai. Isse har CV ka data alag rehta hai aur disk pe kuch bhi
jama nahi hota.

main.py (manual testing) ke liye hum persistent mode (./chroma_db) use
karte hain, jaisa pehle tha.
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Embedding model sirf ek baar load ho, baar baar nahi (warna har request slow hogi)
_embedding_model = None


def split_text_into_chunks(text: str):
    """
    Bara text lo aur chote chote chunks mein todo,
    taake matching aur retrieval better ho.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,      # har chunk mein kitne characters honge
        chunk_overlap=50     # chunks ke beech thora overlap (context na tootay)
    )
    chunks = splitter.split_text(text)
    return chunks


def get_embedding_model():
    """
    Free, local embedding model use kar rahe hain (koi API cost nahi lagti).
    Pehli baar call hone par model download hota hai (~90MB), thora waqt lagega.
    Uske baad memory mein cached rehta hai.
    """
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embedding_model


def store_chunks(chunks: list, collection_name: str = "cv_store", persist_directory: str | None = "./chroma_db"):
    """
    Chunks ko embeddings mein convert kar ke Chroma mein save karta hai.

    persist_directory=None diya jaye to vector store sirf memory mein
    (ephemeral) banega — disk pe kuch save nahi hoga. Server har request
    ke liye isi tareeqe se use karta hai.
    """
    embedding_model = get_embedding_model()

    if persist_directory:
        vectorstore = Chroma.from_texts(
            texts=chunks,
            embedding=embedding_model,
            collection_name=collection_name,
            persist_directory=persist_directory,
        )
    else:
        vectorstore = Chroma.from_texts(
            texts=chunks,
            embedding=embedding_model,
            collection_name=collection_name,
        )

    return vectorstore


def retrieve_relevant_chunks(vectorstore, query: str, k: int = 5):
    """
    Query (jaise JD ki requirements) ke hisaab se
    sabse relevant chunks CV se nikalta hai.
    """
    results = vectorstore.similarity_search(query, k=k)
    return [doc.page_content for doc in results]


if __name__ == "__main__":
    # Quick test
    sample_text = """
    Experienced Python developer with 3 years of experience in backend development.
    Skilled in Django, FastAPI, and REST API design.
    Worked on cloud deployment using AWS and Docker.
    """

    chunks = split_text_into_chunks(sample_text)
    print(f"Total chunks: {len(chunks)}")

    vectorstore = store_chunks(chunks)
    results = retrieve_relevant_chunks(vectorstore, "backend development experience")

    print("\nRelevant chunks found:")
    for r in results:
        print("-", r)