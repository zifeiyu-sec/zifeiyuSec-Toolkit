1. **分析问题原因**：在`core/app.py`的`_open_local`函数中，Windows系统下对.exe文件使用了`subprocess.Popen([path], shell=True)`直接运行，没有指定创建新窗口的参数，导致命令行exe工具继承父进程终端窗口。

2. **修改Windows系统下的.exe文件运行逻辑**：

   * 在`_open_local`函数中，当检测到文件是.exe类型时，也使用`cmd.exe /c start`命令运行

   * 这样可以确保所有命令行工具（包括.exe）都在新的终端窗口中运行

   * 保持现有的.py, .bat, .cmd文件处理逻辑不变

3. **修改代码位置**：`core/app.py`文件中的`_open_local`函数（约行538-555）

4. **测试验证**：修改后，点击卡片运行命令行exe工具时，会在

