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
        self.fullname = "/".join(path.split("/")[-2:])
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


    def outputAllMethods(self, pname):
        Path(os.getcwd()+"/output/"+pname).mkdir(exist_ok=True, parents=True)
        with open("output/"+pname+"/AllMethods.csv", "a") as f:
            writer = csv.writer(f)
            title = ["package", "Code", "Class", "Method", "Modifiers", "Parameters", "ReturnType", "isTestCode", "isTestMethod", "extendFrom", "Annotations"]
            writer.writerow(title)

            for code in list(self.codes):
                for cls in code.classes:
                    #print(cls.name, cls.obj.modifiers)
                    for method in cls.methods:
                        return_type =  method.return_type.name if method.return_type is not None else "void"
                        parameters = [i.type.name for i in method.parameters]
                        #print("   ", method.name, method.modifiers, parameters, "->", return_type)
                        isTestCode = "/test/" in str(code.path)
                        isTestMethod = "Test" in [j.name for j in method.annotations]
                        annotstions = "-".join([i.name for i in method.annotations])
                        output = [code.package, code.name, cls.name, method.name, "-".join(method.modifiers), "-".join(parameters), return_type, isTestCode, isTestMethod, cls.get_extends_from(), annotstions]
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
                    #これは定数のインポートなので無視
                    continue
                splited = splitImport(imp.path)
                if splited[0] in PackageDic:
                    if imp.wildcard == False:
                        Imported.append(splited)
                    else:
                        splited[2] == "(all)"
                        Imported.append(splited)
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
        self.package = "nonpackage"
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
        self.constructors = []
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
            #print(str(type(method)))
            if str(type(method))=="<class 'javalang.tree.ClassDeclaration'>":
                subclass = Class(method)
                subclass.name = self.name+"."+subclass.name
                self.subclass.append(subclass)

            elif str(type(method))=="<class 'javalang.tree.MethodDeclaration'>":
                self.methods.append(method)
            elif str(type(method))=="<class 'javalang.tree.ConstructorDeclaration'>":
                self.constructors.append(method)

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

#for Step3
def splitImport(import_sentence):
    splited = import_sentence.split(".")
    _package = ""
    _class = ""
    _method = ""
    _const = ""
    try:
        if splited[-2][0].isupper() and splited[-1].replace("_","").isupper():
            _const = splited[-1]
            splited = splited[:-1]
        elif splited[-1][0].islower() and splited[-2][0].isupper():
            _method = splited[-1]
            splited = splited[:-1]
        _package = ".".join([i for i in splited if i[0].islower()])
        _class = ".".join([i for i in splited if i[0].isupper()])
    except:
        pass
    return [_package, _class, _method]

def getStream(method_object):
    Stream = []

    count = 0
    for methodelm in method_object:
        count+=1
        if count>500:
            break
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


    count=0
    for methodelm in method_object:
        count+=1
        if count>500:
            break
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

        #tryの中での宣言
        if elmtype == "<class 'javalang.tree.TryResource'>":
            ThisDeclaration = Declaration(None)
            ThisDeclaration.variable = element.name
            ThisDeclaration.type = returnTypeName(element.type)
            Declarations.append(ThisDeclaration)
    return Declarations








#======================================================================== important functions


def getAllProductMethods(P):
    ProductCodes = [i for i in P.codes if "/test/" not in str(i.path)]
    #ProductCodes = P.codes
    for _code in ProductCodes:
        #print(_code.path)
        SpecificImportedClasses = P.getImportedClasses(_code)
        SpecificStaticImportedMethods = P.getStaticImportedMethods(_code)
        Specifics = SpecificImportedClasses + SpecificStaticImportedMethods
        #print(tabulate(Specifics))

        ClassQueue = list(_code.classes)
        while ClassQueue:
            _class = ClassQueue.pop()
            #print("クラス:",_class.name)
            ClassName = _code.package + "." + _class.name
            #print("クラス・フルネーム:", _code.package + "." + _class.name)
            ClassName2Class[ClassName] = _class
            ClassName2Code[ClassName] = _code

            #サブクラスがあればキューに追加
            if _class.subclass:
                ClassQueue.extend(_class.subclass)

            #継承元を取得
            ClassName2ExtendFrom[ClassName] = None
            if _class.is_extends:
                extendFrom = _class.get_extends_from()
                #print("継承元:",extendFrom)
                extendFromList = [i[0]+"."+i[1] for i in Specifics if i[1]==extendFrom]
                if len(set(extendFromList)) == 1:
                    extendFrom_fullname = extendFromList[0]
                    #print("継承元:",extendFrom_fullname)
                    ClassName2ExtendFrom[ClassName] = extendFrom_fullname
                else:
                    ClassName2ExtendFrom[ClassName] = "Unknown"

            #メソッドを取得
            ClassName2Methods[ClassName] = _class.methods
            ClassName2Constructors[ClassName] = _class.constructors


    #継承メソッドの統合
    changed = 2
    while changed:
        #print(changed)
        changed-=1
        for ClassName in ClassName2Class:
            #print(ClassName)
            Methods = ClassName2Methods[ClassName]
            #old = len(Methods)
            #print("直接のメソッド数:", len(Methods))
            ExtendFrom = ClassName2ExtendFrom[ClassName]
            if ExtendFrom is not None and ExtendFrom != "Unknown" and ExtendFrom in ClassName2Methods:
                ExtendedMethods = ClassName2Methods[ExtendFrom]
                old = len(ExtendedMethods)
                #print("継承元", ExtendFrom)
                #print("継承されたメソッド数", len(ExtendedMethods))
                #print("継承:", ExtendFrom, "->", ClassName)

                for _method in Methods:
                    annotations = [i.name for i in _method.annotations]
                    #print(_method.name, annotations)
                    parameters = [i.type.name for i in _method.parameters]
                    if "Override" in annotations:
                        ExtendedMethods = [i for i in ExtendedMethods if _method.name != i.name or [j.type.name for j in i.parameters] != parameters]
                #changed += (old - len(ExtendedMethods))

                integrated = Methods + ExtendedMethods
                ClassName2Methods[ClassName] = integrated

    return [i for i in ClassName2Methods]

def getAllTestHelperMethods(P):
    TestHelperClasses = []
    TestCodes = [i for i in P.codes if "/test/" in str(i.path)]
    for _code in TestCodes:
        SpecificImportedClasses = P.getImportedClasses(_code)
        SpecificStaticImportedMethods = P.getStaticImportedMethods(_code)
        Specifics = SpecificImportedClasses + SpecificStaticImportedMethods

        ClassQueue = list(_code.classes)
        while ClassQueue:
            _class = ClassQueue.pop()
            ClassName = _code.package + "." + _class.name
            TestHelperClasses.append(ClassName)
            ClassName2Class[ClassName] = _class
            ClassName2Code[ClassName] = _code

            #サブクラスがあればキューに追加
            if _class.subclass:
                ClassQueue.extend(_class.subclass)

            #継承元を取得
            ClassName2ExtendFrom[ClassName] = None
            if _class.is_extends:
                extendFrom = _class.get_extends_from()
                extendFromList = [i[0]+"."+i[1] for i in Specifics if i[1]==extendFrom]
                if len(set(extendFromList)) == 1:
                    extendFrom_fullname = extendFromList[0]
                    ClassName2ExtendFrom[ClassName] = extendFrom_fullname
                else:
                    ClassName2ExtendFrom[ClassName] = "Unknown"

            #メソッドを取得
            ClassName2Methods[ClassName] = _class.methods
            ClassName2Constructors[ClassName] = _class.constructors


    #継承メソッドの統合
    changed = 2
    while changed:
        changed-=1
        for ClassName in ClassName2Class:
            Methods = ClassName2Methods[ClassName]
            ExtendFrom = ClassName2ExtendFrom[ClassName]
            if ExtendFrom is not None and ExtendFrom != "Unknown":
                ExtendedMethods = ClassName2Methods[ExtendFrom]
                old = len(ExtendedMethods)

                for _method in Methods:
                    annotations = [i.name for i in _method.annotations]
                    parameters = [i.type.name for i in _method.parameters]
                    if "Override" in annotations:
                        ExtendedMethods = [i for i in ExtendedMethods if _method.name != i.name or [j.type.name for j in i.parameters] != parameters]

                integrated = Methods + ExtendedMethods
                ClassName2Methods[ClassName] = integrated

    return TestHelperClasses

def getCalledbyTestMethod(P):
    CallList = {}
    TestCodes = [i for i in P.codes if "/test/" in str(i.path)]
    for _code in TestCodes:
        print(_code.path)
        SpecificImportedClasses = P.getImportedClasses(_code)
        SpecificStaticImportedMethods = P.getStaticImportedMethods(_code)
        Specifics = SpecificImportedClasses + SpecificStaticImportedMethods


        ClassQueue = list(_code.classes)
        while ClassQueue:
            _class = ClassQueue.pop()
            ClassName = _code.package + "." + _class.name
            print(ClassName)

            #サブクラスがあればキューに追加
            if _class.subclass:
                ClassQueue.extend(_class.subclass)

            #継承クラスであればスキップ
            if _class.is_extends:
                continue

            GlobalVariables = []
            for elm in _class.obj.body:
                if str(type(elm))=="<class 'javalang.tree.FieldDeclaration'>":
                    ThisDeclaration = Declaration(elm)
                    GlobalVariables.append(ThisDeclaration)
            print("グローバル変数:", len(GlobalVariables))

            #メソッドを取得
            for _method in _class.methods:
                try:
                    s = str(_method.body)
                except:
                    continue
                _type = "Helper"
                if "Test" in [i.name for i in _method.annotations]:
                    _type = "Test"
                print("   ", _method.name, "(",_type,")")
                MethodName = ClassName + "." + _method.name

                LocalValiables = getDeclarations(_method)
                print("        ローカル変数:",len(LocalValiables))
                Valiables = GlobalVariables + LocalValiables
                Stream = getStream(_method)
                print("        呼び出し回数:", len(Stream))
                CallListA = getCallListAA(Valiables, Stream, Specifics, ClassName)
                CallListB = getCallListBB(CallListA, Specifics)
                print(tabulate(CallListB))
                CallList[MethodName] = [[MethodName, _type] + i for i in CallListB]
    return CallList

def getCallListAA(Variables, Stream, Specifics, ClassName):
    #print(ClassName)
    CallListA = []
    InnerMethodsName = [i.name for i in ClassName2Methods[ClassName]]
    #print(tabulate(Specifics))

    def getClassName(_type):
        for s in Specifics:
            if s[1] == _type:
                return s[0]+"."+s[1]
        return False

    def getDecralatedType(variable, Declarations):
        for dec in Declarations:
            if dec.variable == variable:
                return dec.type
        return False

    def getArguments(arguments):
        result = []
        for arg in arguments:
            if str(type(arg)) == "<class 'javalang.tree.ClassCreator'>":
                result.append(arg.type.name)
            elif str(type(arg)) == "<class 'javalang.tree.Literal'>":
                result.append(arg.value)
            elif str(type(arg)) == "<class 'javalang.tree.MemberReference'>":
                result.append(arg.member)
            else:
                #<class 'javalang.tree.MethodInvocation'>
                #<class 'javalang.tree.LambdaExpression'>
                #<class 'javalang.tree.BinaryOperation'>
                result.append("UNKNOWN")
        return result

    for call in Stream:
        arguments = []
        arguments = getArguments(call.arguments)
        classname = ""
        if str(type(call)) == "<class 'javalang.tree.MethodInvocation'>":
            #arguments = getArguments(call.arguments)

            if call.member in Object_methods: #Objectクラスのメソッド
                _type = "(Object)"
            elif call.qualifier is None: #メソッド結果のメソッド
                _type = "(Before)"
            elif call.qualifier == "":
                if call.member in InnerMethodsName: #プライベートメソッド
                    _type = "(Private)"
                    classname = ClassName
                else: #staticなメソッド
                    _type = "(Static)"
            elif not call.qualifier[0].isupper():
                #変数オブジェクトの持つメソッド
                _type = getDecralatedType(call.qualifier, Variables)
                if _type == False:
                    _type = "(Unknown)"+str(call.qualifier)
                else:
                    classname = getClassName(_type) if getClassName(_type) else "(Non_Specific)"
            else:
                #明示的なクラスからのメソッド
                _type = call.qualifier
                classname = getClassName(_type) if getClassName(_type) else "(Non_Specific)"

            CallListA.append(["MI", _type, classname, call.member, arguments])
        else:
            type_name = returnTypeName(call.type)
            _type = returnTypeName(call.type)
            classname = getClassName(_type) if getClassName(_type) else "(Non_Specific)"
            CallListA.append(["CC", _type, classname, _type, arguments])

    return CallListA

def getCallListBB(CallListA, Specifics):
    CallListB = []
    Before_type = "(Unknown)"

    def getClassName(_type):
        for s in Specifics:
            if s[1] == _type:
                return s[0]+"."+s[1]
        return False

    def pickup(calledMethods, call):
        picked = [i for i in calledMethods if len(i.parameters) == len(call[4])]
        if  len(picked) ==0:
            return False
        elif len(picked) ==1:
            return [picked[0], None, None]
        else:
            arguments = [[j.type.name for j in i.parameters] for i in picked]
            arguments = [[j[i] for j in arguments] for i in range(len(call[4]))]
            #arguments = list(set(arguments))
            arguments = ["/".join(list(set(i))) for i in arguments]
            #print(999, arguments)
            returnTypes = "/".join(list(set([i.return_type.name for i in picked])))
            #print(999, arguments, returnTypes)
            return [None, arguments, returnType]

    for call in CallListA:
        if call[1] == "(Before)":
            Before_candidates = [i for i in ClassName2Methods if i.split(".")[-1] == Before_type]
            print(Before_candidates)
            if Before_candidates == []:
                call[2] = "(Non_Specific)"
            elif len(Before_candidates) == 1:
                call[2] = Before_candidates[0]
            else:
                call = "/".join(Before_candidates)
            #call[2] = getClassName(Before_type) if getClassName(Before_type) else "(Non_Specific)"

        if call[2] == "(Non_Specific)" or call[1] == "(Static)":
            CallListB.append(call+["","",""]+[[], "", "Non specific"])
            Before_type = "(Non_Specific)"
        else:
            calledClass = call[2]
            arguments = ""
            returnType = ""
            description = ""
            f1 = f2 = f3 = None

            try:
                f1 = calledClass in ClassName2Methods
                if call[0] == "CC":
                    calledConstructors = ClassName2Constructors[call[2]]
                    f2 = len(calledConstructors)
                    if f2 == 0:
                        arguments = []
                        returnType = "void"
                        description = "Default Constructor"
                    elif f2 == 1:
                        f3 = True
                        the = calledConstructors[0]
                        arguments = [i.type.name for i in the.parameters]
                        returnType = the.name
                        #print(999, the.attrs)
                    else:
                        the = pickup(calledConstructors, call)
                        f3 = bool(the[0])
                        if f3:
                            arguments = [i.type.name for i in the[0].parameters]
                            returnType = the[0].name
                        else:
                            aeguments = the[1]
                            returnType = the[2]
                else:
                    calledMethods = [i for i in ClassName2Methods[calledClass] if i.name == call[3]]
                    f2 = len(calledMethods)
                    if f2 == 1 or f2 == 0:
                        theCalledMethod = calledMethods[0]
                        arguments = [i.type.name for i in theCalledMethod.parameters]
                        returnType = theCalledMethod.return_type.name if theCalledMethod.return_type else "void"
                    else:
                        the = pickup(calledMethods, call)
                        f3 = bool(the[0])
                        print(the)
                        if f3:
                            arguments = [i.type.name for i in the[0].parameters]
                            returnType = the[0].return_type.name if the[0].return_type else "void"
                        else:
                            aeguments = the[1]
                            returnType = the[2]

            except:
                description = "No exist"

            CallListB.append(call+[f1, f2, f3] + [arguments, returnType, description])
            Before_type = returnType

    return CallListB

#========================================================================= output functions

def outputCallList(CallList, P):
    CallList_seq = []
    for c in CallList:
        for m in CallList[c]:
            m[10] = "-".join(m[10])
            m.pop(6)
            CallList_seq.append(m)

    title = ["calledBy", "tag","MIorCC", "class","class_detail", "method", "flag1", "flag2", "flag3", "arguments", "return", "reason"]

    Path(os.getcwd()+"/output/"+P.fullname).mkdir(exist_ok=True, parents=True)
    with open("output/"+P.fullname+"/CallList.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(title)
        writer.writerows(CallList_seq)









#============================================================================================



def output_project(P):
    #全てのファイルパスとそのパッケージの対応
    title = ["filepath", "package.file"]
    output = []
    for code in P.codes:
        codepath = str(code.path).split("github.com/")[1]
        #print(codepath, code.package, code.name)
        output.append([codepath, code.package+"."+code.name])

    Path(os.getcwd()+"/output/"+P.fullname).mkdir(exist_ok=True, parents=True)
    with open("output/"+P.fullname+"/CodeFilePath.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(title)
        writer.writerows(output)

    #全てのメソッドに関する情報
    #全てのクラスに関する情報
    m_title = ["package", "Code", "Class", "Method", "Modifiers", "Parameters", "ReturnType", "Annotations"]
    m_output = []
    c_title = ["package", "Code", "Class", "Modifiers", "extendFrom", "n_method", "n_subclass"]
    c_output = []

    for code in P.codes:
        classes = list(code.classes)
        while classes:
            cls = classes.pop()
            #print(cls.name, cls.obj.modifiers)
            extend_from = cls.get_extends_from() if cls.get_extends_from() else ""
            c_output.append([code.package, code.name, cls.name, "-".join(cls.obj.modifiers), cls.get_extends_from(), len(cls.methods), len(cls.subclass)])
            classes.extend(cls.subclass)
            for constructor in cls.constructors:
                return_type = cls.name
                parameters = [i.type.name for i in constructor.parameters]
                #print("   ", constructor.name, constructor.modifiers, parameters, "->", return_type)
                annotstions = "-".join([i.name for i in constructor.annotations])
                m_output.append([code.package, code.name, cls.name, constructor.name, "-".join(constructor.modifiers), "-".join(parameters), return_type, annotstions])
                #global FullName2MethodObject[".".join([code.package, cls.name, constructor.name])] = constructor
            for method in cls.methods:
                return_type =  method.return_type.name if method.return_type is not None else "void"
                parameters = [i.type.name for i in method.parameters]
                #print("   ", method.name, method.modifiers, parameters, "->", return_type)
                annotstions = "-".join([i.name for i in method.annotations])
                m_output.append([code.package, code.name, cls.name, method.name, "-".join(method.modifiers), "-".join(parameters), return_type, annotstions])
                fullname = ".".join([code.package, cls.name, method.name])
                FullName2MethodObject[fullname] = method

    with open("output/"+P.fullname+"/AllMethods.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(m_title)
        writer.writerows(m_output)

    with open("output/"+P.fullname+"/AllClasses.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(c_title)
        writer.writerows(c_output)
def getMethodCallList(P):
    #if ThisCode.main_class is None or ThisCode.main_class.is_extends or ThisCode.main_class.is_implements:
    MethodCallList = []

    for code in tqdm(P.codes):
        #print(code.path)
        classes = list(code.classes)
        if code.main_class is None:
            #print("skip")
            continue
        GlobalVariables = code.getGlobalVariables()
        while classes:
            cls = classes.pop()
            classes.extend(cls.subclass)
            for method in cls.methods + cls.constructors:
                #print(cls.name+"."+method.name)
                try:
                    LocalValiables = getDeclarations(method)
                    Valiables = GlobalVariables + LocalValiables
                    Stream = getStream(method)
                    CallListA = getCallListA(Valiables, Stream, code, P)
                    CalledList = getCalledList(CallListA, code, P, cls.name)

                    calledby = code.package+"."+cls.name+"."+method.name
                    MethodCallList.extend([[calledby]+i for i in CalledList])
                except:
                    continue

                #continue
                #for i in CalledList:
                #    print(i)
    return MethodCallList
def getCalledList(CallListA, _code, _project, name):
    CalledList = []
    SpecificImportedClasses = _project.getImportedClasses(_code)
    SpecificStaticImportedMethods = _project.getStaticImportedMethods(_code)
    Specifics = SpecificImportedClasses + SpecificStaticImportedMethods

    def getpackage(_class):
        for spe in Specifics:
            if _class == spe[1]:
                return spe[0]
        return "(Non_specific)"

    beforeType = "Unknown"

    for call in CallListA:
        _tag = call[0]
        _type = name if call[1] == "(Private)" else call[1]
        _method = _type if call[2]=="(constructor)" else call[2]
        #_method = call[2]
        _specific = False
        _return = "Unknown"
        _calledMethodFullname = None

        if _type == "(Before)":
            _type = beforeType

        _package = getpackage(_type)
        _specific = True if _package != "(Non_specific)" else False
        fullname = ".".join([_package, _type, _method])
        #print(fullname, fullname in FullName2MethodObject)

        if _tag == "CC":
            _return = _type
        elif _specific == False:
            _return = "(Non_specific)"
        else:
            try:
                theMethod = FullName2MethodObject[fullname]
                _return = method.return_type.name if method.return_type is not None else "void"
            except:
                pass
        beforeType = _return

        CalledList.append([_tag, _package, _type, _method, _specific, _return, fullname])

    return CalledList
def output_MethodCallList(MethodCallList, P):
    title = ["calledBy", "tag","package", "class", "method", "isSpecific", "returnType", "fullname"]

    Path(os.getcwd()+"/output/"+P.fullname).mkdir(exist_ok=True, parents=True)
    with open("output/"+P.fullname+"/MethodCallList.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(title)
        writer.writerows(MethodCallList)


def JDetector(project_path):
    print(project_path)
    ThisProject = Project(project_path)

    codename = ""
    for code in ThisProject.codes:
        if code.package + "." + code.name == codename:
            print(code.strcode)
            sys.exit()

    ProductCodes = [i for i in ThisProject.codes if "/test/" not in str(i.path)]
    TestCodes = [i for i in ThisProject.codes if "/test/" in str(i.path)]
    print("プロダクトコード数", len(ProductCodes))
    print("テストコード数", len(TestCodes))

    AllProductMethods = getAllProductMethods(ThisProject)
    print("プロダクトコードのクラス\n", AllProductMethods)
    AllTestHelperMethods = getAllTestHelperMethods(ThisProject)
    print("テスト補助コードのクラス\n", AllTestHelperMethods)

    print("テストメソッド")
    CallList = getCalledbyTestMethod(ThisProject)
    print(len(CallList))
    outputCallList(CallList, ThisProject)

    #output_project(ThisProject)
    #MethodCallList = getMethodCallList(ThisProject)
    #output_MethodCallList(MethodCallList, ThisProject)





#============================================================ main
if __name__ == '__main__':

    domains = ["Web", "Network", "Data", "Database", "Development", "Distribution"]
    for domain in domains:
        print(domain)
        file = "extracted/"+domain+".txt"
        with open(file) as f:
            namelist = f.read()
            namelist = namelist.split("\n")
            for name in namelist:
                name = "RoboBinding/RoboBinding"
                print(name)

                repopath = os.environ['HOME'] + "/testcodeDB/downloads/github.com/"+name
                print(repopath)

                #print(os.getcwd()+"/output/"+name)
                #print(Path(os.getcwd()+"/output/"+name).exists())
                """if Path(os.getcwd()+"/output/"+name).exists():
                    print("already exists")"""
                    #continue

                #出力するもの
                #全てのファイルパスとそのフルネームの対応
                #コードファイル単位の情報
                #メソッド単位の情報
                #メソッド呼び出しの情報

                """try:
                    JDetector(repopath)
                except:
                    print("Not Success")"""

                ClassName2Methods = {}
                ClassName2Constructors = {}
                ClassName2Class = {}
                ClassName2ExtendFrom = {}
                ClassName2Code = {}
                MethodName2Method = {}
                MethodName2ClassName = {}
                MethodName2isProduct = {}
                MathodName2CallList = {}

                JDetector(repopath)
                sys.exit()
