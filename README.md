# 行情系统 (Market Trading System)

一个基于PySide6的行情显示和交易系统。

## 项目结构

```
market/
├── main.py                 # 主入口文件
├── requirements.txt        # Python依赖
├── market.pyproject       # 项目配置
├── src/                   # 源代码目录
│   ├── __init__.py
│   ├── app.py            # 应用程序主类
│   ├── widgets/          # 自定义组件
│   │   ├── __init__.py
│   │   └── main_widget.py
│   ├── ui/               # UI文件
│   │   ├── __init__.py
│   │   └── ui_form.py
│   ├── models/           # 数据模型
│   │   └── __init__.py
│   └── utils/            # 工具模块
│       ├── __init__.py
│       └── config.py
├── resources/            # 资源文件
│   └── form.ui
├── tests/               # 测试文件
└── docs/               # 文档
```

## 运行方式

```bash
python main.py
```

## 开发

### 生成UI文件

当修改了 `resources/form.ui` 文件后，需要重新生成Python UI文件：

```bash
pyside6-uic resources/form.ui -o src/ui/ui_form.py
```

### 添加新功能

1. **新增组件**: 在 `src/widgets/` 目录下创建新的组件类
2. **数据模型**: 在 `src/models/` 目录下创建数据模型
3. **工具函数**: 在 `src/utils/` 目录下添加工具函数
4. **测试**: 在 `tests/` 目录下添加相应的测试文件

## 扩展指南

- 所有自定义组件继承自相应的Qt组件
- 使用统一的日志系统进行调试
- 配置信息统一管理在 `config.py` 中
- 遵循PEP8代码规范
