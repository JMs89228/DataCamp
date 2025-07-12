import os
from langchain_community.document_loaders import CSVLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatOllama
from langchain.text_splitter import CharacterTextSplitter

CHROMA_DIR = "chroma_db"
EMBEDDING_MODEL = "nomic-embed-text:latest"

def build_vectorstore_from_csv(csv_path: str):
    loader = CSVLoader(file_path=csv_path, encoding="utf-8")
    docs = loader.load()

    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = text_splitter.split_documents(docs)

    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)  # Ollama 的嵌入模型
    vectorstore = Chroma.from_documents(split_docs, embeddings, persist_directory=CHROMA_DIR)
    vectorstore.persist()

    return vectorstore

def load_qa_chain():
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=OllamaEmbeddings(model=EMBEDDING_MODEL))
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    llm = ChatOllama(model="gemma3:12b")
    qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever, return_source_documents=True)
    return qa_chain
