## 2025/01/27 代码阅读注释

代码树如下，应重点关注 /core , /network, /data_loader/dataset.py：

```bash
.
|-- README.md
|-- core  # 
|   |-- __init__.py
|   |-- __pycache__
|   |-- base.py     # 基础类
|   |-- test.py     # 测试
|   `-- train.py    # 训练
|-- data_loader     # 与数据加载相关的文件
|   |-- __init__.py
|   |-- __pycache__
|   |-- dataset.py  # 对不同的数据集定义不同的数据集处理类
|   |-- loader.py   # 包含数据加载器、包括训练与测试
|   |-- processing.py  # 数据处理
|   `-- sampler.py  # 数据采样器
|-- main.py         # 程序的主入口文件
|-- network
|   |-- __init__.py
|   |-- __pycache__
|   |-- clip        # CLIP 模型
|   |-- gem_pool.py # 前向传播函数，平均池化
|   |-- lr.py       # 学习率及调整策略
|   |-- model.py    # 模型相关的代码，比如transformer乘积注意力
|   `-- processing.py   # 模型处理
|-- run.sh          # 运行项目的脚本文件
`-- tools           # 工具类与辅助函数的集合
    |-- MSEL.py     # 均方误差损失函数 MSEL 代码
    |-- __init__.py
    |-- __pycache__
    |-- eval_metrics.py # 评估指标
    |-- logger.py   # 日志记录
    |-- loss.py     # 损失函数的定义，如三元组损失等
    |-- meter.py    # 计量工具
    `-- utils.py    # 实用工具函数
```

---

原项目作者：

权重已放出。链接：https://pan.baidu.com/s/1kiMj34iGZMvxFrXmZ4d9EA 
提取码：b7l1
