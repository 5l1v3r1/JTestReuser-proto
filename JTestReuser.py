import javalang, sys, os, csv
from pathlib import Path
from tqdm import tqdm
from tabulate import tabulate
from operator import itemgetter

Object_methods = {
"clone":"Object",
"equals":"boolean",
"finalize":"void",
"getClass":"Class",
"hashCode":"int",
"notify":"void",
"notifyAll":"void",
"toString":"void",
"wait":"void"
}

#===================================================================== Class

class Project():
    def __init__(self, path):
        self.path = path
        self.name = path.split("/")[-1]
        self.codes = []
        self.domain = None

        javas = list(Path(path).glob("**/*.java"))

        for java in tqdm(javas):
            ThisCode = Code(java)
            self.codes.append(ThisCode)
        self.setDomain()

    def getPackageDic(self):
        PackageDic = {}
        for code in list(self.codes):
            if code.package not in PackageDic:
                PackageDic[code.package] = [code]
            else:
                PackageDic[code.package].append(code)
        return PackageDic

    def showAllMethods(self):
        for code in list(self.codes):
            for cls in code.classes:
                print(cls.name, cls.obj.modifiers)
                for method in cls.methods:
                    return_type =  method.return_type.name if method.return_type is not None else "void"
                    parameters = [i.type.name for i in method.parameters]
                    print("   ", method.name, method.modifiers, parameters, "->", return_type)

    def showAllPath(self):
        for code in self.codes:
            print(code.path)

    def getTheClass(self, class_name):
        for code in self.codes:
            for cls in code.classes:
                if cls.name == class_name:
                    return cls
        return None

    def classifySpecificClass(self, class_name):
        #入力したクラス名をテストコード、プロダクトコード、テストヘルパーコード、Noneに分類する
        for code in self.codes:
            if class_name in [i.name for i in code.classes]:
                if "/test/" in str(code.path):
                    if "@Test" in code.strcode:
                        return "Test"
                    else:
                        return "TestHelper"
                else:
                    return "Product"
        return None

    def getImportedClasses(self, Code):
        #コードのパッケージ名およびインポート文から、同じプロジェクト内から使用可能なクラス群を返す
        ImportedClasses = []
        #同じパッケージ名のクラスを取得
        PackageDic = self.getPackageDic()
        same_packages = PackageDic[Code.package]
        ImportedClasses.extend([[Code.package, i.name, ""] for i in same_packages])

        #インポートした自作クラスを取得
        #(例)
        #import packagehoge.ClassHoge
        #import packagehoge.ClassHoge.SubClassHoge
        #import packagehoge.*
        #import packagehoge.ClassHoge.*
        #import packagehoge.ClassHoge.SubClassHoge.*

        for imp in Code.imports:
            splited = splitImport(imp.path)
            if splited[0] in PackageDic:
                if imp.static == False:
                    if imp.wildcard == True:
                        if splited[1] == "":
                            if splited[0] in PackageDic:
                                same_package = PackageDic[imp.path]
                                for _class in same_package:
                                    splited[1] = _class.name
                                    ImportedClasses.append(splited)
                        else:
                            ImportedClasses.append(splited)

                    else:
                        ImportedClasses.append(splited)

        return ImportedClasses

    def getStaticImportedMethods(self, Code):
        Imported = []
        PackageDic = self.getPackageDic()
        #staticインポートした自作クラスのメソッドを取得
        #(例)
        #import packagehoge.ClassHoge.hogehoge
        #import packagehoge.ClassHoge.SubClassHoge.hogehoge
        #import packagehoge.ClassHoge.*
        #import packagehoge.ClassHoge.SubClassHoge.*

        for imp in Code.imports:
            if imp.static == True:
                if imp.path.split(".")[-1].replace("-","").isupper():
                    continue
                splited = splitImport(imp.path)
                if splited[0] in PackageDic:
                    if imp.wildcard == False:
                        Imported.append(splited)
                    else:
                        print("自作クラスをstatic wildcardでインポートするな")
                        sys.exit()
                        for code in PackageDic[splited[0]]:
                            for _class in code.classes:
                                subclasses = getAllSubClassNames(_class)
                                if _class.name == splited[1]:
                                    print(_class.name, "の全てのメソッド")
                                if splited[1] in subclasses:
                                    print(splited[1],"の全てのメソッド")

        return Imported







    def setDomain(self):
        PackageDic = self.getPackageDic()
        all_package = [i for i in PackageDic]
        domain = ""
        for n in range(1,10):
            top_n = [".".join(i.split(".")[:n]) for i in all_package if i is not None]
            if len(list(set(top_n))) == 1:
                domain = list(set(top_n))[0]
            else:
                break
        self.domain = domain

    def getAllClasses(self):
        AllClasses = []
        for code in self.codes:
            for _class in code.classes:
                AllClasses.append(_class.name)
                for subclass in _class.subclass:
                    AllClasses.append(_class.name+"."+subclass.name)
        return AllClasses

class Code():
    def __init__(self, path):
        self.path = path
        self.package = None
        self.name = path.stem
        self.code = None
        self.strcode = None
        self.tree = None
        self.classes = []
        self.main_class = None
        self.imports = []
        self.imported_specific_classes = []
        self.interface = None

        try:
            self.code = path.open()
            self.strcode = " ".join([i for i in self.code])
            self.tree = javalang.parse.parse(self.strcode)
            self.code.close()
        except:
            print("内部エラーのあるコードファイルです:", self.path)
        else:
            self.package = self.tree.package.name if self.tree.package is not None else "nopackage"
            self.imports = self.tree.imports
            for cls in self.tree.types:
                if str(type(cls))=="<class 'javalang.tree.ClassDeclaration'>":
                    thiscls = Class(cls)
                    self.classes.append(thiscls)
                    if thiscls.name == self.name:
                        self.main_class = thiscls
                if str(type(cls))=="<class 'javalang.tree.InterfaceDeclaration'>":
                    self.interface = cls

    def getGlobalVariables(self):
        GlobalVariables = []
        for elm in self.main_class.obj.body:
            if str(type(elm))=="<class 'javalang.tree.FieldDeclaration'>":
                ThisDeclaration = Declaration(elm)
                GlobalVariables.append(ThisDeclaration)
        return GlobalVariables

    def getNonTestMethods(self):
        return [i for i in self.main_class.methods if "Test" not in [j.name for j in i.annotations]]

    def getTestMethods(self):
        return [i for i in self.main_class.methods if "Test" in [j.name for j in i.annotations]]

    def showImports(self):
        for i in self.tree.imports:
            print(i.path, i.static, i.wildcard)

class Class():
    def __init__(self, cls):
        self.name = cls.name
        self.obj = cls
        self.methods = []
        self.subclass = []
        self.is_extends = False
        self.is_implements = False

        if "extends" in self.obj.attrs:
            if self.obj.extends is not None:
                self.is_extends = True

        if "implements" in self.obj.attrs:
            if self.obj.implements is not None:
                self.is_implements = True

        for method in cls.body:
            if str(type(method))=="<class 'javalang.tree.ClassDeclaration'>":
                subclass = Class(method)
                self.subclass.append(subclass)
            elif str(type(method))=="<class 'javalang.tree.MethodDeclaration'>":
                self.methods.append(method)

    def get_extends_from(self):
        if self.is_extends == False:
            return False
        else:
            return self.obj.extends.name

    def get_implements_from(self):
        if self.is_implements == False:
            return False
        else:
            return [i.name for i in self.obj.implements]

    def getAllSubClassNames(self):
        AllSubClasses = []
        for sub in self.subclass:
            if sub is not None:
                sub_name = sub.name
                AllSubClasses.append(sub_name)
                sub_sub_names = sub.getAllSubClassNames()
                sub_sub_names = [sub_name+"."+i for i in sub_sub_names]
                AllSubClasses.extend(sub_sub_names)
        return AllSubClasses

class Declaration():
    def __init__(self, Object):
        self.Object = Object
        self.type = ""
        self.variable = ""

        if str(type(Object)) == "<class 'javalang.tree.CatchClauseParameter'>":
            #Object.typesには文字列の配列が格納されている
            self.TypeObject = None
            self.type = Object.types[0]
            self.variable = Object.name

        elif str(type(Object)) == "<class 'javalang.tree.FormalParameter'>":
            self.TypeObject = Object.type
            #self.type = Object.type.name
            self.type = returnTypeName(Object.type)
            self.variable = Object.name

        elif Object is None:
            pass

        else:
            self.TypeObject = Object.type
            #self.type = Object.type.name
            self.type = returnTypeName(Object.type)
            self.variable = Object.declarators[0].name


#======================================================================== tiny functions

#general
def returnTypeName(_type):
    if _type is None:
        return "Void"
    if str(type(_type))=="<class 'javalang.tree.ReferenceType'>":
        base = _type.name
        if _type.arguments is not None:
            args = []
            for a in _type.arguments:
                args.append(returnTypeName(a.type))
            base = base+"<"+",".join(args)+">"
        if _type.sub_type is not None:
            sub_type_name = returnTypeName(_type.sub_type)
            base = base+"."+sub_type_name
    else:
        base = _type.name
    return base

def isTestCode(Code):
    return ("/test/" in str(Code.path)) and ("@Test" in Code.strcode)

def organizeList(_list):
    organized = []
    for l in _list:
        if l not in organized:
            organized.append(l)
    organized.sort(key=itemgetter(1))
    return organized
#for Step3
def splitImport(import_sentence):
    splited = import_sentence.split(".")
    _package = ""
    _class = ""
    _method = ""
    _const = ""
    if splited[-2][0].isupper() and splited[-1].replace("_","").isupper():
        _const = splited[-1]
        splited = splited[:-1]
    elif splited[-1][0].islower() and splited[-2][0].isupper():
        _method = splited[-1]
        splited = splited[:-1]
    _package = ".".join([i for i in splited if i[0].islower()])
    _class = ".".join([i for i in splited if i[0].isupper()])
    return [_package, _class, _method]

def getStream(method_object):
    Stream = []
    for methodelm in method_object:
        element = methodelm[1]
        elmtype = str(type(element))
        if elmtype in ["<class 'javalang.tree.ClassCreator'>", "<class 'javalang.tree.MethodInvocation'>"]:
            Stream.append(element)
    return Stream

def getDeclarations(method_object):
    #メソッド自体のパラメータ
    Declarations = []
    for parameter in method_object.parameters:
        ThisDeclaration = Declaration(parameter)
        Declarations.append(ThisDeclaration)
    for methodelm in method_object:
        element = methodelm[1]
        elmtype = str(type(element))
        #print(999, elmtype)
        #変数宣言
        declaration_statements = ["<class 'javalang.tree.LocalVariableDeclaration'>","<class 'javalang.tree.VariableDeclaration'>"]
        if elmtype in declaration_statements:
            ThisDeclaration = Declaration(element)
            Declarations.append(ThisDeclaration)
        #キャッチ文での例外型宣言
        if elmtype == "<class 'javalang.tree.CatchClauseParameter'>":
            ThisDeclaration = Declaration(element)
            Declarations.append(ThisDeclaration)
        if elmtype == "<class 'javalang.tree.FormalParameter'>":
            ThisDeclaration = Declaration(None)
            ThisDeclaration.variable = element.name
            ThisDeclaration.type = returnTypeName(element.type)
            Declarations.append(ThisDeclaration)
    return Declarations

#for Step4
def getDecralatedType(variable, Declarations):
    #print(999, variable, [[i.type, i.variable] for i in Declarations])
    for dec in Declarations:
        if dec.variable == variable:
            return dec.type
    return "(Unknown)"

def getStaticType(_method, TestCode, Project):
    StaticImports = Project.getStaticImportedMethods(TestCode)
    for call in StaticImports:
        if call[2] == _method:
            return call[1]
    return "(Non_specific)"

#for Step5
def isSpecific(_type, _method, TestCode, Project):
    SpecificImportedClasses = Project.getImportedClasses(TestCode)
    SpecificStaticImportedMethods = Project.getStaticImportedMethods(TestCode)
    if _type == "(Private)":
        return True
    if _type == "(Non_specific)":
        return False
    if _type == "(Object)":
        return False
    if _type == "(Unknown)":
        return True
    _type = _type.split(".")[0]
    if _type in [i[1] for i in SpecificImportedClasses]:
        return True
    for s in SpecificStaticImportedMethods:
        if _type == s[1] and _method == s[2]:
            return True
    return False

def getReturnType(_type, _method, TestCode, Project):
    InnerMethods = TestCode.main_class.methods

    if _type == "(Unknown)":
        return "(Unknwon)"

    if _type == "(Private)":
        for nt in InnerMethods:
            if _method == nt.name:
                return returnTypeName(nt.return_type)
    else:
        method = getMethod(_type, _method, TestCode, Project)
        if method:
            return returnTypeName(method.return_type)
    return "(Unknown)"

def getCode(_class, TestCode, Project):
    if _class == "(Private)":
        return TestCode
    SpecificImportedClasses = Project.getImportedClasses(TestCode)
    SpecificStaticImportedMethods = Project.getStaticImportedMethods(TestCode)
    Specifics = SpecificImportedClasses + SpecificStaticImportedMethods
    PackageDic = Project.getPackageDic()
    _class = _class.split(".")[0]
    for sp in Specifics:
        if sp[1] == _class:
            for code in PackageDic[sp[0]]:
                if code.name == _class:
                    return code
    return None

def getMethod(_type, _method, Code, Project):
    SpecificImportedClasses = Project.getImportedClasses(Code)
    SpecificStaticImportedMethods = Project.getStaticImportedMethods(Code)
    Specifics = SpecificImportedClasses + SpecificStaticImportedMethods
    PackageDic = Project.getPackageDic()

    _subtype = None
    fullname = str(_type)
    if "." in _type:
        _type = fullname.split(".")[0]
        _subtype = fullname.split(".")[1]

    for s in Specifics:
        if s[1] == _type:
            for i in PackageDic[s[0]]:
                if i.name == s[1]:
                    if i.main_class is None:
                        #print(888, "メインクラスなし")
                        pass
                        #print(999, i.name, "はメインクラスを持たないようだ")
                        #if i.interface is not None:
                            #print(999, i.name, "はインターフェースを持っている")
                            #for elm in i.interface.body:
                                #if str(type(elm))=="<class 'javalang.tree.MethodDeclaration'>":
                                    #print(999, elm.name)

                    else:
                        _class = i.main_class
                        #print(888, _class.name, _subtype, len(_class.subclass), _class.is_extends)
                        if _subtype is not None:
                            for sc in _class.subclass:
                                #print(888, sc.name)
                                if _subtype == sc.name:
                                    _class = sc
                        for m in _class.methods:
                            #print(888, _class.name, _class.is_extends)
                            if m.name == _method:
                                return m
    return False

#for Step6
def getParameters(_type, _method, TestCode, Project):
    InnerMethods = TestCode.main_class.methods

    def m2p(method):
        return [returnTypeName(i.type) for i in method.parameters]

    if _method == "(constructor)":
        constructor = getMethod(_type, _type, TestCode, Project)
        if constructor:
            return m2p(constructor)
        else:
            return []

    if _type == "(Unknown)":
        return "(Unknwon)"

    if _type == "(Private)":
        for nt in InnerMethods:
            if _method == nt.name:
                return m2p(nt)
    else:
        method = getMethod(_type, _method, TestCode, Project)
        if method:
            return m2p(method)
    return "(Unknown)"

#for Step9
def getSingleSpecifics(_class, Method, Code, Project):
    if Method == "(constructor)":
        Method = _class
    #print(999, Code.name, "のメソッド", Method, "についてspecificな呼び出しを探索します")
    if Code.main_class is None:
        #print(999, "このコードはメインクラスを所持していません")
        return []
    if Code.main_class.is_extends:
        #print(999, "このクラスは継承で作られているので追求を見送ります")
        return []

    methods = Code.main_class.methods
    if "." in _class:
        subclass = _class.split(".")[-1]
        for sub in Code.main_class.subclass:
            if sub.name == subclass:
                methods = sub.methods

    for method in methods:
        if method.name == Method:
            break
    else:
        #print(999, Method, "は見つかりませんでした")
        return []


    Variables = Code.getGlobalVariables() + getDeclarations(method)
    #print(999, len(Code.getGlobalVariables()), len(getDeclarations(method)))
    #print(999, [[i.type, i.variable] for i in Variables])
    Stream = getStream(method)
    CallListA = getCallListA(Variables, Stream, Code, Project)
    CallListB = getCallListB(CallListA, Code, Project)
    CallListC = getCallListC(CallListB, Code, Project)
    CallListD = getCallListD(CallListC, Code, Project)
    CallListD_ex = []
    for call in CallListD:
        if call[1] == "(Private)":
            call[1] = _class
        CallListD_ex.append(call)

    return CallListD_ex

#for Step10
def createIntialSeats(Projectname):
    Path(os.getcwd()+"/output/"+Projectname).mkdir(exist_ok=True, parents=True)
    title1 = ["Test-Project","Test-FUllname","Test-Package","Test-Class", "Test-Method", "Requirement", "Dependent", "Test-Filepath"]
    title2 = ["Test-Fullname","Req/Dep","MI/CC", "Package", "Class", "Method","Parameters","ReturnType", "Group", "Filepath"]
    with open("output/"+Projectname+"/ReqDepSummary.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(title1)
    with open("output/"+Projectname+"/ReqDep.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(title2)


def outputRD(Project, TestCode, TestMethod, Requirement, Dependent):
    outputlist = []

    Fullname = TestCode.package+"."+TestCode.name+"."+TestMethod.name

    def getmethodinfo(x):
        CCMI = x[0]
        package = x[-2].package if x[-2] is not None else None
        _class = x[1]
        _method = x[2]
        _parameter = " ".join(x[-3]) if type(x[-3]) == type([]) else x[-3]
        _return = x[-4]
        _group = x[-1]
        _path = x[-2].path if x[-2] is not None else None
        return [CCMI, package, _class, _method, _parameter, _return, _group, _path]

    for r in Requirement:
        outputlist.append([Fullname, "Requirement"]+getmethodinfo(r))
    for d in Dependent:
        outputlist.append([Fullname, "Dependent"] + getmethodinfo(d))

    #print(999, info, len(Requirement), len(Dependent))

    Path(os.getcwd()+"/output/"+Project.name).mkdir(exist_ok=True, parents=True)
    with open("output/"+Project.name+"/ReqDepSummary.csv", "a") as f:
        writer = csv.writer(f)
        writer.writerow([Project.name, Fullname, TestCode.package, TestCode.name, TestMethod.name,len(Requirement), len(Dependent), str(TestCode.path)])
    with open("output/"+Project.name+"/ReqDep.csv", "a") as f:
        writer = csv.writer(f)
        writer.writerows(outputlist)





#======================================================================== important functions

def getSpecificMembers_from_TestCode(TestCode, Project):
    print(TestCode.path)
    if TestCode.main_class.is_extends or TestCode.main_class.is_implements:
        print("諦めます")
        return False

    #Step2
    GlobalVariables = TestCode.getGlobalVariables()
    NonTestMethods = TestCode.getNonTestMethods()
    TestMethods = TestCode.getTestMethods()
    print(len(GlobalVariables),len(TestMethods), len(NonTestMethods))
    ImportedClassNames = Project.getImportedClasses(TestCode)
    print("インポート")
    print(tabulate(ImportedClassNames, ["package","Class",""]))
    ImportedStaticMethods = Project.getStaticImportedMethods(TestCode)
    print("staticインポート")
    print(tabulate(ImportedStaticMethods, ["package","Class","Method"]))

    NonTestMethodDic = {}
    for NonTestMethod in NonTestMethods:
        LocalValiables = getDeclarations(NonTestMethod)
        Valiables = GlobalVariables + LocalValiables
        Stream = getStream(NonTestMethod)
        CallListA = getCallListA(Valiables, Stream, TestCode, Project)
        CallListB = getCallListB(CallListA, TestCode, Project)
        CallListC = getCallListC(CallListB, TestCode, Project)
        CallListD = getCallListD(CallListC, TestCode, Project)
        NonTestMethodDic[NonTestMethod.name] = CallListD
        print("------------------------------NonTestMethod:",NonTestMethod.name)
        for call in CallListD:
            print(call)

    for TestMethod in TestMethods:
        print("------------------------------TestMethod:",TestMethod.name)
        #Step3
        LocalValiables = getDeclarations(TestMethod)
        Valiables = GlobalVariables + LocalValiables
        Stream = getStream(TestMethod)
        #Step4
        CallListA = getCallListA(Valiables, Stream, TestCode, Project)
        print("CallListA////////////////////////////////////////////////")
        print(tabulate(CallListA, ["Tag","Class","Method"]))
        #Step5
        CallListB = getCallListB(CallListA, TestCode, Project)
        print("CallListB////////////////////////////////////////////////")
        print(tabulate(CallListB, ["Tag","Class","Method","isSpecific","ReturnType"]))
        #Step6
        CallListC = getCallListC(CallListB, TestCode, Project)
        print("CallListC////////////////////////////////////////////////")
        print(tabulate(CallListC, ["Tag","Class","Method","isSpecific","ReturnType","ParameterTypes","Code"]))
        #Step7
        CallListD = getCallListD(CallListC, TestCode, Project)
        print("CallListD////////////////////////////////////////////////")
        print(tabulate(CallListD, ["Tag","Class","Method","isSpecific","ReturnType","ParameterTypes","Code","Group"]))
        #Step8
        CallListE = getCallListE(CallListD, NonTestMethodDic)
        donePrivates = CallListE[1]
        CallListE = CallListE[0]
        print("CallListE////////////////////////////////////////////////")
        print(tabulate(CallListE, ["Tag","Class","Method","isSpecific","ReturnType","ParameterTypes","Code","Group"]))
        #Step9
        CallListF = getCallListF(CallListE, TestCode, Project)
        Requirement = CallListF[0]
        Dependent = donePrivates + CallListF[1]
        print("\nRequirement")
        print(tabulate(Requirement, ["Tag","Class","Method","isSpecific","ReturnType","ParameterTypes","Group"]))
        print("Dependent")
        print(tabulate(Dependent, ["Tag","Class","Method","isSpecific","ReturnType","ParameterTypes","Group"]))

        #Step10
        outputRD(Project, TestCode, TestMethod, Requirement, Dependent)




def getCallListA(Variables, Stream, TestCode, Project):
    CallListA = []
    InnerMethodsName = [i.name for i in TestCode.main_class.methods]

    for call in Stream:
        if str(type(call)) == "<class 'javalang.tree.MethodInvocation'>":

            if call.member in Object_methods: #Objectクラスのメソッド
                _type = "(Object)"
            elif call.qualifier is None: #メソッド結果のメソッド
                _type = "(Before)"
            elif call.qualifier == "":
                if call.member in InnerMethodsName: #プライベートメソッド
                    _type = "(Private)"
                else: #staticなメソッド
                    #_type = ThisProject.getStaticImportedClass(call.member, TestCode.imports)
                    _type = getStaticType(call.member, TestCode, Project)
            elif not call.qualifier[0].isupper():
                #変数オブジェクトの持つメソッド
                _type = getDecralatedType(call.qualifier, Variables)
                if _type == False:
                    _type = "(Unknown)"
            else:
                #明示的なクラスからのメソッド
                _type = call.qualifier
            CallListA.append(["MI", _type, call.member])
        else:
            type_name = returnTypeName(call.type)
            CallListA.append(["CC", returnTypeName(call.type), "(constructor)"])
    return CallListA

def getCallListB(CallListA, TestCode, Project):
    CallListB = []

    beforeType = "Unknown"

    for call in CallListA:
        _tag = call[0]
        _type = call[1]
        _method = call[2]
        _specific = False
        _return = "Unknown"

        if _tag == "MI":
            if _type == "(Before)":
                _type = beforeType
            _specific = isSpecific(_type, _method, TestCode, Project)
            if _specific == True:
                _return = getReturnType(_type, _method, TestCode, Project)
            else:
                _return = "(Non_specific)"

        if _tag == "CC":
            _specific = isSpecific(_type, _method, TestCode, Project)
            _return = _type

        beforeType = _return
        CallListB.append([_tag, _type, _method, _specific, _return])

    return CallListB

def getCallListC(CallListB, TestCode, Project):
    done = []
    CallListC = []
    for call in CallListB:
        if call not in done:
            done.append(call)
            if call[3] == True:
                code = getCode(call[1], TestCode, Project)
                paras = getParameters(call[1], call[2], TestCode, Project)
                CallListC.append(call+[paras, code])
    return CallListC

def getCallListD(CallListC, TestCode, Project):
    def name2code(_class):
        SpecificImportedClasses = Project.getImportedClasses(TestCode)
        SpecificStaticImportedMethods = Project.getStaticImportedMethods(TestCode)
        Specifics = SpecificImportedClasses + SpecificStaticImportedMethods
        PackageDic = Project.getPackageDic()
        _class = _class.split(".")[0]
        for s in Specifics:
            if s[1] == _class:
                for i in PackageDic[s[0]]:
                    if i.name == s[1]:
                        return i
        return False

    def witchGenre(code):
        if "/test/" in str(code.path):
            if "@Test" in code.strcode:
                return "Test"
            else:
                return "TestHelper"
        else:
            return "Product"

    def getGenre(call):
        if call[1] == "(Private)":
            return "Test"
        code = name2code(call[1])
        if code:
            return witchGenre(code)
        return "(Unknown)"


    CallListD = []
    #NonTestMethods = TestCode.getNonTestMethods()
    PackageDic = Project.getPackageDic()
    for call in CallListC:
        _genre = getGenre(call)
        CallListD.append(call+[_genre])
    return CallListD

def getCallListE(CallListD, NonTestMethodDic):
    notPrivates = [i for i in CallListD if not i[1] == "(Private)"]
    Privates = [i for i in CallListD if i[1] == "(Private)"]
    donePrivates = []

    while Privates:
        tmp_privates = list(Privates)
        Privates = []
        for p in tmp_privates:
            donePrivates.append(p)
            x = NonTestMethodDic[p[2]]
            for z in x:
                if z[1]=="(Private)":
                    if z[2] not in [i[2] for i in donePrivates]:
                        Privates.append(z)
                else:
                    if z not in notPrivates:
                        notPrivates.append(z)
    return [notPrivates, organizeList(donePrivates)]

def getCallListF(CallListE, TestCode, Project):
    CallListF = []
    do = []
    done = []

    def getCode(_class):
        SpecificImportedClasses = Project.getImportedClasses(TestCode)
        SpecificStaticImportedMethods = Project.getStaticImportedMethods(TestCode)
        Specifics = SpecificImportedClasses + SpecificStaticImportedMethods
        PackageDic = Project.getPackageDic()
        _class = _class.split(".")[0]
        for sp in Specifics:
            if sp[1] == _class:
                for code in PackageDic[sp[0]]:
                    if code.name == _class:
                        return code

    for call in CallListE:
        if call[-1] == "Test" or call[-1] == "TestHelper":
            do.append(call)
        else:
            CallListF.append(call)


    while(do):
        for call in do:
            next_do = []
            if call[-1] == "Test" or call[-1] == "TestHelper":
                if call not in done:
                    #print(999, "次の呼び出しについて追求",call)
                    Code = getCode(call[1])
                    #print(999, "クラス", call[1], "のコードパスは", Code.path)
                    called = getSingleSpecifics(call[1], call[2], Code, Project)
                    done.append(call)
                    #print(999, "追求終了")
                    #print(call[1]+"."+call[2], "は", len(called), "個のspecificな呼び出しを持つ")
                    if called:
                        for x in called:
                            if x[-1] == "Test" or x[-1] == "TestHelper":
                                next_do.append(x)
                            else:
                                if x not in CallListF:
                                    CallListF.append(x)
            do = next_do

    #while (len([i for i in Calllist if i[-1]=="Test" or i[-1] == "TestHelper"])):

    return [organizeList(CallListF), organizeList(done)]




#============================================================ main
if __name__ == '__main__':
    #path = "downloads/github.com/rhuss/jolokia"
    #path = "sample/SimianArmy"
    #path = "sample/jolokia"
    path = "sample/less4j"
    path = "apache/struts"
    #path = "sample/springside4"
    ThisProject = Project(path)
    #PackageDic = ThisProject.getPackageDic()
    #ThisProject.showAllMethods()
    #ThisProject.showAllPath()
    createIntialSeats(ThisProject.name)
    for TestCode in [i for i in ThisProject.codes if isTestCode(i)]:
        SpecificMembers = getSpecificMembers_from_TestCode(TestCode, ThisProject)
