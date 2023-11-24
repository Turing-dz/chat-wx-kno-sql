from langchain.vectorstores.faiss import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
import sentence_transformers
import numpy as np
import re,os
import sys
import os
# 获取当前脚本的父目录路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# 将父目录添加到 sys.path 中
sys.path.append(parent_dir)
from common import const

#最大抽取数量
rtst_count=const.rtst_count
#分块大小"
rtst_size=const.rtst_size
#分块重叠长度
rtst_overlap=const.rtst_overlap
#向量模型存储路径
rtst_model_path=const.rtst_model_path
#外挂知识库地址
rtst_memory_path=const.rtst_memory_path
#embedding运行设备
rtst_device=const.rtst_device
#知识库默认上下文步长
rtst_step=const.rtst_step
vectorstores={}
try:
    print('知识库路径为 '+rtst_model_path)# 打印路径，查看是否路径错误
    embeddings = HuggingFaceEmbeddings(model_name='')
    # print('path is '+embeddings)
    embeddings.client = sentence_transformers.SentenceTransformer(rtst_model_path,device=rtst_device)
except Exception  as e:
    print("embedding加载失败，请下载语义知识库计算模型",r"https://github.com/l15y/wenda#st%E6%A8%A1%E5%BC%8F")
    raise e
def get_vectorstore(memory_name):
    try:
        return vectorstores[memory_name]
    except Exception  as e:
        try:
            vectorstores[memory_name] = FAISS.load_local(
                rtst_memory_path+memory_name, embeddings=embeddings)
            return vectorstores[memory_name]
        except Exception  as e:
            print("没有读取到RTST记忆区%s，将新建。"%memory_name)
    return None
def get_doc_by_id(id,memory_name):
    return vectorstores[memory_name].docstore.search(vectorstores[memory_name].index_to_docstore_id[id])
def process_strings(A, C, B):
    # find the longest common suffix of A and prefix of B
    common = ""
    for i in range(1, min(len(A), len(B)) + 1):
        if A[-i:] == B[:i]:
            common = A[-i:]
    # if there is a common substring, replace one of them with C and concatenate
    if common:
        return A[:-len(common)] + C + B
    # otherwise, just return A + B
    else:
        return A + B
def get_doc(id,score,step,memory_name):
    doc = get_doc_by_id(id,memory_name)
    final_content=doc.page_content
    # print("文段分数：",score,[doc.page_content])
    if step > 0:
        for i in range(1, step+1):
            try:
                doc_before=get_doc_by_id(id-i,memory_name)
                if doc_before.metadata['source']==doc.metadata['source']:
                    final_content=process_strings(doc_before.page_content,divider,final_content)
                    # print("上文分数：",score,doc.page_content)
            except:
                pass
            try:
                doc_after=get_doc_by_id(id+i,memory_name)
                if doc_after.metadata['source']==doc.metadata['source']:
                    final_content=process_strings(final_content,divider,doc_after.page_content)
            except:
                pass
    if doc.metadata['source'].endswith(".pdf") or doc.metadata['source'].endswith(".txt"):
        title=f"[{doc.metadata['source']}](/api/read_news/{doc.metadata['source']})"
    else:
        title=doc.metadata['source']
    return {'title': title,'content':re.sub(r'\n+', "\n", final_content),"score":int(score)}
def find(s,step = rtst_step,memory_name="default"):
    try:
        # 获取输入s的嵌入向量（embedding）
        embedding = get_vectorstore(memory_name).embedding_function(s)
        # 获取到的嵌入向量通过索引搜索操作，在vectorstores[memory_name]中查找与输入向量最相似的项，并返回一组相似度得分和对应的索引
        scores, indices = vectorstores[memory_name].index.search(np.array([embedding], dtype=np.float32), int(rtst_count))
        # 创建一个空列表docs，用于存储找到的文档（documents）
        docs = []
        # 使用enumerate函数遍历相似度得分和索引的列表。对于每个索引i和相似度得分scores[0][j]
        for j, i in enumerate(indices[0]):
            if i == -1:# 如果索引i为-1，则跳过当前循环
                continue
            if scores[0][j]>700:continue# 如果相似度得分scores[0][j]大于700，则跳过当前循环
            docs.append(get_doc(i,scores[0][j],int(step),memory_name))# 调用get_doc(i, scores[0][j], step, memory_name)函数，获取对应索引的文档，并将文档信息添加到docs列表中
        return docs
    except Exception as e:# 如果在执行过程中发生异常，将打印异常信息，并返回一个空列表
        print(e)
        return []