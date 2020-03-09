import sys, os, csv, itertools
from pathlib import Path
from tqdm import tqdm
from statistics import stdev, variance, median

def pprint(title, _list):
    print(title, "　平均",sum(_list)/len(_list), "中央値",median(_list), "標準偏差",stdev(_list))

def uniquelist(_list):
    output = ["@".join(i) for i in _list]
    output = list(set(output))
    output = [i.split("@") for i in output]
    return output

domains = "Web,Network,Development,Database,Data,Distribution"
domains = "Network"
domains = domains.split(",")

ready = True
projects = {}
for domain in domains:
    file = "extracted/"+domain+".txt"
    with open(file) as f:
        namelist = f.read()
        namelist = namelist.split("\n")
        print(domain)
        for name in tqdm(namelist[:3]):
            #print(name)
            #print(Path("output/"+name).exists())
            try:
                if name not in projects:
                    with open("output/"+name+"/AllMethods.csv") as am:
                        reader = csv.reader(am)
                        next(reader)
                        AllMethods = list(reader)
                    with open("output/"+name+"/AllMethodCall.csv") as amc:
                        reader = csv.reader(amc)
                        next(reader)
                        AllMethodCall = list(reader)
                    with open("output/"+name+"/FilePath.txt") as fp:
                        FilePath = fp.read()
                        FilePath = FilePath.split("\n")
                    projects[name] = [AllMethods, AllMethodCall, FilePath]
            except:
                print(name, "が存在しません")
                ready = False

if ready:
    print("分析開始")
    print("プロジェクト総数", len(projects))

    n_methods = 0
    n_tmethods = 0
    n_pmethods = 0
    n_thmethods = 0
    n_codes = 0
    n_tcodes = 0
    nTestCodesList = []

    nTestMethodCall = []
    nTestScenarioCall = []
    n_notspecificCall = []
    n_productCall = []
    n_testhelperCall = []

    n_IndirectProductCall = []
    n_IndirectTestHelperCall = []
    n_IndirectNotSpecificCall = []



    for p in tqdm(projects):
        AllMethods = projects[p][0]
        Name2Method = {}
        for method in AllMethods:
            fullname = method[0]+"."+method[2]+"."+method[3]
            print(fullname)
            Name2Method[fullname] = method
        sys.exit()

        Code2Method = {}
        for method in AllMethods:
            codename = method[0]+"."+method[1]
            if codename not in Code2Method:
                Code2Method[codename] = [method]
            else:
                Code2Method[codename].append(method)

        TC = [i.split("/")[-1][:-5] for i in projects[p][2] if "/test/" in i]
        PC = [i.split("/")[-1][:-5] for i in projects[p][2] if "/test/" not in i]


        n_methods += len(AllMethods)
        TestMethods = [i for i in AllMethods if i[8]=="True"]
        n_tmethods += len(TestMethods)
        TestHelperMethods = [i for i in AllMethods if i[7]=="True" and i[8]=="False"]
        n_thmethods += len(TestHelperMethods)
        ProductMethods = [i for i in AllMethods if i[7]=="False"]
        n_pmethods += len(ProductMethods)
        n_codes += len(set([i[0]+i[1] for i in AllMethods]))
        n_tcodes += len(set([i[0]+i[1] for i in AllMethods if i[8]=="True"]))

        nTMperTC = [len([j for j in Code2Method[i] if j[8]=="True"]) for i in Code2Method]
        nTMperTC = [i for i in nTMperTC if i!=0]
        nTestCodesList.extend(nTMperTC)


        AllMethodCall = projects[p][1]
        Method2Call = {}
        for method in AllMethodCall:
            if method[0] not in Method2Call:
                Method2Call[method[0]] = [method]
            else:
                Method2Call[method[0]].append(method)
        #for i in Method2Call: print(i)
        #sys.exit()

        for tm in TestMethods:
            codename = tm[0]+"."+tm[1]
            fullname = tm[0]+"."+tm[2]+"."+tm[3]
            try:
                ThisCall = Method2Call[fullname]
            except:
                ThisCall = []
            ThisCall = uniquelist(ThisCall)
            nTestMethodCall.append(len(ThisCall))


            MethodsInSameCode = Code2Method[codename]
            BeforeOrAfter = [i for i in MethodsInSameCode if "Before" in i[-1] or "After" in i[-1]]

            additional = []
            for boa in BeforeOrAfter:
                boa_fullname = boa[0]+"."+boa[2]+"."+boa[3]
                try:
                    boa_calling = Method2Call[boa_fullname]
                except:
                    boa_calling = []
                additional.extend(boa_calling)

            ThisScenarioCall = ThisCall + additional
            ThisScenarioCall = uniquelist(ThisScenarioCall)
            nTestScenarioCall.append(len(ThisScenarioCall))


            specificCall = [i for i in ThisScenarioCall if i[3]=="True"]
            not_specificCall = [i for i in ThisScenarioCall if i[3]=="False"]
            n_notspecificCall.append(len(not_specificCall))

            n_p = [i for i in specificCall if i[1] in PC]
            n_t = [i for i in specificCall if i[1] in TC or i[1]=="(Private)"]
            n_productCall.append(len(n_p))
            n_testhelperCall.append(len(n_t))


            def getFullname(thmethod):
                fullname = False
                if thmethod[1]=="(Private)":
                    _class = ".".join(thmethod[0].split(".")[:-1])
                    matching = [i for i in Code2Method[_class] if i[3]==thmethod[2]]
                    try:
                        fullname = _class+"."+thmethod[2]
                    except:
                        return False
                else:
                    _class = thmethod[1]
                    _method = thmethod[2]
                    _class_candidates = [i for i in Code2Method if _class in i]
                    for _class_candidate in _class_candidates:
                        matching = [i for i in Code2Method[_class_candidate] if i[3]==_method]
                        try:
                            fullname = _class_candidate+"."+_method
                        except:
                            return False
                return fullname

            TestHelperMethodCalledByThisTestMethod = []
            ProductMethodCalledByThisTestMethod = [getFullname(i) for i in n_p if getFullname(i)]
            n_indirectory_nonspecific_call = len(not_specificCall)

            TestHelperQueue = n_t

            while TestHelperQueue:
                CalledTestHelperMethod = TestHelperQueue.pop()

                fullname = getFullname(CalledTestHelperMethod)

                if fullname in TestHelperMethodCalledByThisTestMethod:
                    continue
                else:
                    TestHelperMethodCalledByThisTestMethod.append(fullname)

                if CalledTestHelperMethod[2] == "(constructor)":
                    continue
                if fullname == False:
                    continue
                if fullname not in Method2Call:
                    continue

                #print(fullname, fullname in Method2Call)
                Called = Method2Call[fullname]

                nonspecific = [i for i in Called if i[3]=="False"]
                n_indirectory_nonspecific_call += len(nonspecific)

                specificCall = [i for i in Called if i[3]=="True"]
                n_p = [i for i in specificCall if "/"+i[1] in PC]
                n_t = [i for i in specificCall if "/"+i[1] in TC or i[1]=="(Private)"]

                ProductMethodCalledByThisTestMethod.extend([getFullname(i) for i in n_p if getFullname(i)])
                TestHelperQueue.extend(n_t)

            TestHelperMethodCalledByThisTestMethod
            ProductMethodCalledByThisTestMethod = list(set(ProductMethodCalledByThisTestMethod))

            n_IndirectProductCall.append(len(ProductMethodCalledByThisTestMethod))
            n_IndirectTestHelperCall.append(len(TestHelperMethodCalledByThisTestMethod))
            n_IndirectNotSpecificCall.append(n_indirectory_nonspecific_call)

            print(len(ProductMethodCalledByThisTestMethod), len(TestHelperMethodCalledByThisTestMethod))

            for pmethod in ProductMethodCalledByThisTestMethod:
                print(pmethod)
                try:
                    print(Name2Method[pmethod][5:7])
                except:
                    print("Not Found")

            #sys.exit()









    print("合計メソッド数", n_methods)
    print("合計テストメソッド数", n_tmethods)
    print("合計プロダクトメソッド数", n_pmethods)
    print("合計テスト補助メソッド数", n_thmethods)
    print("合計コード数", n_codes)
    print("合計テストコード数", n_tcodes)
    print("プロジェクト平均テストメソッド数", n_tmethods/len(projects))
    print("コードあたりテストメソッド数平均値", n_tmethods/n_tcodes)
    print("コードあたりテストメソッド数中央値", median(nTestCodesList))

    for n in range(31):
        print(n, nTestCodesList.count(n))
    print("31以上", len([i for i in nTestCodesList if i>30]))

    pprint("テストメソッドが呼び出すメソッド数（重複なし）", nTestMethodCall)
    pprint("テストシナリオが呼び出すメソッド数", nTestScenarioCall)
    pprint("テストシナリオが直接呼び出すプロダクトメソッド数", n_productCall)
    pprint("テストシナリオが直接呼び出すテスト補助メソッド数", n_testhelperCall)
    pprint("テストシナリオが直接呼び出す外部メソッド数", n_notspecificCall)

    pprint("テストシナリオが結果的に呼び出すプロダクトメソッド数", n_IndirectProductCall)
    pprint("テストシナリオが結果的に呼び出すテスト補助メソッド数", n_IndirectTestHelperCall)
    pprint("テストシナリオが結果的に呼び出すのべ外部メソッド数", n_IndirectNotSpecificCall)
