import re

import openai
from openai import OpenAI

from vl_prompt.p_manager import   extract_objects, \
    get_frontier_prompt, get_candidate_prompt, get_grouping_prompt, get_discover_prompt,extract_top4_scores

# should be replaced by your API key
with open("./apikey.txt") as f:
    # key order：temp key, long-term, mine
    keys = f.read().split("\n")
    openai.api_key = keys[0] # NOTE: change key before running

client = OpenAI(
    base_url = 'http://localhost:11434/v1',
    api_key='ollama', # required, but unused
)

class LLM():
    def __init__(self, goal_name, prompt_type):
        self.api_name = "llama3"
        # self.api_name = "gpt-3.5-turbo"
        self.goal_name = goal_name
        self.prompt_type = prompt_type
        self.history = []
    
    def inference_once(self, system_prompt, message):
        if message:
            msg = {
                "role": "user",
                "content": message
            }
            self.history = system_prompt + [msg]
            try:
#                chat = openai.ChatCompletion.create(
#                    model=self.api_name, messages=self.history,
#                    temperature=0
#                )
                chat = client.chat.completions.create(
                    model="llama3",
                    messages=self.history,
                    temperature=0
                )
            except Exception as e:
                print(f"=====> llm inference error: {e}")
                chat = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo", messages=self.history,
                    temperature=0
                )
        reply = chat.choices[0].message.content

        return reply
    
    def discover_objects(self, img, objects):
        response = get_discover_prompt(img, objects)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai.api_key}"
        }
        #response = requests.post("http://localhost:11434/api/chat", headers=headers, json=payload)



        print("2"+str(response))
        #print("2!" + response)
        #reply = response.json()["choices"][0]["message"]["content"]
        reply = response["message"]["content"]
        print("3"+str(reply))
        print("3!" + reply)
        c = extract_objects(reply)
        print("--------------discover_objects------------"+str(c))
        return c
        
    def inference_accumulate(self, message):
        if message:
            self.history.append(
                {"role": "user", "content": message},
            )
            try:
                chat = client.chat.completions.create(
                    model="llama3",
                    messages=self.messages
                )
                #chat = openai.ChatCompletion.create(
                #    model=self.api_name, messages=self.messages
                #)
            except Exception as e:
                print(f"=====> gpt-4-turbo error: {e}")
                chat = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo", messages=self.history,
                    temperature=0
                )
            
        reply = chat.choices[0].message.content
        # print(reply)
        self.history.append({"role": "assistant", "content": reply})
        return reply
    
    def choose_frontier(self, message, num):
        total_reply_positive=[]
        total_reply_negative = []
        for i in range(num):  # 重复三次打分
            #print("i", i)
            system_prompt = get_frontier_prompt("scoring_positive")
            text_reply_positive = self.inference_once(system_prompt, message)
            #print("text_reply_positive", text_reply_positive)
            reply_positive = re.search(r'Answer: \[(.*?)\]', text_reply_positive)
            try:
                reply_positive = [float(x) for x in reply_positive.group(1).split(',')]
            except Exception as e:
                print("reply_positive",e)
                reply_positive = [0.5]
            if i==0:
                shape = len(reply_positive)
                for j in range(shape):
                    total_reply_positive.append(0)
                    total_reply_negative.append(0)
            #print("reply_positive", reply_positive)
            total_reply_positive = [x + y for x, y in zip(total_reply_positive, reply_positive)]
            print("total_reply_positive", total_reply_positive)
            system_prompt = get_frontier_prompt("scoring_negative")
            text_reply_negative = self.inference_once(system_prompt, message)
            #print("text_reply_negative", text_reply_negative)
            reply_negative = re.search(r'Answer: \[(.*?)\]', text_reply_negative)
            if reply_negative is not None:
                try:
                    reply_negative = [1-float(x) for x in reply_negative.group(1).split(',')]
                except Exception as e:
                    print("reply_negative",e)
                    reply_negative = []
                    for j in range(len(reply_positive)):
                        reply_negative.append(0.5)
                #print("reply_negative", reply_negative)
                total_reply_negative = [x + y for x, y in zip(total_reply_negative, reply_negative)]
                print("total_reply_negative", total_reply_negative)

        reply = [(x + y) / (num*2) for x, y in zip(total_reply_positive, total_reply_negative)]
        print("replyscore", reply)
        answer_rank, scores, maxindex, maxscores = extract_top4_scores(str(reply))


        return answer_rank, reply,maxindex, maxscores, scores
        
    def imagine_candidate(self, instr):
        system_prompt = get_candidate_prompt(candidate_type="open")
        reply = self.inference_once(system_prompt, instr)
        c = extract_objects(reply)
        return c
    
    def group_candidate(self, clist, nlist):
        system_prompt = get_grouping_prompt()
        message = f"Current object list: {clist}\n\nNew object list: {nlist}"
        reply = self.inference_once(system_prompt, message)
        c = extract_objects(reply) # newly discovered object list
        new_c = []
        for ob in c:
            if ("room" in ob) or ("wall" in ob) or ("floor" in ob) or ("ceiling" in ob):
                continue
            new_c.append(ob)
        return new_c