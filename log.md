# 工作日志

## 0310

1. 配置环境，编写配置文件
2. 尝试跑通测试sysu代码  `CUDA_VISIBLE_DEVICES=2 python main.py --cuda cuda:0 --mode test --dataset sysu --output_path ckp/sysu410/base`
3. 尝试跑通训练sysu代码 `CUDA_VISIBLE_DEVICES=1 python main.py --cuda cuda:0 --mode train --dataset sysu --output_path ckp/sysu0310/`, 目测没有问题，中间强制退出了，没有训练完。
4. 尝试跑通训练regdb的代码 `CUDA_VISIBLE_DEVICES=1 python main.py --cuda cuda:0 --mode train --dataset regdb --output_path ckp/regdb0310`, 已经跑通

## 0311

0. 搞清楚regdb数据集组织方式、agreid数据集组织方式，两者的不同之处。
1. 搞清楚regdb数据载入逻辑
2. 搞清楚regdb双向测试逻辑