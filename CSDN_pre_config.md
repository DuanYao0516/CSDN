# CSDN 如何快速配置运行

1. 安装 python=3.8
2. 按照 requirements.txt 进行安装
3. 下载数据集 SYSU-MM01.zip 与 RegDB 数据集
4. 移动到 ./CSDN/datasets 目录下
5. 将所有代码中的 `Image.ANTIALIAS` 修改为 `Image.LANCZOS` （pre_process_sysu 与 data_loader/dataset.py 两个文件）
6. 使用预处理脚本处理 sysu 数据集， `python pre_process_sysu.py`
7. 注意修改代码`main.py`中的参数设置 `CUDA_VISIBLE_DEVICES=2 python main.py --cuda cuda:0 --mode test --dataset sysu --output_path ckp/sysu410/base`