
# 1.需要提供的目录
#   1.1 基准包备份目录              baseApkSavePath(没有使用 tinker 或 bugly 热修复的忽略)
#   1.2 项目根目录                  projectPath，默认使用当前目录，将该脚本放到 project 目录下即可
#   1.3 需要加固的渠道配置文件       reinforceChannelFile

# 2.最终的渠道包目录 project/app/finalChannels

# 注意：
# 1.应用宝的渠道名必须为：yingyongbao，否则会导致 yingyongbao 的包用360加固，或者自行修改代码也行
# 2.将自己的 zipalign.exe 和 apksigner.bat 添加到环境变量，例如：C:\Users\xxx\AppData\Local\Android\Sdk\build-tools\26.0.2
# 3.默认所有apk都加固，除了 yingyongbao 渠道外都用360加固

# 脚本执行步骤：
# 1.AssembleRelease 打包未加固版包
# 2.保存基准包到指定目录
# 3.对 build/output/apk 目录下的 flavor 渠道包根据 加固配置文件 选择加固方式并加固
# 4.将加固后的文件 进行 zipalign 对齐，apksigner 签名
# 5.写入渠道，之前的 defaultChannel 按照 channel 文件中批量写入，productFlavor 的渠道分别写入，输出路径为 finalChannels，写入后使用walle打印渠道信息
# 6.完成

import ctypes,sys
import os,json
import os.path 
import shutil 
import time  # 引入time模块

# 保存到的基准包目录
baseApkSavePath = 'E:/BaseApkSave/'
# 项目根目录(当前目录)
projectPath = os.getcwd()+'/'
# 360 加固宝安装目录(如果不存在，则不加固)
reforce360AbsPath = 'F:/360jiagubao_windows_64/jiagu/'
# keystorePath
keystorePath = projectPath + 'app/xx.jks'
# CheckAndroidV2Signature.jar 路径(检测是否 v2 签名)
checkAndroidV2SignJarPath = 'E:/Walle/CheckAndroidV2Signature.jar'
# walle-cli-all 写入渠道(必填)
walleCliAllPath = 'E:/Walle/walle-cli-all.jar'

# 项目 app 目录
projectAppAbsolutePath = projectPath + 'app/'
# 项目 channels 目录
projectChannelsAbsolutePath = projectAppAbsolutePath + 'channels/'
# 项目的最终 channels 目录
projectChannelsFinalAbsolutePath = projectAppAbsolutePath + 'finalChannels/'
# app 的 build.gradle
gradleAbsolutePath = os.path.join(projectAppAbsolutePath + 'build.gradle')
# app 的 channel 文件
projectAppChannelFile = projectAppAbsolutePath + 'channel'
# app 的 build 目录
projectAppBuildAbsolutePath = projectAppAbsolutePath + 'build/'
# app 的 build/outputs/apk 目录
projectAppBuildOutputsApkAbsoultePath = projectAppBuildAbsolutePath + 'outputs/apk/'
# app 的 bakApk 基准包生成目录
projectAppBakApkAbsolutePath = projectAppBuildAbsolutePath + 'bakApk/'

# 改变 windows 输出命令行颜色
# get handle
STD_OUTPUT_HANDLE = -11
FOREGROUND_RED = 0x0c # red.
WHITE_COLOR = 0x0f # white
std_out_handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

def set_cmd_text_color(color, handle=std_out_handle):
    Bool = ctypes.windll.kernel32.SetConsoleTextAttribute(handle, color)
    return Bool

def resetColor():
    set_cmd_text_color(WHITE_COLOR)

def printRed(mess):
    set_cmd_text_color(FOREGROUND_RED)
    sys.stdout.write(mess)
    resetColor()

# 2.保存基准包到指定目录
def copyFiles(sourceDir,  targetDir): 
    if sourceDir.find(".svn") > 0: 
        return 
    for file in os.listdir(sourceDir): 
        sourceFile = os.path.join(sourceDir,  file) 
        targetFile = os.path.join(targetDir,  file) 
        if os.path.isfile(sourceFile): 
            if not os.path.exists(targetDir):  
                os.makedirs(targetDir)  
            if not os.path.exists(targetFile) or(os.path.exists(targetFile) and (os.path.getsize(targetFile) != os.path.getsize(sourceFile))):  
                    open(targetFile, "wb").write(open(sourceFile, "rb").read()) 
        if os.path.isdir(sourceFile): 
            copyFiles(sourceFile, targetFile)


globalVersionCode = ''
globalVersonName = ''
def setGradleVersionCode():
    global globalVersionCode
    global globalVersonName
    with open(gradleAbsolutePath, 'r', encoding='utf-8') as gradleFile:
        for line in gradleFile.readlines():
            if(line.find('versionCode') !=-1 and globalVersionCode==''):
                index = line.find('versionCode')
                globalVersionCode = line[index + len('versionCode'):].strip('\n').strip(' ').strip('"')
                print('获取到 versionCode=' + globalVersionCode)
            if(line.find('versionName') != -1 and globalVersonName==''):
                index = line.find('versionName')
                globalVersonName = line[index + len('versionName'):].strip('\n').strip(' ').strip('"')
                print('获取到 versionName=' + globalVersonName) 

# 3.对 build/output/apk 目录下的 flavor 渠道包根据 加固配置文件 选择加固方式并加固

is360Login = False

# 截取 .apk 后缀的字符串
def getApkPreFix(apkFileAbsPath):
    return os.path.splitext(apkFileAbsPath)[0]

# 判断该 apk 是否可能是批量写入渠道的
def getTargetApkIsWriteChannels(targetApkPath):
    if(targetApkPath.find('release')!=-1 or targetApkPath.find('defaultChannel')!=-1):
        return True
    return False

# 判断 channel 文件中是否有 yingyongbao
def getChannelHasYingyongbao():
    with open(projectAppChannelFile, 'r', encoding='utf-8') as channelsFile:
        for line in channelsFile.readlines():
            if(line.find('yingyongbao') !=-1):
                return True
    return False

# 返回某渠道的 Output/Apk/xxChannel/release/xxx.apk 的绝对路径
def getOutputApkChannelReleaseApkFileAbsPath(channelName):
    isIsOutputsApkDirExist = os.path.exists(projectAppBuildOutputsApkAbsoultePath)
    if(isIsOutputsApkDirExist == True):
        outputApkFiles = os.listdir(projectAppBuildOutputsApkAbsoultePath) #得到文件夹下的所有文件名称  
        if(len(outputApkFiles) != 0 ):
            for file in outputApkFiles: 
                if(file == channelName):
                    if(channelName == 'release'):
                        releaseDirFiles = os.listdir(projectAppBuildOutputsApkAbsoultePath + file)
                    else:
                        releaseDirFiles = os.listdir(projectAppBuildOutputsApkAbsoultePath + file + '/release')
                    for releaseFile in releaseDirFiles:
                        if os.path.splitext(releaseFile)[1] == '.apk': 
                            if(channelName == 'release'):
                                return projectAppBuildOutputsApkAbsoultePath + 'release/' + releaseFile
                            else:
                                return projectAppBuildOutputsApkAbsoultePath + file + '/release/' + releaseFile
                        break
                    break

# 校验是否成功写入渠道信息
def checkIsSuccessWriteChannel(outPutChannelApkAbsPath,channelName):
    print('开始检测是否成功写入渠道信息 ' + outPutChannelApkAbsPath,end='\n\n')
    cmd = 'java -jar ' + walleCliAllPath + ' show ' + outPutChannelApkAbsPath
    stateStr = os.popen(cmd).read()
    print('执行结果:' + stateStr)
    splitChannel = stateStr.split(':')[-1]
    if(len(stateStr) !=0 and splitChannel.find('channel')!=-1):
        print("写入渠道信息成功",end='\n\n')
    else:
        raise RuntimeError('写入渠道信息失败:' + channelName)

globalTimeStamp = ''
# 写入单个渠道(因为通过channel文件写入多个渠道不知道怎么改apk输出格式)
def writeSingleChannel(signApkAbsPath,channelName):
    global globalTimeStamp
    global globalVersionCode
    global globalVersonName
    if(globalTimeStamp==''):
        globalTimeStamp = '20' + time.strftime("%y%m%d-%H-%M-%S", time.localtime())

    # outPutChannelApkAbsPath = projectChannelsFinalAbsolutePath + getApkPreFix(os.path.basename(signApkAbsPath)) + 'Channeled.apk'  #生成的渠道包的最终路径
    curDir = os.path.basename(os.path.dirname(__file__) )
    outPutChannelApkAbsPath = projectChannelsFinalAbsolutePath + 'app-' + curDir + '-' + channelName + '-release-' + 'v' + globalVersonName + '-' + globalVersionCode + '-' + globalTimeStamp + ".apk"
    print("开始写入渠道"+ " channelName=" + channelName,end='\n\n')
    cmd = 'java -jar ' + walleCliAllPath + ' put -c ' + channelName + ' '+ signApkAbsPath + ' ' + outPutChannelApkAbsPath
    print("cmd=" + cmd)
    os.system(cmd)
    # 获取渠道信息
    checkIsSuccessWriteChannel(outPutChannelApkAbsPath,channelName)

# 使用 walle 写入渠道
# notFlavor:不使用 productFlavor 差异化打包，并且 productFlavor{} 中也没有 defaultChannel 的 flavor，此时根据 channel 文件判断是否加固
def walleWriteChannls(signApkAbsPath,channelName):
    
    print('开始使用 walle 写入渠道 ' + signApkAbsPath + ' 渠道名为' + channelName,end='\n\n')

    if(getTargetApkIsWriteChannels(channelName)): #写入多个渠道
         
        print("开始写入多个渠道" + " channelName=" + channelName,end='\n\n') #app-defaultChannel-releaseZipalign_52toys
        # cmd = 'java -jar ' + walleCliAllPath + ' batch -f '+ projectAppChannelFile + ' '+ signApkAbsPath + ' ' + projectChannelsFinalAbsolutePath
        # print("cmd=" + cmd)
        # os.system(cmd)
        # finalAbsPathFiles = os.listdir(projectChannelsFinalAbsolutePath)
        flavorSet = getAllFlavor('productFlavors')
        with open(projectAppChannelFile, 'r', encoding='utf-8') as channelsFile:
            for line in channelsFile.readlines():
                line = line.strip('\n')
                if(line.find('yingyongbao') == -1 and line not in flavorSet): #应用宝的不生成渠道包 #已有 productFlavor 的不生成渠道包
                    print('开始打单渠道包' + line)
                    writeSingleChannel(signApkAbsPath,line)
                    
    else: #写入单个渠道
       writeSingleChannel(signApkAbsPath,channelName)

# v2 签名完成
def onSignApkSuccess(signApkAbsPath,channelName):
    if(os.path.exists(checkAndroidV2SignJarPath)):
        print('开始检查是否成功 v2 签名',end='\n\n')
        cmd = 'java -jar '+ checkAndroidV2SignJarPath + ' '+ signApkAbsPath
        stateStr = os.popen(cmd).read()
        print('签名信息:' + stateStr)
        if(len(stateStr) !=0 and stateStr.find('failed')==-1):
            print("v2 签名成功" + signApkAbsPath,end='\n\n')
            walleWriteChannls(signApkAbsPath,channelName)
        else:
            raise RuntimeError('v2 签名失败' +  signApkAbsPath)

#  apksigner 签名
def signApk(signApkAbsPath,channelName):
    print('开始使用 v2 签名 ' + signApkAbsPath,end='\n\n')

    with open('buildSignChannelConfig.json', 'r') as configJson:
        config = json.load(configJson, encoding="utf-8")

        keyAlias = config['keyAlias']
        storePassword = config['storePassword']
        keyPassword = config['keyPassword']

        finalSignedApkAbsPath = getApkPreFix(signApkAbsPath) + 'Sign.apk '
        finalUnSignApkAbsPath = signApkAbsPath

        cmd = 'apksigner sign --ks '+ keystorePath +' --ks-key-alias '+ keyAlias +' --ks-pass pass:'+ storePassword  +' --key-pass pass:'+ keyPassword +' --out ' + finalSignedApkAbsPath + ' ' + finalUnSignApkAbsPath
        print('签名命令:'+ cmd,end='\n\n')

        state = os.system(cmd)
        if(state==0):
            print('执行签名成功!')
            onSignApkSuccess(signApkAbsPath,channelName)
        else:
            print("\n")
            print('配置信息中有特殊字符，例如&*，请自行输入，复制 password 后右键',end='\n\n')
            cmd = 'apksigner sign --ks ' + keystorePath + ' ' +  finalUnSignApkAbsPath
            print('签名命令:'+ cmd,end='\n\n')
            state = os.system(cmd)
            if(state == 0):
                #执行重命名
                signedApkAbsPath = getApkPreFix(signApkAbsPath) + 'Sign.apk '
                if(os.path.exists(signedApkAbsPath)):
                    print(signedApkAbsPath + '文件已存在，删除掉')
                    os.remove(signedApkAbsPath)
                print('开始执行重命名，将 ' + signApkAbsPath + ' 重命名为 ' + signedApkAbsPath)
                os.rename(signApkAbsPath, signedApkAbsPath)
                print('执行签名成功! path=' + signedApkAbsPath)
                onSignApkSuccess(signedApkAbsPath,channelName)
            else:
                #这里密码可能输错，直接抛异常
                raise RuntimeError('执行签名失败' + channelName)
    
#  zipalign 对齐   
def zipalignSignerWriteChannel(reforceApkAbsPath,channelName):
    infilePath = reforceApkAbsPath
    outfilePath = getApkPreFix(reforceApkAbsPath) + 'Zipalign.apk'
    if(os.path.exists(outfilePath)):
        print( outfilePath + '文件已存在，删除掉')
        os.remove(outfilePath)
    cmd = 'zipalign -v 4 ' + infilePath  + ' ' + outfilePath
    print('开始使用 zipalign 对齐 cmd=' + cmd)
    state = os.system(cmd)
    if(state == 0):
        print('对齐成功')
    else:
        raise RuntimeError('对齐失败')
    signApk(outfilePath,channelName)

# 使用 360 加固助手/乐固加固
def reforceChannelFunc(channelApkAbsolutePath,channelName,is360):
    if(is360):
        if os.path.exists(reforce360AbsPath):

            print('开始使用360加固助手加固apk' + channelApkAbsolutePath + ' 渠道名为' + channelName)

            cmdPreFix = 'java -jar '+ reforce360AbsPath +'jiagu.jar '
            global is360Login #必须使用 global 引用全局变量：否则报 pylint: variable 'xxx' referenced before assignment
            
            if(is360Login == False):
                
                # 登录360
                with open('buildSignChannelConfig.json', 'r') as configJson:
                    config = json.load(configJson, encoding="utf-8")

                    userName360 = config['360ReforceUsername']
                    pwd360 = config['360ReforcePassword']
                    if((not userName360) or (not pwd360)):
                        print('360 用户名和密码是空的，停止登录')
                    else:
                        cmd =  cmdPreFix + '-login ' + userName360  + ' ' + pwd360
                        print('360 登录 cmd= ' + cmd)
                        state = os.system(cmd)

                        if(state==0):
                            print('360 加固宝登录成功')
                        else:
                            raise RuntimeError('360 加固宝登录失败，加固取消' + channelName)
                        is360Login = True

            # 加固应用
            inputAPKPath = channelApkAbsolutePath
            outputAPKPath = os.path.dirname(channelApkAbsolutePath)  # outputAPKPath 不能带 .apk 后缀
            cmd = cmdPreFix + '-jiagu ' + inputAPKPath + ' ' +  outputAPKPath
            print('开始使用 360 加固宝加固应用 cmd=' + cmd)
            state = os.system(cmd) #这里使用 pOpen 就阻塞了，只能使用 os.system()，但是不准
            if(state == 0):
                print('加固成功,channel 为' + channelName)
            else:
                print('加固失败，再试一次')
                state = os.system(cmd)
                if(state == 0):
                    print('加固成功,channel 为' + channelName)
                else:
                    raise RuntimeError('加固失败,channel 为' + channelName)

            # 对齐，签名
            jiaguFiles = os.listdir(outputAPKPath)
            tempJiaguFileName = ''
            for file in jiaguFiles: 
                if(file.find('jiagu')!=-1):
                    tempJiaguFileName = file
                    break
            signOutputApkPath = outputAPKPath + '/' +  tempJiaguFileName
            print('开始对齐，签名，apkPath =' + signOutputApkPath)
            zipalignSignerWriteChannel(signOutputApkPath,channelName)
        else:
            print('360 加固宝目录不存在，停止加固')
    else:
        print('使用乐固加固apk ' + channelApkAbsolutePath + ' 渠道名为' + channelName)
        printRed('检测到有yingyongbao渠道，但乐固暂时不支持命令行，请手动加固!')

# 获取 gradle 文件中的所有 flavor
flavorsSet = set([])
def getAllFlavor(brancketName):
    global flavorSet
    if(len(flavorsSet)!=0):
        return flavorsSet
    with open(gradleAbsolutePath, 'r+', encoding='utf-8') as gradleFile:
        bracketLeftCount = 0
        bracketRightCount = 0
        bracketChildLeftCount = 0
        bracketChildRightCound = 0
        isFindProductFlavor = False
        flavorChildName = ""
        for line in gradleFile.readlines():

            if(line.find(brancketName) != -1):
                isFindProductFlavor = True
                
            if(isFindProductFlavor == True):
                if(line.find('{') != -1):
                    bracketLeftCount +=1
                if(line.find('}') != -1):
                    bracketRightCount +=1

                #从这起开始注释，直到{}匹配为止
                if(bracketLeftCount == bracketRightCount):
                    isFindProductFlavor = False
                    return flavorsSet

                if(bracketLeftCount >1): 
                    if(line.find('{') != -1):
                        leftIndex = line.find('{')
                        flavorChildName = line[0:leftIndex].strip(' ').strip(' \n')
                        bracketChildLeftCount +=1
                    if(line.find('}') != -1):
                        bracketChildRightCound +=1
                    if(bracketChildLeftCount!=0 and bracketChildRightCound!=0 and bracketChildLeftCount == bracketChildRightCound):
                        flavorsSet.add(flavorChildName)
                        bracketChildLeftCount = 0
                        bracketChildRightCound = 0
    return flavorsSet

# AssembleRelease 打包未加固版包
cmd = projectPath + 'gradlew clean assembleRelease'
state = os.system(cmd)
if(state != 0):
    raise RuntimeError('gradle build 异常!')

# 执行 获取 versionCode 和 versionName 的方法
setGradleVersionCode()

# 复制基准包
isbakApkPathExist = os.path.exists(projectAppBakApkAbsolutePath)
bakApkAbsolutePathWithDate = ""  #带日期的基准包目录
if(isbakApkPathExist == True):
    files = os.listdir(projectAppBakApkAbsolutePath) #得到文件夹下的所有文件名称  
    if(len(files) != 0 ):
        tempBakApkPathFolder = files[len(files)-1]   #保存最新日期的包
        tempFromBakApkAbsolutePath = projectAppBakApkAbsolutePath  + tempBakApkPathFolder
        curDir = os.path.basename(os.path.dirname(__file__) )
        bakApkAbsolutePathWithDate = baseApkSavePath + curDir + '/' + tempBakApkPathFolder #基准包路径 + 当前项目名 + app-0525xxx
        print('开始复制基准包 from=' + tempFromBakApkAbsolutePath + ' to=' + bakApkAbsolutePathWithDate)
        copyFiles(tempFromBakApkAbsolutePath,bakApkAbsolutePathWithDate)
        print('path=' + bakApkAbsolutePathWithDate)
else:
    print('基准包目录不存在')

# 遍历 outputs/apk/ 目录下的 apk，如果 reforceChannelFile 中有该渠道，则加固
outputApkChannelFiles = os.listdir(projectAppBuildOutputsApkAbsoultePath) #得到文件夹下的所有文件名称  
if(len(outputApkChannelFiles) != 0 ):

    # 遍历 output/apk/ 下的所有渠道 file
    for file in outputApkChannelFiles: 
        if(file.find('yingyongbao')!=-1):
            print('开始加固 flavor 为 yingyongbao 的渠道')
            reforceChannelFunc(getOutputApkChannelReleaseApkFileAbsPath(file),'yingyongbao',False)
        else:
            if(getTargetApkIsWriteChannels(file)):
                print('开始加固默认渠道' + file)
                if(getChannelHasYingyongbao()):
                    #使用 360 加固一次
                    reforceChannelFunc(getOutputApkChannelReleaseApkFileAbsPath(file),file,True)
                    #使用 乐固加固一次
                    reforceChannelFunc(getOutputApkChannelReleaseApkFileAbsPath(file),file,False)
                else:
                    reforceChannelFunc(getOutputApkChannelReleaseApkFileAbsPath(file),file,True)
            else:
                print('开始使用 360 加固宝加固 非默认，非 yingyongbao 的渠道')
                reforceChannelFunc(getOutputApkChannelReleaseApkFileAbsPath(file),file,True)

else:
    print('output/apk/ 文件夹中的没有 apk，取消加固')
