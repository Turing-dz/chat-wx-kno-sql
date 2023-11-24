# encoding:utf-8
from langchain import SQLDatabase, SQLDatabaseChain
import pymysql
import re
import requests
import torch
from bot.bot import Bot
from bridge.reply import Reply, ReplyType
from transformers import AutoModel, AutoTokenizer
from  common.const import PAUSE, MODEL_PATH, GPU, GPU_LEVEL
from common import const
from common.util import Util
from PIL import Image
import re
from kno import two_match
import pyodbc
# 本地部署的chatGML模型（与app.py系统启动在同一个环境下）
#class ChatGML(Bot):
class ChatGML():
    history = []
    def __init__(self):
        # global sd_model_dict # sd模型的model_name与model_hash
        if PAUSE == False:
            # print("初始化stable diffusion...")
            # print("读取sd模型...")
            # model_name, model_hash = Util.stable_diffusion_get_sd_models()
            # sd_model_dict = dict(zip(model_name, model_hash))
            # print("读取本地的sd_model成功...")

            print("初始化chatGML....")
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH,trust_remote_code=True)
            
            self.model = AutoModel.from_pretrained(MODEL_PATH, trust_remote_code=True, device='cuda')
            # self.model = AutoModel.from_pretrained(MODEL_PATH, trust_remote_code=True, device='cuda').quantize(4).half().cuda()
            # if GPU == False:
            #     self.model = self.model.float()
            # else:
            #     if GPU_LEVEL == "fp16":
            #         self.model = self.model.half().cuda()
            #         print("启动fp16")
            #     elif GPU_LEVEL == "int4":
            #         print("启动int4")
            #         self.model = self.model.half().quantize(4).cuda()
            #         print("启动int4")
            #     elif GPU_LEVEL == "int8":
            #         self.model = self.model.half().quantize(8).cuda()
            #         print("启动int8")
            self.model = self.model.eval()
            self.history = []
            self.readable_history = []
            print("初始化chatGML完成")
        else:
            print("模型暂停启动，如需启动，请修改common.const.PAUSE为False")
        

    def predict(self, query, max_length, top_p, temperature, drawHistory):
        global history
        if(len(self.readable_history) > 10):
            self.readable_history=[]
        if self.isNotBlank(drawHistory):
            output, history = self.model.chat(
            self.tokenizer, query=query, 
            # history=drawHistory,
            history=[],
            max_length=max_length,
            top_p=top_p,
            temperature=temperature)
            return output
        else:
            print("self.readable_history")
            print(self.readable_history)
            # self.readable_history=[]
            output, history = self.model.chat(
            self.tokenizer, query=query,
            history=[],
            # history=self.readable_history[0] if self.readable_history and self.readable_history[0] else [],
            max_length=max_length,
            top_p=top_p,
            temperature=temperature)
            self.readable_history.append((query, ChatGML.parse_codeblock(ChatGML, output)))
            return output, self.readable_history
    def predict_sql(self, query, max_length, top_p, temperature, drawHistory):
        global history
        # conn_sqlserver = pyodbc.connect('DRIVER={SQL Server};''SERVER=localhost;''DATABASE=电商数据库;''Trusted_Connection=yes;')
        cursor = conn_pymysql.cursor()
        # cursor = conn_sqlserver.cursor()
        question=query
        from sql.self_prompt import tableinfo
        result_info = f"{tableinfo}".replace("{question}", question)
        # print(result_info)

        sql_query,_=self.predict(result_info, max_length, top_p, temperature, drawHistory)
        print({sql_query})
        pattern = r"(SELECT.*)"
        match = re.search(pattern, sql_query)
        if match:
            sql_query=match.group(1)
        print({sql_query})
        try:
            cursor.execute(sql_query)
            sql_response = cursor.fetchall()
            print(sql_response)
            # 根据sql语句和返回的response请求大模型将问题答案转成自然语言
            from sql.self_prompt import sql_question_to_answer
            sql_question_to_answer = f"{sql_question_to_answer}".replace("{first_format}", str(sql_query)).replace("{second_format}", str(sql_response)).replace("{question}", question)
            response,_ = self.predict(sql_question_to_answer, max_length, top_p, temperature, drawHistory)
            conn_pymysql.close()
            # conn_sqlserver.close()
            print(response)
            return response,_
        except Exception as e:
            response,_ = self.predict(query, max_length, top_p, temperature, drawHistory)
            return response,_
        
    def predict_kno(self, query, max_length, top_p, temperature, drawHistory):
        global history
        memory_name=const.rtst_memory_name
        results = ''  # 初始化知识库查询结果
        response_d = two_match.find(query, memory_name=memory_name)
        if len(response_d) == 0:  # 如果检索不到知识
            response,_ = self.predict(query, max_length, top_p, temperature, drawHistory)
            return response,_
        else:  # 将知识作为系统消息的一部分添加到 input 中
            results = '\n'.join([str(i + 1) + ". " + re.sub('\n\n', '\n',
                                                            response_d[i]['content']) for i in
                                    range(len(response_d))])
            if results=='':# 如果没有从知识库中找到任何信息,直接调用模型进行输入
                response,_ = self.predict(query, max_length, top_p, temperature, drawHistory)
            else:
                prompt = '请根据以下内容回答问题：' + query + "\n" + results
                response,_ = self.predict(prompt, max_length, top_p, temperature, drawHistory)
            return response,_
    def parse_codeblock(cls, text):
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "```" in line:
                if line != "```":
                    lines[i] = f'<pre><code class="{lines[i][3:]}">'
                else:
                    lines[i] = '</code></pre>'
            else:
                if i > 0:
                    lines[i] = "<br/>" + line.replace("<", "&lt;").replace(">", "&gt;")
        return "".join(lines)


    # 删除请求字符中开头的多余空格和逗号
    def deleteInvalid(self, query):
        return query.lstrip(" ,，")

    # 判断空字符
    def isNotBlank(self, s):
        return s is not None and bool(s and isinstance(s, list))

    # 向模型发起聊天会话
    def reply(self, query, context = None):
        print("执行进入了chatGML模型")
        if PAUSE == True:
            reply = Reply(ReplyType.TEXT, "目前项目停止，小周同学正在快马加鞭DEBUG中...")
            return reply
        else:
            prompt_history = None
            print(const,query)
            if const.KNO in query[:3]:
                print("进入知识库查询........")
                reply = None
                reply = Reply(ReplyType.TEXT, self.predict_kno(query[3:],const.max_length, const.top_p, const.temperature, prompt_history)[0])
                return reply
            elif const.SQL in query[:3]:
                print("进入数据库查询........")
                reply = None
                reply = Reply(ReplyType.TEXT, self.predict_sql(query[3:],const.max_length, const.top_p, const.temperature, prompt_history)[0])
                return reply
            else:
                print("进入对话模型........")
                # print(torch.cuda.memory_summary())
                reply = None
                # prompt_history = [["你是一个调皮的智障，无论我问你什么问题，你都回答说：你猜"]]
                reply = Reply(ReplyType.TEXT, self.predict(query,const.max_length, const.top_p, const.temperature, prompt_history)[0])
                print(reply)
                return reply

    def run():
        print("初始化chat_gml_bot...")
        ChatGML.reply(ChatGML,"testText")
        