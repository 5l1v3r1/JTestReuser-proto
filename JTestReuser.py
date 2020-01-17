import javalang, sys
from pathlib import Path
from tqdm import tqdm

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
            splited = splitImport(imp)
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
                if imp.path.split(".")[-1].isupper():
                    continue
                splited = splitImport(imp)
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
            top_n = [".".join(i.split(".")[:n]) for i in all_package]
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

        try:
            self.code = path.open()
            self.strcode = " ".join([i for i in self.code])
            self.tree = javalang.parse.parse(self.strcode)
            self.code.close()
        except:
            print("内部エラーのあるコードファイルです:", self.path)
        else:
            self.package = self.tree.package.name
            self.imports = self.tree.imports
            for cls in self.tree.types:
                if str(type(cls))=="<class 'javalang.tree.ClassDeclaration'>":
                    thiscls = Class(cls)
                    self.classes.append(thiscls)
                    if thiscls.name == self.name:
                        self.main_class = thiscls

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

        else:
            self.TypeObject = Object.type
            #self.type = Object.type.name
            self.type = returnTypeName(Object.type)
            self.variable = Object.declarators[0].name


#======================================================================== tiny functions

#for Step2
def splitImport(import_sentence):
    splited = import_sentence.path.split(".")
    _package = ""
    _class = ""
    _method = ""
    if splited[-1][0].islower() and splited[-2][0].isupper():
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
        #変数宣言
        declaration_statements = ["<class 'javalang.tree.LocalVariableDeclaration'>","<class 'javalang.tree.VariableDeclaration'>"]
        if elmtype in declaration_statements:
            ThisDeclaration = Declaration(element)
            Declarations.append(ThisDeclaration)
        #キャッチ文での例外型宣言
        if elmtype == "<class 'javalang.tree.CatchClauseParameter'>":
            ThisDeclaration = Declaration(element)
            Declarations.append(ThisDeclaration)
    return Declarations

def getStaticType(_method, TestCode, Project):
    StaticImports = Project.getStaticImportedMethods(TestCode)
    for call in StaticImports:
        if call[2] == _method:
            return call[1]
    return "(Non_specific)"

#for Step3
def isSpecific(_type, _method, TestCode, Project):
    SpecificImportedClasses = Project.getImportedClasses(TestCode)
    SpecificStaticImportedMethods = Project.getStaticImportedMethods(TestCode)
    if _type == "(Private)":
        return True
    if _type == "(Non_specific)":
        return False
    if _type == "(Object)":
        return False
    if _type in [i[1] for i in SpecificImportedClasses]:
        return True
    for s in SpecificStaticImportedMethods:
        if _type == s[1] and _method == s[2]:
            return True
    return False

def getReturnType(_type, _method, TestCode, Project):
    NonTestMethods = TestCode.getNonTestMethods()
    SpecificImportedClasses = Project.getImportedClasses(TestCode)
    SpecificStaticImportedMethods = Project.getStaticImportedMethods(TestCode)
    Specifics = SpecificImportedClasses + SpecificStaticImportedMethods
    PackageDic = Project.getPackageDic()

    if _type == "(Private)":
        for nt in NonTestMethods:
            if _method == nt.name:
                return returnTypeName(nt.return_type)
    else:
        for s in Specifics:
            if s[1] == _type:
                for i in PackageDic[s[0]]:
                    if i.name == s[1]:
                        for m in i.main_class.methods:
                            if m.name == _method:
                                return returnTypeName(m.return_type)
    return "(Unknown)"





def isTestCode(Code):
    return ("/test/" in str(Code.path)) and ("@Test" in Code.strcode)

def searchType_from_DeclarationList(variable, DeclarationList):
    for dec in DeclarationList:
        if dec.variable == variable:
            return dec.type
    return False

def getMethodSigneture(_type, _call, ThisProject):
    #print(_type,"のメソッド",_call,"についてシグネチャを取得します")
    _class = ThisProject.getTheClass(_type)

    if _class is None:
        #print(_type,"は見つかりません")
        return False

    for method in _class.methods:
        if method.name == _call:
            #print(_type,"のメソッド",_call,"が見つかりました")
            return method

    #print(_type,"のメソッド",_call,"は見つかりません")

    if _class.is_extends:
        #print(_type,"の継承元である",_class.get_extends_from(),"を調査します")
        return getMethodSigneture(_class.get_extends_from(), _call, ThisProject)
    elif _class.is_implements:
        for itf in _class.get_implements_from():
            #print(_type,"のインターフェースである",itf,"を調査します")
            if getMethodSigneture(itf, _call, ThisProject):
                return getMethodSigneture(itf, _call, ThisProject)
        else:
            return False
    return False

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
    print("インポート",ImportedClassNames)
    ImportedStaticMethods = Project.getStaticImportedMethods(TestCode)
    print("staticインポート",ImportedStaticMethods)

    for TestMethod in TestMethods:
        print("------------------------------TestMethod:",TestMethod.name)
        #Step3
        LocalValiables = getDeclarations(TestMethod)
        Valiables = GlobalVariables + LocalValiables
        Stream = getStream(TestMethod)
        #Step4
        CallListA = getCallListA(Valiables, Stream, TestCode, Project)
        #Step5
        CallListB = getCallListB(CallListA, TestCode, Project)
        #Step6
        CallListC = getCallListC(CallListB)

        for c in CallListC:
            print(c)


def getCallListA(Valiables, Stream, TestCode, Project):
    CallListA = []
    NonTestMethods = TestCode.getNonTestMethods()
    NonTestsName = [i.name for i in NonTestMethods]

    for call in Stream:
        if str(type(call)) == "<class 'javalang.tree.MethodInvocation'>":

            if call.member in Object_methods: #Objectクラスのメソッド
                _type = "(Object)"
            elif call.qualifier is None: #メソッド結果のメソッド
                _type = "(Before)"
            elif call.qualifier == "":
                if call.member in NonTestsName: #プライベートメソッド
                    _type = "(Private)"
                else: #staticなメソッド
                    #_type = ThisProject.getStaticImportedClass(call.member, TestCode.imports)
                    _type = getStaticType(call.member, TestCode, Project)
            elif not call.qualifier[0].isupper():
                #変数オブジェクトの持つメソッド
                _type = searchType_from_DeclarationList(call.qualifier, Valiables)
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
    NoneTestMethods = TestCode.getNonTestMethods()
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

def getCallListC(CallListB):
    return CallListB





#============================================================ main

#path = "downloads/github.com/rhuss/jolokia"
#path = "sample/SimianArmy"
#path = "sample/jolokia"
path = "sample/jadx"
ThisProject = Project(path)
#PackageDic = ThisProject.getPackageDic()
#ThisProject.showAllMethods()
#ThisProject.showAllPath()
for TestCode in [i for i in ThisProject.codes if isTestCode(i)]:
    SpecificMembers = getSpecificMembers_from_TestCode(TestCode, ThisProject)
