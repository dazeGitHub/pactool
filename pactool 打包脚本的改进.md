
#### 1. 为什么要使用 多渠道快速打包脚本

直接使用 walle 打多渠道包后使用 360 加固，渠道信息会丢失（因为 360 加固宝使用的签名是 v1，walle 获取不到渠道）

所以 apk 打包加固签名要经历如下步骤：

1. AssembleRelease 生成未加固的 Release 包
2. 使用360加固助手加固(注意:不要签名)
3. 使用 zipalign 压缩对齐 
4. 使用 apksigner 进行签名
5. 检查 V2 签名是否成功
6. 使用 walle-cli-all.jar 写入渠道
7. 查看是否成功写入了渠道信息

所以希望用脚本实现以上繁琐步骤

#### 2. packtool 打包脚本

https://blog.csdn.net/qq_35559358/article/details/75966284
参考：http://www.cnblogs.com/YatHo/p/6672484.html

##### 该 packtool 打包脚本的缺点

以上的 packtool 的打包脚本无法同时复制基准包到指定目录，无法直接加固，而只能在加固后完成 zipalign 对齐和 v2 签名，而且没有日志..

#### 3. 改进后的 python 脚本

##### 1.一键打包

该脚本修复了 packtool 的以上缺点，可以打包的同时复制基准包，然后调用 360 加固宝实现命令行加固，加固后完成 zipalign 对齐和 v2 签名，可以通过日志查看是否成功

> 由于乐固不支持命令行，所以 yingyongbao 渠道只能手动加固，加固完成后执行 leguPacktoo.py

##### 2.支持 productFlavor 差异化打包

该脚本自动对 build/output/apk/ 目录下的包做加固签名写渠道等工作，并输出到 ``project/app/finalChannels`` 目录下。

不差异化打包就不需要用 productFlavor，直接将所有渠道写入 channel 文件即可

> 由于该目录下默认包目录是 release ，使用 productFlavor 会生成对应的渠道目录，所以该脚本根据目录名完成非默认包的渠道写入，而对默认包根据 channel 文件完成批量渠道写入

**注意：** 使用 productFlavor 时需要指定默认渠道为 defaultChannel!

> 美团walle 虽然可以通过 gradlew clean assembleXXXReleaseChannels 来支持 productFlavor，但是执行该命令会同时在 channel 目录下生成 channel 文件中的所有渠道包，并且这些渠道包中的资源都是使用的该XXX渠道的，导致正常的apk包也变成差异化的了，以至于得先把 channnel 文件中的渠道都注释掉

代码参考：BuildSignChannelApk.py

#### 4. 改进后的脚本的配置

##### 目录的配置 :

将 BuildSignChannelApk.py，leguPacktool.py 和 buildSignChannelConfig.json 放到 Project 目录下

将 channel 文件(包含要打包的渠道) 放到 Project/app 目录下

> 可以参考 Project Structure 的目录结构

##### app 中 build.gradle 的配置

因为该脚本需要用到 keystore password 等信息，所以为方便将配置信息放到 buildSignChannelConfig.json 中，为了防止 build.gradle 中也保存一份，需要将其 storePassword 等配置为从 buildSignChannelConfig.json 中读取

```groovy
//读取配置的 buildSignChannelConfig.json 的信息
import groovy.json.JsonSlurper
def jsonPayload = new File("buildSignChannelConfig.json").text
def slurper = new JsonSlurper()
def configJsonObj = slurper.parseText(jsonPayload)

signingConfigs {
    debug {
        v1SigningEnabled true
        v2SigningEnabled true
    }
    release {
        storeFile file("toys.jks")
        storePassword configJsonObj['storePassword']
        keyAlias configJsonObj['keyAlias']
        keyPassword configJsonObj['keyPassword']
        v1SigningEnabled true
        v2SigningEnabled true
    }
}
```

##### 路径的配置

基准包目录：修改 BuildSignChannelApk.py 中的 baseApkSavePath（如果没有使用 tinker/bugly 的热修复，则不用配置）

360 加固宝安装目录(如果不存在，则不加固)：修改 BuildSignChannelApk.py 中的 reforce360AbsPath

keystorePath：修改 BuildSignChannelApk.py 中的 keystorePath

CheckAndroidV2Signature.jar 路径：这个是检测是否 v2 签名的，修改 BuildSignChannelApk.py 中的 checkAndroidV2SignJarPath

walleCliAllPath 路径：这是用于 walle-cli-all.jar 写入渠道的，修改 BuildSignChannelApk.py 中的 walleCliAllPath

环境变量的配置：将自己的 zipalign.exe 和 apksigner.bat 添加到环境变量，例如：C:\Users\xxx\AppData\Local\Android\Sdk\build-tools\26.0.2

> lib 目录中提供 apksigner.bat，CheckAndroidV2Signature.jar，walle-cli-all.jar，zipalign.exe

#### 5. 如何使用

##### 1.安装 python 环境
##### 2.运行 BuildSignChannelApk.py 

> 如果使用 vsCode 并且安装了 python 插件，可以直接用 vsCode 打开 project 工作目录，并 F5 运行 BuildSignChannelApk.py