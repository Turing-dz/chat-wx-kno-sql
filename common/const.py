# bot_type
OPEN_AI = "openAI"
CHATGPT = "chatGPT"
BAIDU = "baidu"
CHATGPTONAZURE = "chatGPTOnAzure"
CHATGML = "chatGML"
PAUSE = False # 项目启动(False)，暂停（True）
MODEL_PATH = f"D:/ChatGLM3_main/model/chatglm3_6b" # 模型路径
# MODEL_PATH = "D:/Projects/ChatWLW/model/chatglm2-6b" # 模型路径
GPU = True # 是否使用显卡
GPU_LEVEL = "int4" # choices=["fp16", "int4", "int8"] 默认int8 可在8G显存上运行，int 4可在6G显存上运行， fp16 需要13G以上显存
SAY = "say" # 调用对话模型
DRAW = "draw" # 调用绘图模型
SEARCH = "search" # 调用搜索模型
SQL='sql'
KNO='kno'
# chatGLM入参
max_length = 2048
# max_length =8192
top_p = 0.7       
temperature = 0.95
#知识库相关配置
rtst_model_path = "/model/m3e-base"
# rtst_memory_path = "/kno/memory/"
rtst_memory_path = "./memory/"
rtst_source_path = "/kno/txt"
rtst_count = "1"
rtst_size = "30"
rtst_overlap = "0"
rtst_device = "cuda"
rtst_step = "15"
# rtst_memory_name="default"
