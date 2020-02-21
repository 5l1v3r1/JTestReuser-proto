import sys, os, csv, itertools

alldomains = "Web,Network,Development,Database,Data,Distribution"
alldomains = alldomains.split(",")

file = "summary.csv"
star = {}
with open(file) as f:
    reader = csv.reader(f)
    next(reader)
    repos = list(reader)
    for repo in repos:
        star[repo[1]]=repo[5]



file = "Javaリポジトリのドメイン分類.csv"
with open(file) as f:
    reader = csv.reader(f)
    next(reader)
    repos = list(reader)

    for domain in alldomains:
        print(domain)
        including = [[int(star[i[0]]), i[0]] for i in repos if domain in i[3:6]]
        including.sort(reverse=True)
        top100 = including[:100]
        print(top100[0][0], top100[49][0],top100[-1][0])
        
