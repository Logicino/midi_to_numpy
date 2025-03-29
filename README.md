主函数文件：read_midi.py
代码的96，97行，经过修改，时间轴坐标从拍（beat）为单位转化为了秒（second）为单位
* 调用函数方式：
aaa = Read_midi(filepath, 4).read_file()
这样出来的aaa是一个list，每个list的元素是一个轨道的 【一个numpy数组】【形状是 (time, 88)，所以plot的时候是.T】
* 按顺序调用list的元素方法：
pianoroll_violin = aaa[list(aaa.keys())[0]]  # 这里按轨道顺序读取，0 1 2 3代表小1 2，中，大
