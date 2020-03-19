import sys, os, csv, itertools
from pathlib import Path
from tqdm import tqdm
from statistics import stdev, variance, median
import pandas as pd
import numpy as np
from tabulate import tabulate


#ac
#c_title = ["package", "Code", "Class", "Modifiers", "extendFrom", "n_method", "n_subclass"]

#am
#["package", "Code", "Class", "Method", "Modifiers", "Parameters", "ReturnType", "Annotations"]

#fp
#["filepath", "package.file"]

#cl
 #["calledBy", "tag","package", "class", "method", "isSpecific", "returnType", "fullname"]


#辞書整理
#Name2Method    メソッド名フルネーム -> メソッド情報
#Name2Class    クラス名フルネーム -> クラス情報
#Class2Method    クラス名フルネーム -> クラス中のメソッド情報のリスト
#Code2Method    コード名フルネーム -> メソッド情報のリスト
#Name2Code    コード名フルネーム -> コードパス



def pprint(title, _list):
    print(title, "　平均",sum(_list)/len(_list), "中央値",median(_list), "標準偏差",stdev(_list))

def uniquelist(_list):
    output = ["@".join(i) for i in _list]
    output = list(set(output))
    output = [i.split("@") for i in output]
    return output

def getFullname(method):
    return method[0]+"."+method[2] +"."+method[3]

def isTestCode(code):
    if "/test/" in code[0]:
        return True
    else:
        return False


domains = "Web,Network,Development,Database,Data,Distribution"
#domains = "Network"
domains = "Data"
domains = domains.split(",")

ready = True
projects = {}
e_table = [["name","dir", "ac", "am", "fp", "cl"]]
for domain in domains:
    file = "extracted/"+domain+".txt"
    with open(file) as f:
        namelist = f.read()
        namelist = namelist.split("\n")
        print(domain)
        for name in namelist[:2]:
            fullname = name
            #name = name.split("/")[-1]
            e_dir = Path("output/"+name).exists()
            e_ac = Path("output/"+name+"/AllClasses.csv").exists()
            e_am = Path("output/"+name+"/AllMethods.csv").exists()
            e_fp = Path("output/"+name+"/CodeFilePath.csv").exists()
            e_mc = Path("output/"+name+"/MethodCallList.csv").exists()

            e_list = ["o" if i else "" for i in [e_dir, e_ac, e_am, e_fp, e_mc]]
            e_table.append([fullname]+e_list)
            #print(name)
            #print(Path("output/"+name).exists())
            try:
                if name not in projects:
                    with open("output/"+name+"/AllClasses.csv") as f:
                        ac = csv.reader(f)
                        ac = [i for i in ac]
                    with open("output/"+name+"/AllMethods.csv") as f:
                        am = csv.reader(f)
                        am = [i for i in am]
                    with open("output/"+name+"/CodeFilePath.csv") as f:
                        fp = csv.reader(f)
                        fp = [i for i in fp]
                    with open("output/"+name+"/MethodCallList.csv") as f:
                        mc = csv.reader(f)
                        mc = [i for i in mc]
                    projects[name] = [ac, am, fp, mc]
            except:
                print(name, "が存在しません")
                ready = False

print(tabulate(e_table))
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



    for p in projects:
        print(p)
        AllClasses = list(projects[p][0])
        AllMethods = list(projects[p][1])
        FilePath = list(projects[p][2])
        CallList = list(projects[p][3])

        Name2Method = {}
        Code2Method = {}
        Class2Method = {}
        for method in AllMethods:
            fullname = method[0] +"."+ method[2] +"."+ method[3]
            Name2Method[fullname] = method

            codename = method[0] +"."+ method[1]
            if codename not in Code2Method:
                Code2Method[codename] = [method]
            else:
                Code2Method[codename].append(method)

            classname = method[0] +"."+ method[2]
            if classname not in Class2Method:
                Class2Method[classname] = [method]
            else:
                Class2Method[classname].append(method)


        Name2Class = {}
        for _class in AllClasses:
            classname = _class[0] +"."+ _class[2]
            Name2Class[classname] = _class

        AllClassName = [i[2] for i in AllClasses]

        Name2Code = {}
        for code in FilePath:
            Name2Code[code[1]] = code[0]


        Method2Call = {}
        for method in CallList:
            if method[0] not in Method2Call:
                Method2Call[method[0]] = [method]
            else:
                Method2Call[method[0]].append(method)


        #継承されたメソッドを含める
        for c in Name2Class:
            if c in Class2Method:
                #print(i, len(Class2Method[i]))
                n = len(Class2Method[c])
                original = Name2Class[c]
                _class = Name2Class[c]
                extendFrom = _class[4]
                classname = _class[2]

                if extendFrom != "False":
                    extended_methods = []
                    if classname in AllClassName:
                        extendFrom_fullname = _class[0]+"."+extendFrom
                        if extendFrom_fullname not in Class2Method:
                            extendFrom_fullname = [j for j in Name2Class if j.split(".")[-1]==extendFrom]
                            #print(len(extendFrom_fullname))
                            if len(extendFrom_fullname) == 1:
                                extendFrom_fullname = extendFrom_fullname[0]
                            else:
                                continue
                        if extendFrom_fullname in Class2Method:
                            extended_methods = Class2Method[extendFrom_fullname]
                            if c in Class2Method:
                                Class2Method[c].extend(extended_methods)
                    #print(c, extendFrom_fullname, len(extended_methods))
                    #print(n, "->", len(Class2Method[c]))

                    #overrideなメソッド
                    Overrides = [i for i in Class2Method[c] if "Override" in i[7].split("-")]
                    NotOverrides = [i for i in Class2Method[c] if "Override" not in i[7].split("-")]
                    #print(len(Overrides), len(NotOverrides))
                    #print([i[3] for i in NotOverrides])

                    for o in Overrides:
                        name = o[3]
                        #print(name)
                        NotOverrides = [z for z in NotOverrides if z[3] != name]
                    Class2Method[c] = Overrides + NotOverrides

                    #print("->", len(Class2Method[c]))
                    for m in Class2Method[c]:
                        #print(c+"."+m[3])
                        Name2Method[c+"."+m[3]] = original[:3]+m[3:]

        for c in Class2Method:
            print(c)
            for m in Class2Method[c]:
                print("    ", m)

        sys.exit()




        TC = TestCode_codename = [i[1] for i in FilePath if "/test/" in i[0]]
        PC = ProductCode_codename = [i[1] for i in FilePath if "/test/" not in i[0]]

        print("コードファイル数:", len(FilePath))
        print("テストコード数:",len(TestCode_codename))
        print("プロダクトコード数:",len(FilePath) - len(TestCode_codename))

        print("合計メソッド数:", len(AllMethods))

        Methods_belong_TestCode = [i for i in AllMethods if i[0]+"."+i[1] in TestCode_codename]
        ProductMethods = [i for i in AllMethods if i[0]+"."+i[1] not in TestCode_codename]
        TestMethods = [i for i in Methods_belong_TestCode if "Test" in i[7].split("-")]
        TestHelperMethods = [i for i in Methods_belong_TestCode if "Test" not in i[7].split("-")]

        print("テストメソッド数:", len(TestMethods))
        print("テスト補助メソッド数:", len(TestHelperMethods))
        print("プロダクトメソッド数:", len(ProductMethods))

        nTMperTC = []
        for TC in TestCode_codename:
            try:
                M = Code2Method[TC]
                TM = [j for j in M if "Test" in j[7].split("-")]
                nTM = len(TM)
                if nTM > 0:
                    nTMperTC.append(nTM)
            except:
                print(TC)
                continue
        nTestCodesList.extend(nTMperTC)





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
            BeforeOrAfter = [i for i in MethodsInSameCode if "Before" in i[7] or "After" in i[-1]]

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


            specificCall = [i for i in ThisScenarioCall if i[5]=="True"]
            not_specificCall = [i for i in ThisScenarioCall if i[5]=="False"]
            n_notspecificCall.append(len(not_specificCall))

            #SpecificMethods = []
            called_ProductMethods = []
            called_TestHelperMethods = []
            for call in specificCall:
                fullname = call[-1]
                try:
                    method = Name2Method[fullname]
                    codename = call[2]+"."+call[3]
                    codepath = Name2Code[codename]
                    if "/test/" in codepath:
                        called_TestHelperMethods.append(method)
                    else:
                        called_ProductMethods.append(method)
                except:
                    print(fullname)
                    continue
            n_productCall.append(len(called_ProductMethods))
            n_testhelperCall.append(len(called_TestHelperMethods))




            #TestHelperMethodCalledByThisTestMethod = []
            name_CPM = [getFullname(i) for i in called_ProductMethods if getFullname(i)]
            name_NSC = list(set([i[-1] for i in not_specificCall]))
            name_CTHM = []

            object_CPM = called_ProductMethods
            object_CTHM = []

            TestHelperQueue = called_TestHelperMethods



            while TestHelperQueue:
                #テスト補助メソッドをキューの先頭から取り出す
                #これはフルメソッドオブジェクト
                CalledTestHelperMethod = TestHelperQueue.pop()
                print(CalledTestHelperMethod)
                fullname = getFullname(CalledTestHelperMethod)
                print(fullname)

                if fullname in name_CTHM:
                    #もうすでに見ている場合、スキップ
                    continue
                else:
                    #初見の場合、登録
                    name_CTHM.append(fullname)
                    object_CTHM.append(CalledTestHelperMethod)



                #(テスト補助メソッドが)コンストラクタの場合
                if CalledTestHelperMethod[2] == CalledTestHelperMethod[3]:
                    print("これはコンストラクタ")
                    if fullname in Name2Method:
                        print("コンストラクタが定義済み", fullname)
                    else:
                        print("デフォルトコンストラクタの呼び出し")
                        continue

                #テスト補助メソッドの中で呼び出されているメソッド
                try:
                    CalledMethods = Method2Call[fullname]
                except:
                    CalledMethods = []

                #考慮すべきこと
                #1. specificなものかどうか
                #2. プロダクトコードかテスト補助コードか
                #3. コンストラクタならばデフォルトコンストラクタか
                #4. 継承されたメソッドか
                #5. 損傷ファイルに含まれるメソッドか

                #そのうちnonspecificなもの
                nonspecific_fullname = [i[-1] for i in CalledMethods if i[5]=="False"]
                print(nonspecific_fullname)
                name_NSC.extend(nonspecific_fullname)
                #specificなもののうち、プロダクトメソッドであるもの
                for s in [i for i in CalledMethods if i[5]=="True"]:
                    fullname = s[-1]
                    print(fullname)
                    codename = s[2]+"."+s[3]
                    try:
                        codepath = Name2Code[codename]
                    except:
                        continue
                    isTest = "/test/" in codepath

                    if isTest:
                        if s[3] == s[4]:
                            if fullname in Name2Method:
                                print("定義済みコンストラクタ")
                            else:
                                print("デフォルトコンストラクタ")
                        else:
                            if fullname in Name2Method:
                                print("未定義")
                            else:
                                print("定義済みメソッド")
                    else:#specificなもののうち、テスト補助メソッドであるもの
                        if s[3] == s[4]:
                            if fullname in Name2Method:
                                print("定義済みコンストラクタ")

                            else:
                                print("デフォルトコンストラクタ")
                        else:
                            if fullname in Name2Method:
                                print("未定義")
                            else:
                                print("定義済みメソッド")




                continue


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


            continue
            TestHelperMethodCalledByThisTestMethod
            ProductMethodCalledByThisTestMethod = list(set(ProductMethodCalledByThisTestMethod))

            n_IndirectProductCall.append(len(ProductMethodCalledByThisTestMethod))
            n_IndirectTestHelperCall.append(len(TestHelperMethodCalledByThisTestMethod))
            n_IndirectNotSpecificCall.append(n_indirectory_nonspecific_call)

            #print(len(ProductMethodCalledByThisTestMethod), len(TestHelperMethodCalledByThisTestMethod))

            for pmethod in ProductMethodCalledByThisTestMethod:
                print(pmethod)
                try:
                    print(Name2Method[pmethod][5:7])
                except:
                    print("Not Found")

            #sys.exit()









    sys.exit()
    print("プロジェクト平均テストメソッド数", n_tmethods/len(projects))
    pprint("コードあたりテストメソッド数中央値", nTestCodesList)

    for n in range(16):
        print(n, nTestCodesList.count(n))
    print("16以上", len([i for i in nTestCodesList if i>15]))

    pprint("テストメソッドが呼び出すメソッド数（重複なし）", nTestMethodCall)
    pprint("テストシナリオが呼び出すメソッド数", nTestScenarioCall)
    pprint("テストシナリオが直接呼び出すプロダクトメソッド数", n_productCall)
    pprint("テストシナリオが直接呼び出すテスト補助メソッド数", n_testhelperCall)
    pprint("テストシナリオが直接呼び出す外部メソッド数", n_notspecificCall)

    pprint("テストシナリオが結果的に呼び出すプロダクトメソッド数", n_IndirectProductCall)
    pprint("テストシナリオが結果的に呼び出すテスト補助メソッド数", n_IndirectTestHelperCall)
    pprint("テストシナリオが結果的に呼び出すのべ外部メソッド数", n_IndirectNotSpecificCall)
