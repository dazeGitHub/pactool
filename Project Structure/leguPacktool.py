
import sys, os,json,time
projectPath = os.getcwd()+'/'

# 项目 app 目录
projectAppAbsolutePath = projectPath + 'app/'
# 项目 channels 目录
projectChannelsAbsolutePath = projectAppAbsolutePath + 'channels/'
# 项目的最终 channels 目录
projectChannelsFinalAbsolutePath = projectAppAbsolutePath + 'finalChannels/'
# CheckAndroidV2Signature.jar 路径(检测是否 v2 签名)
checkAndroidV2SignJarPath = 'E:/Walle/CheckAndroidV2Signature.jar'
walleCliAllPath = 'E:/Walle/walle-cli-all.jar'
gradleAbsolutePath = os.path.join(projectAppAbsolutePath + 'build.gradle')
# keystorePath
keystorePath = projectPath + 'app/toys.jks'

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

# v2 签名完成
def onSignApkSuccess(signApkAbsPath,channelName):
    if(os.path.exists(checkAndroidV2SignJarPath)):
        print('开始检查是否成功 v2 签名',end='\n\n')
        cmd = 'java -jar '+ checkAndroidV2SignJarPath + ' '+ signApkAbsPath
        stateStr = os.popen(cmd).read()
        print('签名信息:' + stateStr)
        if(len(stateStr) !=0 and stateStr.find('failed')==-1):
            print("v2 签名成功" + signApkAbsPath,end='\n\n')
            writeSingleChannel(signApkAbsPath,channelName)
        else:
            raise RuntimeError('v2 签名失败' +  signApkAbsPath)

# 截取 .apk 后缀的字符串
def getApkPreFix(apkFileAbsPath):
    return os.path.splitext(apkFileAbsPath)[0]

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

# try:
setGradleVersionCode()
filepath = sys.argv[1] #直接将 legu 加固好的 apk 拖过来作为 argv[1]
print('filePath' + filepath)
signApk(filepath,'yingyongbao')
# finally:
#     print("finally") 
#     input("暂停窗口")

