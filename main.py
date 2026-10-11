"""
main.py

Yeh file real CV PDF ko test karne ke liye hai.
Flow:
1. loaders.py se CV PDF ka text nikalna
2. rag_pipeline.py se chunks banana + embed karna + Chroma mein store karna
3. Job description (JD) ke keywords se relevant chunks retrieve karna

Kaise use karein:
    python main.py

Isse pehle:
- data/ folder mein apni CV ki PDF rakh dein
- Neeche CV_PATH aur JD_QUERY ko apne hisaab se update kar lein
"""

from loaders import load_pdf
from rag_pipeline import split_text_into_chunks, store_chunks, retrieve_relevant_chunks


# ==== Yahan apni settings likhein ====

# Apni CV ka path (data/ foldser mein rakhein)
CV_PATH = "data/Amnabibi_cv.pdf"

# Job description ka matn, ya sirf JD ke important keywords/requirements
JD_QUERY = """
We are looking for a backend developer with experience in Python,
REST APIs, cloud deployment, and containerization.
"""

# Kitne top relevant chunks chahiye
TOP_K = 5


def main():
    print(f"CV load ho rahi hai: {CV_PATH}")
    try:
        cv_text = load_pdf(CV_PATH)
    except FileNotFoundError:
        print(f"\n Error: '{CV_PATH}' nahi mili.")
        print("   Apni CV ki PDF 'data' folder mein rakhein, ya CV_PATH update karein.\n")
        return

    print(f"CV se {len(cv_text)} characters nikle.\n")

    print("Text ko chunks mein toda ja raha hai...")
    chunks = split_text_into_chunks(cv_text)
    print(f"Total chunks: {len(chunks)}\n")

    print("Chunks ko embed karke Chroma mein store kiya ja raha hai...")
    vectorstore = store_chunks(chunks, collection_name="real_cv")

    print(f"\nJob description ke against relevant chunks dhoondhe ja rahe hain...")
    results = retrieve_relevant_chunks(vectorstore, JD_QUERY, k=TOP_K)

    print(f"\n=== Top {len(results)} relevant CV chunks ===\n")
    for i, chunk in enumerate(results, start=1):
        print(f"--- Chunk {i} ---")
        print(chunk.strip())
        print()


if __name__ == "__main__":
    main()