import sys, os, csv, itertools

alldomains = "Web,Network,Development,Programing,Testing,Operation,Database,Data,Document,Distribution,OS,Middleware,Security,Performance,Multimedia,Game,Science,Financial,Geospatial,Android,Utility,No Category"
alldomains = alldomains.split(",")

file = "Javaリポジトリのドメイン分類.csv"
with open(file) as f:
    reader = csv.reader(f)
    next(reader)
    repos = list(reader)

    ones = []
    for domain in alldomains:
        including = [i for i in repos if domain in i[3:6]]
        #print(domain, len(including))
        ones.append([len(including), domain])
    ones.sort(reverse=True)

    twos = []
    for two in itertools.combinations(alldomains, 2):
        including = [i for i in repos if two[0] in i[3:6] and two[1] in i[3:6]]
        #print(two, len(including))
        twos.append([len(including), two])
    print(sorted(twos, reverse=True)[:3])

    print()

    print("domain & repositories")
    for one in ones:
        if one[1]=="No Category":
            nc = one[1]+" & "+str(one[0])
            pass
        print(one[1],"&", one[0], "\\\\")
    print(nc)
