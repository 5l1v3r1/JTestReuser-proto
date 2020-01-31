from github import Github
from tqdm import tqdm

token =  "d332841bfdbbee0253e3e28318773fb9520168a4"

namelist = []
with open("newnamelist.txt") as f:
    ftxt = f.read()
    namelist = ftxt.split("\n")

print("repo,description")

g = Github(token)
for name in tqdm(namelist):
    try:
        repo = g.get_repo(name)
        desc = repo.description
    except:
        desc = "!!!!! 404 not found !!!!!"
    desc = desc.replace(",", " -") if desc is not None else ""
    print(name+","+desc)
