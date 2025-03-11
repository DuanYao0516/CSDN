# 工作日志

1. 配置环境，编写配置文件
2. 尝试跑通测试sysu代码  `CUDA_VISIBLE_DEVICES=2 python main.py --cuda cuda:0 --mode test --dataset sysu --output_path ckp/sysu410/base`
3. 尝试跑通训练sysu代码 `CUDA_VISIBLE_DEVICES=1 python main.py --cuda cuda:0 --mode train --dataset sysu --output_path ckp/sysu0310/`, 目测没有问题，中间强制退出了，没有训练完。
4. 尝试跑通训练regdb的代码 `CUDA_VISIBLE_DEVICES=1 python main.py --cuda cuda:0 --mode train --dataset regdb --output_path ckp/regdb0310`