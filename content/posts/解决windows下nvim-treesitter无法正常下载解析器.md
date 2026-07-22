---
title: "解决windows下nvim-treesitter无法正常下载解析器"
date: 2026-02-17T23:58:23+08:00
slug: "d86f51b1"
description: "很神奇的问题"
tags:
  - "neovim"
---


这两天一直在折腾neovim，在搞treesitter的语法高亮时碰到一个很奇怪的问题，在配置好插件后一直报错，显示windows自带的tar无法解压解析器。

于是乎我寻找了一下压缩包所在的位置，但是却都是空的。经历了一翻折腾之后找到了解决方案。

### 第一步：获取curl
我重新获取了最新版的curl，或许不是版本的问题，不过我懒得试了。从[这里](https://curl.se)下载curl。加入到**系统**的PATH中。注意，是系统PATH，不是用户的PATH。并把顺序提高的最前面，如图所示。
![系统的PATH](https://pic.planten.dev/2026/02/cee9b9631f470fbb5cc1edff5fa1adcd.webp)

然后重启电脑应用新的环境变量。

### 第二步：配置curl暂时忽略ssl证书
在我替换了系统的curl之后，neovim就不再报无法解压，而是报证书不正确。所以我尝试了暂时禁用SSL验证。但是请注意，这不建议用在任何生产环境，只是我个人的临时解决方案。

打开资源管理器，在地址栏输入`%APPDATA%`回车，如图所示。
![APPDATA](https://pic.planten.dev/2026/02/355df45bcf974e4b2b1be5088feea654.webp)

打开里面的Romaing文件夹，创建一个新的文本文件`.curlrc`。在里面加入下面的配置。
```
insecure
```
然后保存。重新打开neovim，curl就可以正常下载解析器了。记得下完之后删除这个配置文件。
附上安装完成的nvim-treesitter。
![image.png](https://pic.planten.dev/2026/02/fdf01edee3bd1a982aa8566b562c8470.webp)
