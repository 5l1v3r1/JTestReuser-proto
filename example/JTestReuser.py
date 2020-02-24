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


    def outputAllMethods(self):
        Path(os.getcwd()+"/output/"+self.name).mkdir(exist_ok=True, parents=True)
        with open("output/"+self.name+"/AllMethods.csv", "a") as f:
            writer = csv.writer(f)

            for code in list(self.codes):
                for cls in code.classes:
                    print(cls.name, cls.obj.modifiers)
                    for method in cls.methods:
                        return_type =  method.return_type.name if method.return_type is not None else "void"
                        parameters = [i.type.name for i in method.parameters]
                        print("   ", method.name, method.modifiers, parameters, "->", return_type)
                        isTestCode = "/test/" in str(code.path)
                        isTestMethod = "Test" in [j.name for j in method.annotations]
                        output = [code.package, code.name, cls.name, method.name, "-".join(method.modifiers), "-".join(parameters), return_type, isTestCode, isTestMethod, cls.get_extends_from()]
                        writer.writerow(output)

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
                        continue
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


#for Step10
def createIntialSeats(Projectname):
    Path(os.getcwd()+"/output/"+Projectname).mkdir(exist_ok=True, parents=True)
    title = ["package", "Code", "Class", "Method", "Modifiers", "Parameters", "ReturnType", "isTestCode", "isTestMethod"]
    with open("output/"+Projectname+"/AllMethods.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(title)

    title = ["Fullname", "CalledClass", "CalledMethod", "isSpecific", "ReturnType"]
    with open("output/"+Projectname+"/AllMethodCall.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(title)






#======================================================================== important functions

def getSpecificMembers_from_TestCode(ThisCode, Project):
    print(ThisCode.path)
    if ThisCode.main_class is None or ThisCode.main_class.is_extends or ThisCode.main_class.is_implements:
        print("諦めます")
        return False

    #Step2
    GlobalVariables = ThisCode.getGlobalVariables()
    #NonTestMethods = TestCode.getNonTestMethods()
    #TestMethods = TestCode.getTestMethods()


    for ThisMethod in ThisCode.main_class.methods:
        print("ThisMethod:",ThisMethod.name)

        LocalValiables = getDeclarations(ThisMethod)
        Valiables = GlobalVariables + LocalValiables
        Stream = getStream(ThisMethod)

        CallListA = getCallListA(Valiables, Stream, ThisCode, Project)
        CallListB = getCallListB(CallListA, ThisCode, Project)
        print(tabulate(CallListB, ["Tag","Class","Method","isSpecific","ReturnType"]))

        outputCallListB(CallListB, ThisMethod, ThisCode, Project)




def outputCallListB(CallListB, TestMethod, TestCode, Project):
    Fullname = TestCode.package+"."+TestCode.name+"."+TestMethod.name

    outputlist = [[Fullname]+i[1:] for i in CallListB]

    Path(os.getcwd()+"/output/"+Project.name).mkdir(exist_ok=True, parents=True)
    with open("output/"+Project.name+"/AllMethodCall.csv", "a") as f:
        writer = csv.writer(f)
        writer.writerows(outputlist)



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





#============================================================ main
if __name__ == '__main__':
    #path = "downloads/github.com/rhuss/jolokia"
    #path = "sample/SimianArmy"
    #path = "sample/jolokia"
    path = "netty"
    #path = "couchdb-lucene"
    ThisProject = Project(path)
    createIntialSeats(ThisProject.name)
    #PackageDic = ThisProject.getPackageDic()
    #ThisProject.showAllMethods()
    ThisProject.outputAllMethods()
    #sys.exit()
    #ThisProject.showAllPath()
    for TestCode in ThisProject.codes:
        SpecificMembers = getSpecificMembers_from_TestCode(TestCode, ThisProject)
