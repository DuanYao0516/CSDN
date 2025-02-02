
import os
import ast
import torch
import random
import argparse
import numpy as np


from data_loader.loader import Loader
from core import Base, train, train_stage1, train_stage2, test
from tools import make_dirs, Logger, os_walk, time_now
import warnings
warnings.filterwarnings("ignore")   # 忽略警告信息

best_mAP = 0    # 全局 最佳平均精度均值 mAP
best_rank1 = 0  # 全局 rank1 准确率

#  设置随机种子
def seed_torch(seed):
    seed = int(seed)
    random.seed(seed)
    os.environ['PYTHONASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def main(config):
    global best_mAP
    global best_rank1

    # 初始化数据加载器与模型
    loaders = Loader(config)
    model = Base(config)

    # 创建输出目录、模型保存目录、日志保存目录
    make_dirs(model.output_path)
    make_dirs(model.save_model_path)
    make_dirs(model.save_logs_path)

    # 初始化日志记录器
    logger = Logger(os.path.join(os.path.join(config.output_path, 'logs/'), 'log.txt'))
    logger('\n' * 3)
    logger(config)

    # 训练
    if config.mode == 'train':
        if config.resume_train_epoch >= 0: # 恢复训练，从指定轮次训练
            model.resume_model(config.resume_train_epoch)
            start_train_epoch = config.resume_train_epoch
        else:   # 开始训练
            start_train_epoch = 0

        # 自动恢复
        if config.auto_resume_training_from_lastest_step:
            root, _, files = os_walk(model.save_model_path)
            if len(files) > 0:
                indexes = []
                for file in files:
                    indexes.append(int(file.replace('.pth', '').split('_')[-1]))
                indexes = sorted(list(set(indexes)), reverse=False)
                model.resume_model(indexes[-1])
                start_train_epoch = indexes[-1]
                logger('Time: {}, automatically resume training from the latest step (model {})'.format(time_now(),
                                    indexes[-1]))

        # 第一阶段训练
        print('Start the 1st Stage of Training')
        print('Extracting Image Features')
        # 提取图像特征
        visible_image_features = [] # 可见光图像特征
        visible_labels = []         # 可见光图像标签
        infrared_image_features = []    # 近红外图像特征
        infrared_labels = []            # 近红外图像标签

        with torch.no_grad():
            for i, data in enumerate(loaders.get_train_normal_loader()):
                rgb_imgs, rgb_pids = data[0].to(model.device), data[2].to(model.device)
                ir_imgs, ir_pids = data[1].to(model.device), data[3].to(model.device)
                rgb_image_features_proj = model.model(x1=rgb_imgs, get_image=True)
                ir_image_features_proj = model.model(x2=ir_imgs, get_image=True)
                for i, j, img_feat1, img_feat2 in zip(rgb_pids, ir_pids, rgb_image_features_proj, ir_image_features_proj):
                    visible_labels.append(i)
                    visible_image_features.append(img_feat1.cpu())
                    infrared_labels.append(j)
                    infrared_image_features.append(img_feat2.cpu())
            visible_labels_list = torch.stack(visible_labels, dim=0).cuda()
            infrared_labels_list = torch.stack(infrared_labels, dim=0).cuda()
            visible_image_features_list = torch.stack(visible_image_features, dim=0).cuda()
            infrared_image_features_list = torch.stack(infrared_image_features, dim=0).cuda()
            batch = config.stage1_batch_size
            num_image = infrared_labels_list.shape[0]
            i_ter = num_image // batch
        del visible_labels, visible_image_features, infrared_labels, infrared_image_features
        print('Visible Image Features Extracted, Start Training')

        model._init_optimizer_stage1()

        for current_epoch in range(start_train_epoch, config.stage1_train_epochs):
            model.model_lr_scheduler_stage1.step(current_epoch)
            _, result = train_stage1(model, num_image, i_ter, batch, visible_labels_list,
                                     visible_image_features_list, infrared_labels_list, infrared_image_features_list)
            logger('Time: {}; Epoch: {}; LR: {}; {}'.format(time_now(), current_epoch,
                                                            model.model_lr_scheduler_stage1._get_lr
                                                            (current_epoch)[0], result))

        print('The 1st Stage of Trained')

        # 第二阶段训练
        print('Start the 2st Stage Training')
        print('Extracting Image Features')

        image_features = []
        labels = []

        with torch.no_grad():
            for i, data in enumerate(loaders.get_train_normal_loader()):
                rgb_imgs, rgb_pids = data[0].to(model.device), data[2].to(model.device)
                ir_imgs, ir_pids = data[1].to(model.device), data[3].to(model.device)
                rgb_image_features_proj = model.model(x1=rgb_imgs, get_image=True)
                ir_image_features_proj = model.model(x2=ir_imgs, get_image=True)
                pids = torch.cat([rgb_pids, ir_pids], dim=0)
                image_features_proj = torch.cat([rgb_image_features_proj, ir_image_features_proj], dim=0)
                for i, img_feat in zip(pids, image_features_proj):
                    labels.append(i)
                    image_features.append(img_feat.cpu())
            labels_list = torch.stack(labels, dim=0).cuda()
            image_features_list = torch.stack(image_features, dim=0).cuda()
            batch = config.batch_size * 2
            num_image = labels_list.shape[0]
            i_ter = num_image // batch
        del labels, image_features
        print('Image Features Extracted, Start Training')

        model._init_optimizer_stage2()

        for current_epoch in range(start_train_epoch, config.stage1_train_epochs):
            model.model_lr_scheduler_stage2.step(current_epoch)
            _, result = train_stage2(model, num_image, i_ter, batch, labels_list,
                                     image_features_list, )
            logger('Time: {}; Epoch: {}; LR: {}; {}'.format(time_now(), current_epoch,
                                                            model.model_lr_scheduler_stage2._get_lr
                                                            (current_epoch)[0], result))

        print('The 2st Stage Trained')

        # 第三阶段训练
        print('Start the 3st Stage Training')
        print('Extracting Text Features')

        num_classes = model.model.module.num_classes
        batch = config.batch_size
        i_ter = num_classes // batch
        left = num_classes - batch * (num_classes // batch)
        if left != 0:
            i_ter = i_ter + 1
        text_features = []
        with torch.no_grad():
            for i in range(i_ter):
                if i + 1 != i_ter:
                    l_list = torch.arange(i * batch, (i + 1) * batch)
                else:
                    l_list = torch.arange(i * batch, num_classes)
                text_feature = model.model(label=l_list, get_fusion_text=True)
                text_features.append(text_feature.cpu())
            text_features = torch.cat(text_features, 0).cuda()
        print('Text Features Extracted, Start Training')

        model._init_optimizer_stage3()

        for current_epoch in range(start_train_epoch, config.total_train_epoch):
            model.model_lr_scheduler_stage3.step(current_epoch)

            _, result = train(model, loaders, text_features, config, current_epoch)
            logger('Time: {}; Epoch: {}; LR, {}; {}'.format(time_now(), current_epoch,
                                                            model.model_lr_scheduler_stage3.get_lr()[0], result))

            # 定期测试并保存最佳模型
            if current_epoch + 1 >= 1 and (current_epoch + 1) % config.eval_epoch == 0:
                cmc, mAP, mINP = test(model, loaders, config)
                is_best_rank = (cmc[0] >= best_rank1)
                best_rank1 = max(cmc[0], best_rank1)
                model.save_model(current_epoch, is_best_rank)
                logger('Time: {}; Test on Dataset: {}, \nmINP: {} \nmAP: {} \n Rank: {}'.format(time_now(),
                                                                                            config.dataset,
                                                                                            mINP, mAP, cmc))
    # 测试
    elif config.mode == 'test':
        # 恢复指定模型
        model.resume_model(config.resume_test_model)
        # 进行测试并记录测试结果
        cmc, mAP, mINP = test(model, loaders, config)
        logger('Time: {}; Test on Dataset: {}, \nmINP: {} \nmAP: {} \n Rank: {}'.format(time_now(),
                                                                                       config.dataset,
                                                                                       mINP, mAP, cmc))

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    # 命令行参数
    # 定义使用的计算设备，默认为 'cuda'，即使用 GPU 进行计算
    parser.add_argument('--cuda', type=str, default='cuda')
    # 定义运行模式，默认为 'train'，可选项为 'train' 或 'test'，用于指定是进行训练还是测试
    parser.add_argument('--mode', type=str, default='train', help='train, test')
    # 定义数据测试模式，all表示对所有可用数据进行测试，indoor可能表示仅室内数据
    parser.add_argument('--test_mode', default='all', type=str, help='all or indoor')
    # 图库模式 single表示仅使用单个模态地数据，multi表示使用多模态数据
    parser.add_argument('--gall_mode', default='single', type=str, help='single or multi')
    # regdb这个数据集的测试模式， v-t表示从可见光到热红外的测试模型，将可见光作为查询样本，将热红外作为图库样本进行识别匹配，通过这种方式评估模型的跨模态能力
    parser.add_argument('--regdb_test_mode', default='v-t', type=str, help='')
    parser.add_argument('--dataset', default='sysu', help='dataset name: regdb or sysu]')
    parser.add_argument('--sysu_data_path', type=str, default='/ssd/s01015/data/SYSU-MM01/')
    parser.add_argument('--regdb_data_path', type=str, default='/ssd/s01015/data/RegDB/')
    # 定义regdb数据集 试验编号，默认为1
    parser.add_argument('--trial', default=1, type=int, help='trial (only for RegDB dataset)')
    parser.add_argument('--batch-size', default=32, type=int, metavar='B', help='training batch size')
    parser.add_argument('--img_w', default=144, type=int, metavar='imgw', help='img width')
    parser.add_argument('--img_h', default=288, type=int, metavar='imgh', help='img height')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--pid_num', type=int, default=395)
    parser.add_argument('--learning_rate', type=float, default=0.0003)
    # 权重衰减系数，防止过拟合
    parser.add_argument('--weight_decay', type=float, default=0.0005)
    # 定义学习率衰减的里程碑，默认[40,70]，即在第40和第70个epoch时降低学习率
    parser.add_argument('--milestones', nargs='+', type=int, default=[40, 70],
                        help='milestones for the learning rate decay')

    parser.add_argument('--stage1_batch-size', default=32, type=int, metavar='B', help='training batch size')
    parser.add_argument('--stage1_learning_rate', type=float, default=0.0003)
    parser.add_argument('--stage2_learning_rate', type=float, default=0.0003)
    parser.add_argument('--stage1_weight_decay', type=float, default=1e-4)
    parser.add_argument('--stage1_lr_min', type=float, default=1e-6)
    # 第一阶段 warmup 初始学习率
    parser.add_argument('--stage1_warmup_lr_init', type=float, default=0.00001)
    parser.add_argument('--stage1_warmup_epochs', type=int, default=5)
    # 第一阶段训练的总轮数
    parser.add_argument('--stage1_train_epochs', type=int, default=60)

    parser.add_argument('--lambda1', type=float, default=0.15)
    parser.add_argument('--lambda2', type=float, default=0.05)
    parser.add_argument('--lambda3', type=float, default=0.1)

    # 损失函数编号
    parser.add_argument('--loss', default=1, type=int,
                        help='num of pos per identity in each modality')
    # 每个身份在每个模态中的正样本数量，m默认4
    parser.add_argument('--num_pos', default=4, type=int,
                        help='num of pos per identity in each modality')
    parser.add_argument('--num_workers', default=8, type=int,
                        help='num of pos per identity in each modality')
    parser.add_argument('--output_path', type=str, default='models/base/',
                        help='path to save related informations')
    parser.add_argument('--max_save_model_num', type=int, default=1, help='0 for max num is infinit')
    parser.add_argument('--resume_train_epoch', type=int, default=-1, help='-1 for no resuming')
    parser.add_argument('--auto_resume_training_from_lastest_step', type=ast.literal_eval, default=True)
    parser.add_argument('--total_train_epoch', type=int, default=120)
    parser.add_argument('--eval_epoch', type=int, default=1)
    parser.add_argument('--resume_test_model', type=int, default=119, help='-1 for no resuming')

    config = parser.parse_args()    # 解析命令行参数
    seed_torch(config.seed)         # 设置随机种子
    main(config)                    # 调用主函数并开始训练或测试
