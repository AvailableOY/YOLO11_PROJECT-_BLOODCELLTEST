'''
    定义MobileViT模型网络结构
    考虑：是否使用预训练模型的权重，使用模型的类型 固定为small
'''

import os
import torch.nn as nn
from pathlib import Path

from transformers import MobileViTModel,MobileViTConfig


'''
    定义MobileVitBackbone网络
'''
class MobileViTBackbone(nn.Module):
    # 初始化
    def __init__(self,model_name="apple/mobilevit-small",pretrained=True):
        super(MobileViTBackbone, self).__init__()
        self.model_path = os.path.join(Path(__file__).resolve().parents[3],"mobilemodel")
        self.model_name = model_name
        # 加载模型  是否使用预训练权重
        if pretrained:
            # 使用预训练权重
            self.model = MobileViTModel.from_pretrained(
                pretrained_model_name_or_path = self.model_name,
                cache_dir=self.model_path
                )
        else:
            # 不使用预训练权重
            self.model = MobileViTModel(MobileViTConfig.from_pretrained(
                pretrained_model_name_or_path = self.model_name,
                cache_dir=self.model_path
            ))
        # 得到模型中的stem,encoder
        self.conv_stem = self.model.conv_stem
        self.encoder = self.model.encoder.layer
        # 关于输出通道数的配置  --因为mobilevit的输出通道和YOLO的输出通道数不一致，所以需要修改
        self.out_channels = [96,128,160]
        '''
            96-->256
            128->512
            160->1024
        '''
        # 通过1x1的卷积实现通道的转化  在卷积中加入BN  激活函数增加非线性的能力
        self.conv3 = nn.Sequential(
            nn.Conv2d(in_channels=self.out_channels[0],out_channels=256,kernel_size=1,stride=1,padding=0),
            nn.BatchNorm2d(256),
            nn.SiLU()
            )
        self.conv4 = nn.Sequential(
            nn.Conv2d(in_channels=self.out_channels[1],out_channels=512,kernel_size=1,stride=1,padding=0),
            nn.BatchNorm2d(512),
            nn.SiLU()
            )
        self.conv5 = nn.Sequential(
            nn.Conv2d(in_channels=self.out_channels[2],out_channels=1024,kernel_size=1,stride=1,padding=0),
            nn.BatchNorm2d(1024),
            nn.SiLU()
            )
    # 前向传播
    def forward(self,x):
        '''
            0-4层
            Modelvit分别对应2 3 4层
            来替换YOLO的p3p4p5层
        '''
        # 进入conv_stem层
        x = self.conv_stem(x)
        # encoder
        x = self.encoder[0](x)
        x = self.encoder[1](x)
        x = self.encoder[2](x)

        # 把这个赋值给p3
        p3 = x
        x = self.encoder[3](x)
        # 赋值给p4
        p4 = x
        x = self.encoder[4](x)
        # 赋值给p5
        p5 = x
        '''
            调整输出通道
        '''
        p3 = self.conv3(p3)
        p4 = self.conv4(p4)
        p5 = self.conv5(p5)
        # 返回的是一个列表
        return [p3,p4,p5]


