import javalang, sys, os, csv
from pathlib import Path
from tqdm import tqdm

with open("output/netty/AllMethods.csv") as f:
    reader = csv.reader(f)
    AllMethods = [i for i in reader][1:]

with open("output/netty/AllMethodCall.csv") as f:
    reader = csv.reader(f)
    AllMethodCall = [i for i in reader][1:]

for method in tqdm(list(AllMethods)):
    if method[-2] == "True" and method[-1] == "False":
        fullname = method[0]+"."+method[2]+"."+method[3]
        call = [i for i in AllMethodCall if i[0]==fullname]
        specific = [i for i in call if i[3] == "True" and i[1] != "(Private)"]
        specific = [i for i in specific if not i[2].islower()]
        #print(fullname, len(specific))
        if len(specific)==1:
            print(method)

#使用するテストメソッド
#['io.netty.handler.codec.CharSequenceValueConverterTest.testByteFromAsciiString', 'CharSequenceValueConverter', 'convertToByte', 'True', 'byte']
#['io.netty.handler.codec', 'CharSequenceValueConverter', 'CharSequenceValueConverter', 'convertToByte', 'public', 'CharSequence', 'byte', 'False', 'False', 'False']
