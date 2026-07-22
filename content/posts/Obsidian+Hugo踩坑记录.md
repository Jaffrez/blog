---
title: "Obsidian+Hugo踩坑记录"
date: 2026-02-14T02:08:19+08:00
slug: "77605e59"
description: "记录一下配置博客时碰到的问题"
tags:
  - "hugo"
  - "obsidian"
---
今天突然想搞一搞个人博客，于是上网查了查资料，最终参考这篇[博客](https://www.printlove.cn/obsidian-blog/)开始折腾。在这里记录一下碰到的一些问题。以后再碰到了也方便找。
## 1. 使用Obsidian默认时间模板生成的文章无法正常显示
弄好主题和别的一堆东西之后，我发现无论怎么尝试都无法让文章正常显示，最后对比了一些上面那篇博客中可以正常显示的文章，最终确定问题出在文章头的date属性上。
必须要把Obsidian设置中模板>日期格式改为“YYYY-MM-DDTHH:mm:ssZ”，使生成出的时间戳类似于"2026-02-14T02:08:19+08:00"，才能正常被hugo识别并显示。
## 2. github市场中的action自带的hugo版本过老，无法正常生成网站
如果你和我一样把博客放在github pages上，使用市场中的hugo action，可能会出现无法编译的问题。这时候只需要把配置文件中的hugo版本改为最新版就好了。在我写出这一条时，Hugo的最新版本是0.155.3。

## 3. 如何使用文章标题和时间戳生成slug
我在Obsidian中添加了Templater来使用模板生成文章。在模板中添加如下内容再插入就可以自动生成slug。为了避免获取到的文件名称都是Untitled，在生成前会自动询问文章名称。
```yaml
<%*
  let title = await tp.system.prompt("请输入文章标题");
  if (title == null || title == "") { title = "Untitled"; }
  await tp.file.rename(title);
  const timestamp = tp.date.now("YYYY-MM-DDTHH:mm:ssZ");
  const inputString = title + timestamp;
  let hash = 5381;
  for (let i = 0; i < inputString.length; i++) {
      hash = ((hash << 5) + hash) + inputString.charCodeAt(i);
  }

  let hexSlug = (hash >>> 0).toString(16);
  while (hexSlug.length < 8) {
      hexSlug = "0" + hexSlug;
  }
-%>
---
title: "<% title %>"
date: <% tp.file.creation_date("YYYY-MM-DDTHH:mm:ss+08:00") %>
tags: []
slug: "<% hexSlug %>"
share: false
description: ""
author: Jaffrez
dir: posts
comments: true
disableCopyright: false
---

<% tp.file.cursor() %>
```

## 4. 修复添加medium-zoom后，鼠标在目录栏上也显示放大镜
在我给博客添加了一些功能后，我发现了如题的情况，经过一段时间的研究。最终我使用css覆盖的方式修复了这个问题。只需要把下面这段代码加到`layouts/partials/extend_footer.html`的末尾就行。
``` html
<style>
summary .details,
summary span.details {
    cursor: pointer !important;
    pointer-events: auto !important;
}
.toc summary,
.toc .details {
    cursor: pointer !important;
}
</style>
```
