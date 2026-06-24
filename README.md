# JJG_Download_Tool

国家计量技术规范全文公开系统下载工具。

原项目：[AthenaCN/JJG_Download_Tool](https://github.com/AthenaCN/JJG_Download_Tool)

原版脚本使用的旧详情页网址已经被新格式替代，且在线预览页的令牌变量也已发生变化。本版兼容：

- 当前详情页：`https://jjg.spc.org.cn/resmea/standard/detail.html?standno=JJF+1070-2023`
- 带分页参数的当前详情页
- 旧详情页：`http://jjg.spc.org.cn/resmea/standard/JJF%25201261.9-2013/?`
- 直接输入规范编号：`JJF 1070-2023`

## 使用方法

需要 Python 3.10 或更高版本及 `requests`：

```powershell
python -m pip install requests
python .\JJG_Download_Tool.py "https://jjg.spc.org.cn/resmea/standard/detail.html?standno=JJF+1070-2023" -y
```

也可以不带参数运行，按提示交互输入：

```powershell
python .\JJG_Download_Tool.py
```

使用 `-o` 指定保存目录：

```powershell
python .\JJG_Download_Tool.py "JJF 1070-2023" -o .\downloads -y
```

脚本只有在响应内容包含 PDF 文件头时才会写入文件并报告成功。
