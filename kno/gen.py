import sentence_transformers
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document
import threading
import pdfplumber
import re
import chardet
import os
import sys
import time
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# 将父目录添加到 sys.path 中
sys.path.append(parent_dir)
from common import const
from pathlib import Path
# 定义rtst模型和知识库路径
model_path=const.rtst_model_path
memory_path=const.rtst_memory_path
memory_name=const.rtst_memory_name
knowledge_path = memory_path+memory_name
knowledge_path = Path(knowledge_path)
# 设置外挂知识库的地址
source_folder_path=const.rtst_source_path
class CounterLock:
    def __init__(self):
        self.lock = threading.Lock()
        self.waiting_threads = 0 # 初始化等待中的线程数量
        self.waiting_threads_lock = threading.Lock()

    def acquire(self):
        with self.waiting_threads_lock:
            self.waiting_threads += 1
        acquired = self.lock.acquire()

    def release(self):
        self.lock.release()
        with self.waiting_threads_lock:
            self.waiting_threads -= 1

    def get_waiting_threads(self):
        with self.waiting_threads_lock:
            return self.waiting_threads

    def __enter__(self):  # 实现 __enter__() 方法，用于在 with 语句的开始获取锁
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # 实现 __exit__() 方法，用于在 with 语句的结束释放锁
        self.release()
import torch
torch.set_num_threads(4)

# if settings.librarys.rtst.backend=="Annoy":
    # from langchain.vectorstores.annoy import Annoy as Vectorstore
# else:
from langchain.vectorstores.faiss import FAISS as Vectorstore



import logging
logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.ERROR)

root_path_list = source_folder_path.split(os.sep)
docs = []
vectorstore = None

# model_path = settings.librarys.rtst.model_path
try:
    embeddings = HuggingFaceEmbeddings(model_name='')
    embeddings.client = sentence_transformers.SentenceTransformer(
        model_path, device="cpu")
except Exception as e:
    print("Embedding加载失败，请更新Embedding模型",
                 r"https://huggingface.co/moka-ai/m3e-base")
    raise e

print("Embedding加载完成！")

embedding_lock=CounterLock()
vectorstore_lock=threading.Lock()
def clac_embedding(texts, embeddings, metadatas):
    global vectorstore
    with embedding_lock:
        vectorstore_new = Vectorstore.from_texts(texts, embeddings, metadatas=metadatas)
    with vectorstore_lock:
        if vectorstore is None:
            vectorstore = vectorstore_new
        else:
            vectorstore.merge_from(vectorstore_new)
# 向量化
def make_index():
    global docs
    # # if hasattr(settings.librarys.rtst,"size") and hasattr(settings.librarys.rtst,"overlap"):
    #     text_splitter = CharacterTextSplitter(
    #         chunk_size=int(settings.librarys.rtst.size), chunk_overlap=int(settings.librarys.rtst.overlap), separator='\n')
    # else:
    text_splitter = CharacterTextSplitter(
        chunk_size=20, chunk_overlap=0, separator='\n')
    doc_texts = text_splitter.split_documents(docs)
    docs = []
    texts = [d.page_content for d in doc_texts]
    metadatas = [d.metadata for d in doc_texts]
    thread = threading.Thread(target=clac_embedding, args=(texts, embeddings, metadatas))
    thread.start()
    while embedding_lock.get_waiting_threads()>2:
        time.sleep(0.1)

all_files=[]

for root, dirs, files in os.walk(source_folder_path):
    for file in files:
        all_files.append([root, file])
print("文件列表生成完成！",len(all_files))
length_of_read=0
for i in range(len(all_files)):
    root, file=all_files[i]
    data = ""
    title = ""
    try:
        file_path = os.path.join(root, file)
        _, ext = os.path.splitext(file_path)
        if ext.lower() == '.pdf':
            #pdf
            with pdfplumber.open(file_path) as pdf:
                data_list = []
                for page in pdf.pages:
                    print(page.extract_text())
                    data_list.append(page.extract_text())
                data = "\n".join(data_list)
        elif ext.lower() == '.txt':
            # txt
            with open(file_path, 'rb') as f:
                b = f.read()
                result = chardet.detect(b)
            with open(file_path, 'r', encoding=result['encoding']) as f:
                data = f.read()
        else:
            print("目前还不支持文件格式：", ext)
    except Exception as e:
        print("文件读取失败，当前文件已被跳过：",file,"。错误信息：",e)
    data = re.sub(r'！', "！\n", data)
    data = re.sub(r'：', "：\n", data)
    data = re.sub(r'。', "。\n", data)
    data = re.sub(r'\r', "\n", data)
    data = re.sub(r'\n\n', "\n", data)
    data = re.sub(r"\n\s*\n", "\n", data)
    length_of_read+=len(data)
    docs.append(Document(page_content=data, metadata={"source": file}))
    if length_of_read > 1e5:
        print("处理进度",int(100*i/len(all_files)),f"%\t({i}/{len(all_files)})")
        make_index()
        # print(embedding_lock.get_waiting_threads())
        length_of_read=0


if len(all_files) == 0:
    print("txt 目录没有数据")
    sys.exit(0)

if len(docs) > 0:
    make_index()

while embedding_lock.get_waiting_threads()>0:
    time.sleep(0.1)
print("处理进度",100,"%")
with embedding_lock:
    time.sleep(0.1)
    with vectorstore_lock:
        print("处理完成")
try:
    vectorstore_old = Vectorstore.load_local(knowledge_path, embeddings=embeddings)
    print("合并至已有索引。如不需合并请删除 "+memory_path+" 文件夹")
    vectorstore_old.merge_from(vectorstore)
    vectorstore_old.save_local(knowledge_path)
except:
    print("新建索引")
    vectorstore.save_local(knowledge_path)
    print("保存完成")
