'''
    根据索引取出p3 p4 p5
'''

import torch.nn as nn

class SelectIndex(nn.Module):
    def __init__(self,index):
        super(SelectIndex,self).__init__()
        self.index = index
    def forward(self,x):
        return x[self.index]