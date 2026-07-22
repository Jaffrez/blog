---
title: "安装使用GNU target的Rust"
date: 2026-02-16T00:15:27+08:00
slug: "e0726e2a"
description: "简要记录在windows下搭建rust环境"
tags:
  - "rust"
---
看看网上搭建Rust环境的教程，一般都是使用MSVC作为后端。这里介绍一下如何使用gnu后端搭建。
当然，使用gnu后端也有好几种，比如使用cygwin或者msys2，就我个人而言，我不太喜欢装额外的环境，所以最终选择了winlibs，它是一个打包好的编译器和工具包。

## 第一步：下载winlibs
在这个网址下载[winlibs](https://winlibs.com/),大部分时候选择最新版本就好。这里我选择了图中的版本。
![winlibs.com](https://pic.planten.dev/2026/02/f8fd3ba314bf9e7f1116f451628e1295.webp)
然后解压并移动到合适的位置。例如`E:/mingw/`。
接下来需要把gcc所在的位置加入PATH，以便于rust编译器能找到gcc。
打开系统的环境变量设置，将解压后的文件夹中的bin文件夹加入到PATH。
![用户的PATH变量](https://pic.planten.dev/2026/02/f8cf5b51f9ddc36071dda9a9b0cf5cfd.webp)

完成这一切后就可以重启电脑，使环境变量生效。

## 第二步：开始安装Rust
首先打开终端，输入`$ gcc[enter]`。如果看到和图片中类似的输出，就说明gcc已经成功的加入到PATH中。

![Output](https://pic.planten.dev/2026/02/2f43663ae92a3507c9ee3cc5baf1d0ef.webp)

接下来获取Rust的安装包。可以直接点击这个[链接](https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe)下载，或者自行到官网获取。
下载完安装包后，可以配置一个镜像来加快稍后的安装速度。我建议使用字节的[RsProxy](https://rsproxy.cn/)。毕竟不限速（doge）。
```
export RUSTUP_DIST_SERVER="https://rsproxy.cn"
export RUSTUP_UPDATE_ROOT="https://rsproxy.cn/rustup"
```
需要把这两行环境变量加入到shell中。因为我使用的是[Nushell](https://www.nushell.sh/)。所以我改成了对应的
```nu
$env.RUSTUP_DIST_SERVER = "https://rsproxy.cn"
$env.RUSTUP_UPDATE_ROOT = "https://rsproxy.cn/rustup"
```
只需要按照具体的shell修改即可。接下来就是正式安装。回到下载的Rust安装包所在的文件夹。打开终端，使用`$ ./rustup-init.exe`启动安装。
![rust-init.exe](https://pic.planten.dev/2026/02/51463325eb063d1e4df2a9f716edd5b7.webp)

可以看到3个选项。因为要使用GNU target，所以这里输入`$ 3[enter]`。  
然后再输入`$ 2[enter]`进入自定义安装。  
终端中会出现类似于`Default host triple? [x86_64-pc-windows-msvc]`的提示。中括号中的是默认选项。如果回车就会自动使用这个。  
我们输入`x86_64-pc-windows-gnu[enter]`,接下来的几项就是工具链的选择。通常都直接使用默认选项，回车就好。  

等再次出现3个选项时。我们就已经完成了所有的设定，让我们直接输入`[enter]`开始安装。
经过一段时间的等待之后，安装完成了，由于配置了镜像，所以安装会比较快速。
![安装完成](https://pic.planten.dev/2026/02/00df952ec79b951d64d4cd010d090125.webp)

出现类似的输出就是安装成功。然后需要重启shell或电脑来应用修改的PATH。整个安装过程就完成了。打开终端输入`$ rustc[enter]`显示出一长串文档就是安装成功了。

## 第三步：额外配置
上面为Rust的安装和更新配置了镜像，但是Rust在开发时需要从crates.io下载大量的库，有时候也会很慢，幸运的是，RsProxy也提供了镜像。
在cargo目录下新建一个文件`Config.toml`。通常这个目录位于`C:/Users/用户名/.cargo`。
我们需要把配置文件放在`C:/Users/用户名/.cargo/Config.toml`。在文件中添加如下内容。
```toml
[source.crates-io]
replace-with = 'rsproxy-sparse'
[source.rsproxy]
registry = "https://rsproxy.cn/crates.io-index"
[source.rsproxy-sparse]
registry = "sparse+https://rsproxy.cn/index/"
[registries.rsproxy]
index = "https://rsproxy.cn/crates.io-index"
[net]
git-fetch-with-cli = true
```
这样就可以使用RsProxy下载crates了。
