#!/usr/bin/env python
# -*- coding: utf8 -*-

from mido import MidiFile
from unidecode import unidecode
import numpy as np

#######
# Pianorolls dims are  :   TIME  *  PITCH

## TODO: 修改时间单位从ticks到指定的frames

class Read_midi(object):
    def __init__(self, song_path, quantization):
        ## Metadata
        self.__song_path = song_path
        self.__quantization = quantization

        ## Pianoroll
        self.__T_pr = None

        ## Private misc
        self.__num_ticks = None
        self.__T_file = None
        self.__beats_per_second = None
        

    @property
    def quantization(self):
        return self.__quantization

    @property
    def T_pr(self):
        return self.__T_pr

    @property
    def T_file(self):
        return self.__T_file

    def get_total_num_tick(self):
        # Midi length should be written in a meta message at the beginning of the file,
        # but in many cases, lazy motherfuckers didn't write it...

        # Read a midi file and return a dictionnary {track_name : pianoroll}
        mid = MidiFile(self.__song_path)

        # Parse track by track
        num_ticks = 0
        for i, track in enumerate(mid.tracks):
            tick_counter = 0
            for message in track:
                # Note on
                time = float(message.time)
                tick_counter += time
            num_ticks = max(num_ticks, tick_counter)
        #print("num_ticks", num_ticks)
        self.__num_ticks = num_ticks

    def get_pitch_range(self):
        mid = MidiFile(self.__song_path)
        min_pitch = 200
        max_pitch = 0
        for i, track in enumerate(mid.tracks):
            for message in track:
                if message.type in ['note_on', 'note_off']:
                    pitch = message.note
                    if pitch > max_pitch:
                        max_pitch = pitch
                    if pitch < min_pitch:
                        min_pitch = pitch
        return min_pitch, max_pitch

    def get_time_file(self):
        # Get the time dimension for a pianoroll given a certain quantization
        mid = MidiFile(self.__song_path)
        # Beat per minute
        tempo = None
        for msg in mid.tracks[0]:
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                break
        
        if tempo is not None:
            microseconds_per_beat = tempo
            self.__beats_per_second = 1e6 / microseconds_per_beat
            print(self.__beats_per_second)
            # Tick per beat
            ticks_per_beat = mid.ticks_per_beat
            # ticks_per_second = ticks_per_beat * beats_per_second
        else:
            raise ValueError("Tempo information was not found in the MIDI file.")
            
        # Total number of ticks
        self.get_total_num_tick()
        
        # 将以拍为单位转成以秒为单位
        self.__quantization = 1. / self.__beats_per_second
        
        # Dimensions of the pianoroll for each track
        self.__T_file = int((self.__num_ticks / ticks_per_beat) * self.__quantization)
        return self.__T_file
        
    def read_file(self):
        # Read the midi file and return a dictionnary {track_name : pianoroll}
        mid = MidiFile(self.__song_path)

        # Tick per beat
        ticks_per_beat = mid.ticks_per_beat

        # Get total time
        self.get_time_file()
        T_pr = self.__T_file
        # Pitch dimension
        N_pr = 88
        pianoroll = {}

        def add_note_to_pr(note_off, notes_on, pr):
            pitch_off, _, time_off = note_off
            # Note off : search for the note in the list of note on,
            # get the start and end time
            # write it in th pr
            match_list = [(ind, item) for (ind, item) in enumerate(notes_on) if item[0] == pitch_off]
            if len(match_list) == 0:
                print("Try to note off a note that has never been turned on")
                # Do nothing
                return

            # Add note to the pr
            pitch, velocity, time_on = match_list[0][1]
            pitch = pitch - 21
            pr[time_on:time_off, pitch] = velocity
            # Remove the note from notes_on
            ind_match = match_list[0][0]
            del notes_on[ind_match]
            return

        # Parse track by track
        counter_unnamed_track = 0
        for i, track in enumerate(mid.tracks):
            # Instanciate the pianoroll
            pr = np.zeros([T_pr, N_pr])
            time_counter = 0
            notes_on = []
            for message in track:
                # Time. Must be incremented, whether it is a note on/off or not
                time = float(message.time)
                time_counter += time / ticks_per_beat * self.__quantization
                # Time in pr (mapping)
                time_pr = int(round(time_counter))
                # Note on
                if message.type == 'note_on':
                    # Get pitch
                    pitch = message.note
                    if 0 <= pitch - 21 < 88:
                        # Get velocity
                        velocity = message.velocity
                        if velocity > 0:
                            notes_on.append((pitch, velocity, time_pr))
                        elif velocity == 0:
                            add_note_to_pr((pitch, velocity, time_pr), notes_on, pr)
                            
                # Note off
                elif message.type == 'note_off':
                    pitch = message.note
                    if 0 <= pitch - 21 < 88:
                        velocity = message.velocity
                        add_note_to_pr((pitch, velocity, time_pr), notes_on, pr)

            # We deal with discrete values ranged between 0 and 127
            #     -> convert to int
            pr = pr.astype(np.int16)
            if np.sum(np.sum(pr)) > 0:
                name = unidecode(track.name)
                name = f'Track_{i}'  # 修改了Track Name，使得每个轨道独立，按轨道顺序读取；轨道顺序依然是0 1 2 3
                name = name.rstrip('\x00')
                if name == u'':
                    name = 'unnamed' + str(counter_unnamed_track)
                    counter_unnamed_track += 1
                if name in pianoroll.keys():
                    # Take max of the to pianorolls
                    pianoroll[name] = np.maximum(pr, pianoroll[name])
                else:
                    pianoroll[name] = pr
        return pianoroll


if __name__ == '__main__':
    filepath = "/data/xyth/Dataset/stringquad_midi/aasesdeath/aasesdeath.MID"
    aaa = Read_midi(filepath, 4).read_file()
    #print(aaa)
    # print(aaa['Violin'].shape)
    print(Read_midi(filepath, 1).get_time_file())
    # 使用示例
    import matplotlib.pyplot as plt

    # 假设 aaa 是从 Read_midi 类的 read_file 方法返回的钢琴卷字典
    # pianoroll_violin = aaa['Violoncello']
    pianoroll_violin = aaa[list(aaa.keys())[3]]  # 这里按轨道顺序读取，0 1 2 3代表小1 2，中，大

    # 绘制钢琴卷
    plt.imshow(pianoroll_violin.T, aspect='auto', origin='lower', cmap='hot')
    plt.colorbar()  # 显示颜色条
    plt.xlabel('Time')
    plt.ylabel('Pitch')
    plt.title('Pianoroll for "Violin" Track')

    # 保存图像到文件，你可以指定文件格式和分辨率
    plt.savefig('cello_11_pianoroll.png', format='png', dpi=300)

    # 关闭图形，释放资源
    plt.close()
    
