import csv
from tqdm import tqdm

def is_zh(in_str):
    return (set(in_str) - set(in_str.encode('sjis','ignore').decode('sjis'))) != set([])

repos = []
with open("descriptionsAll.csv") as f:
    reader = csv.reader(f)
    repos = [i for i in reader]

print("All:", len(repos))
repos = [i for i in repos if i!=[]]
print("not[]:", len(repos))
not404 = [i for i in repos if "404" not in i[1]]
print("not 404", len(not404))
notNodesc = [i for i in not404 if i[1]!=""]
print("not nocoment", len(notNodesc))
notChinese = [i for i in notNodesc if not is_zh(i[1])]
print("not Chinese", len(notChinese))
nottoolong = [i for i in notChinese if len(i[1])<1000]
print("not too long", len(nottoolong))
repos = nottoolong

for repo in repos:
    name = repo[0]
    desc = repo[1]
    if " web " in desc:
        print(desc.strip())
