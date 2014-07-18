#!/usr/bin/env python
#encoding: UTF-8

'''
网易云音乐 Player
'''
# Let's make some noise

import subprocess
import threading
import time
import os
import signal

from .ui import Ui


# carousel x in [left, right]
carousel = lambda left, right, x: left if (x>right) else (right if x<left else x)

class Player:


    def __init__(self):
        self.PLAY_MODE_NORMAL = 1
        self.PLAY_MODE_SHUFFLE = 2
        self.PLAY_MODE_REPEAT = 3
        self.ui = Ui()
        self.datatype = 'songs'
        self.popen_handler = None
        # flag stop, prevent thread start
        self.playing_flag = False
        self.pause_flag = False
        self.play_mode = self.PLAY_MODE_NORMAL
        self.songs = []
        self.idx = 0
        self.q_level = 0

    def popen_recall(self, onExit, popenArgs):
        """
        Runs the given args in a subprocess.Popen, and then calls the function
        onExit when the subprocess completes.
        onExit is a callable object, and popenArgs is a lists/tuple of args that
        would give to subprocess.Popen.
        """
        def runInThread(onExit, popenArgs):
            self.popen_handler = subprocess.Popen(['mpg123', popenArgs], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
       
            # auto decrease quality level , [hMusic, bMusic, mMusic, defaultMusic, lMusic]    
            if self.q_level != 4:
                count = 20
                for line in self.popen_handler.stderr:
                    if count == 0:
                        self.q_level += 2
                        self.next()
                        return
                    count -= 1

            self.popen_handler.wait()
            if self.playing_flag:
                self.idx = carousel(0, len(self.songs)-1, self.idx+1 )
                onExit()
            return


        thread = threading.Thread(target=runInThread, args=(onExit, popenArgs))
        thread.start()
        # returns immediately after the thread starts
        return thread

    def notify(self, item, executable='notify-send'):
        try:
            try:
                msg = 'display notification "' + item['artist'] + '   < ' + item['album_name'] + ' >' + '" with title "' + item['song_name'] +'"'
                subprocess.Popen(['osascript', '-e', msg])
            except:
                pass
        except:
            cover_path = os.path.expanduser('~') + \
                '/netease-musicbox/cover.jpg'
            song_info = "%s-%s \n %s"  \
                % (item['album_name'], item['song_name'], item['artist'])
            with open(os.devnull, 'w') as fnull:
                handler = subprocess.Popen(['curl', item['cover_url'], '-o', cover_path],
                        stdout=fnull, stderr=subprocess.STDOUT)
                handler.wait()
                handler = subprocess.Popen(['convert', cover_path, '-resize', '150x150', cover_path],
                        stdout=fnull, stderr=subprocess.STDOUT)
                handler.wait()
                handler = subprocess.Popen(['notify-send', '-i', cover_path, '-t', '3000', song_info], 
                        stdout=fnull, stderr=subprocess.STDOUT)

    def recall(self):
        self.playing_flag = True
        item = self.songs[ self.idx ]
        self.ui.build_playinfo(item['song_name'], item['artist'], item['album_name'], item['mp3'][self.q_level]['bitrate'])
        self.popen_recall(self.recall, item['mp3'][self.q_level]['mp3_url'])
        self.notify(item)

    def play(self, datatype, songs, idx):
        # if same playlists && idx --> same song :: pause/resume it
        self.datatype = datatype

        if len(songs) and (datatype == 'songs' or datatype == 'djchannels'):
            if idx == self.idx and songs == self.songs:
                if self.pause_flag:
                    self.resume()
                else:
                    self.pause()

            else:
                if datatype == 'songs' or datatype == 'djchannels':
                    self.songs = songs
                    self.idx = idx

                # if it's playing
                if self.playing_flag:
                    self.switch()

                # start new play
                else:
                    self.recall()
        # if current menu is not song, pause/resume
        else:
            if self.playing_flag:
                if self.pause_flag:
                    self.resume()
                else:
                    self.pause()
            else:
                pass

    # play another
    def switch(self):
        self.stop()
        # wait process be killed
        time.sleep(0.01)
        self.recall()

    def stop(self):
        if self.playing_flag and self.popen_handler:
            self.playing_flag = False
            self.popen_handler.kill()

    def pause(self):
        self.pause_flag = True
        os.kill(self.popen_handler.pid, signal.SIGSTOP)
        item = self.songs[ self.idx ]
        self.ui.build_playinfo(item['song_name'], item['artist'], item['album_name'], bitrate=item['mp3'][self.q_level]['bitrate'], pause=True)

    def resume(self):
        self.pause_flag = False
        os.kill(self.popen_handler.pid, signal.SIGCONT)
        item = self.songs[ self.idx ]
        self.ui.build_playinfo(item['song_name'], item['artist'], item['album_name'], bitrate=item['mp3'][self.q_level]['bitrate'])

    def next(self):
        self.stop()
        time.sleep(0.01)
        if self.play_mode == self.PLAY_MODE_NORMAL:
            self.idx = carousel(0, len(self.songs)-1, self.idx+1 )
        elif self.play_mode == PLAY_MODE_SHUFFLE:
            self.idx = random.sample(range(0, len(self.songs)), 1)[0]
        self.recall()

    def prev(self):
        self.stop()
        time.sleep(0.01)
        self.idx = carousel(0, len(self.songs)-1, self.idx-1 )
        self.recall()
