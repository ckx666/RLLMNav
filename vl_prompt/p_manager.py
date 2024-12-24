import heapq
import re
from PIL import Image
import base64

def extract_integer_answer(s):
    match = re.search(r'Answer: \d+', s)
    if match:
        return int(match.group().split(' ')[-1])
    else:
        print('=====> No integer found in string')
        return -1
    
    
def extract_scores(s):
    match = re.search(r'Answer: \[(.*?)\]', s)
    if match:
        scores = [float(x) for x in match.group(1).split(',')]
        return scores.index(max(scores)), scores
    else:
        print('=====> No list found in string')
        return -1, []

def extract_top4_scores(s): #python 获取列表中最大的K的数以及它们的下标，包含重复数字情况
    match = re.search(r'\[(.*?)\]', s)
    if match:
        scores = [float(x) for x in match.group(1).split(',')]
        maxindex = scores.index(max(scores))
        top4_scores = heapq.nlargest(4,scores)
        top4_index = heapq.nlargest(4, range(len(scores)), key=lambda x: scores[x]) #按照在K中的值来排序一个range(len(K))生成的list，那这个list排序出来的结果是升序的，值就是该元素在原数组中对应的下标
        return top4_index, top4_scores, maxindex, max(scores)
    else:
        print('=====> No list found in string')
        return -1, []

def extract_objects(s):
    elements = re.findall(r'"([^"]*)"', s)
    return list(set(elements))
    

def object_query_constructor(objects):
    """
    Construct a query string based on a list of objects

    Args:
        objects: torch.tensor of object indices contained in an area

    Returns:
        str query describing the area, eg "This area contains toilet and sink."
    """
    assert len(objects) > 0
    query_str = "This area contains "
    names = []
    for ob in objects:
        names.append(ob.replace("_", " "))
    if len(names) == 1:
        query_str += names[0]
    elif len(names) == 2:
        query_str += names[0] + " and " + names[1]
    else:
        for name in names[:-1]:
            query_str += name + ", "
        query_str += "and " + names[-1]
    query_str += "."
    return query_str

def get_frontier_prompt(prompt_type):
    if prompt_type == "deterministic":
        from vl_prompt.prompt.deterministic import \
            SYSTEM_PROMPT, USER1, ASSISTANT1, USER2, ASSISTANT2,USER3, ASSISTANT3
    elif prompt_type == "scoring_positive":
        from vl_prompt.prompt.scoring_positive import \
            SYSTEM_PROMPT, USER1, ASSISTANT1, USER2, ASSISTANT2,USER3, ASSISTANT3
    elif prompt_type == "scoring_negative":
        from vl_prompt.prompt.scoring_negative import \
            SYSTEM_PROMPT, USER1, ASSISTANT1, USER2, ASSISTANT2,USER3, ASSISTANT3
    else:
        raise NotImplementedError("Froniter prompt type not implemented.")
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER1},
        {"role": "assistant", "content": ASSISTANT1},
        {"role": "user", "content": USER2},
        {"role": "assistant", "content": ASSISTANT2},
        {"role": "user", "content": USER3},
        {"role": "assistant", "content": ASSISTANT3}
    ]
    
    return messages


def get_candidate_prompt(candidate_type):
    if candidate_type == "open":
        from vl_prompt.prompt.candidate_open import \
        SYSTEM_PROMPT, USER1, ASSISTANT1, USER2, ASSISTANT2
    elif candidate_type == "close":
        from vl_prompt.prompt.candidate_close import \
        SYSTEM_PROMPT, USER1, ASSISTANT1, USER2, ASSISTANT2
    else:
        raise NotImplementedError("Candidate prompt type not implemented.")
        
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER1},
        {"role": "assistant", "content": ASSISTANT1},
        {"role": "user", "content": USER2},
        {"role": "assistant", "content": ASSISTANT2}
    ]
    
    return messages

def get_grouping_prompt():
    from vl_prompt.prompt.group_obj import \
        SYSTEM_PROMPT, USER1, ASSISTANT1, USER2, ASSISTANT2
        
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER1},
        {"role": "assistant", "content": ASSISTANT1},
        {"role": "user", "content": USER2},
        {"role": "assistant", "content": ASSISTANT2}
    ]
    
    return messages

from ollama import Client
def get_discover_prompt(img, objects):
    from vl_prompt.prompt.discover import \
        SYSTEM_PROMPT, USER
        
    img.save("current_for_gpt4.jpg")
    with open("current_for_gpt4.jpg", "rb") as image_file:
        img = base64.b64encode(image_file.read()).decode('utf-8')


    question = f"""Current object list: {objects}\n{USER}"""
    '''
    payload = {
        "model": "llava", "messages": [{
            "role": "system", "content": SYSTEM_PROMPT
            }, {
            "role": "user", "content": [
                {"type": "text", "text": question}, 
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}
            ]
        }], "max_tokens": 300
    }
    '''
    client = Client(host='http://localhost:11434')

    response = client.chat(model='llava', messages=[
        {
            "role": "system", "content": """You are an intelligent assistant called DiscoverVLM that can understand natural language and scene images. Given a list of objects and an image, your goal is to discover new objects in the image that are not in the list.

You should consider the following rules when discovering new objects:

(1) You should first consider, what's in the image? Note that you should only include objects in the house, and avoid things that are part of the house, like ceiling, wall, floor, window etc and avoid room names, like bedroom, kitchen, etc.

(2) Considering the given object list, you should only output things that are not in the list or are not similar to things in the list because your duty is to discover new things. For example, if the given object list contains "couch" or "tv", you should not output "sofa" or "television" because they are similar.

(3) Confirm that the objects you output are in the image. For example, if the image is a bedroom, you should not output "bathtub" because it is impossible to find a bathtub in a bedroom. And also confirm the objects you output don't violate rule (1).

(4) Avoid objects are common everywhere. For example, objects like light switch and door are present in every room, so you should not output them.

Your output should be in the form of "Answer: <list of objects>" such as:

Answer: ["chair", "bed", "bottle"] 

notice Answer is not like this below : 
- A carpet with a visible seam where the two sections meet. 
- A portion of a tile floor.
- A baseboard heater in the foreground.
"""
        },

        {
            'role': 'user',
            'content': question,
            'images': [img]
        },
    ])

    return response