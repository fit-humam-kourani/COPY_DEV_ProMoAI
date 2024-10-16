from utils.prompting import create_conversation

desc = open("../testfiles/long_descriptions/hotel.txt", "r").read()

prompt = create_conversation(desc)[0]['content']

print(prompt)