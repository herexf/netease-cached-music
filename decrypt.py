#coding : utf-8
import os
import sys
import glob
import requests
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


DESDIR = '../Decrypted'
LRCDIR = os.path.join(DESDIR, 'lyric')
MSCDIR = os.path.join(DESDIR, 'music')

API = 'https://api.imjad.cn/cloudmusic/?'
# two args: id  type
# type=song, lyric, comments, detail, artist, album, search
# eg  API = 'https://api.imjad.cn/cloudmusic/?type=song&id=1234132'    download music

hasModu = False
try:
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import ID3, APIC
    from mutagen.mp3 import MP3
    from mutagen import MutagenError
    hasModu = True
except:
    pass

def safeprint(s):
    '''deal with invalid encoded filename'''
    try:
        print(s)
    except:
        print(repr(s)[1:-1])

class netease_music:
    def __init__(self, path=''):
        '''path is the directory that contains Music files(cached)'''
        if path == '':
            path = input('input the path of cached netease_music')
        self.path = path
        safeprint('[+] Current Path: ' + path)
        os.chdir(path)
        self.files = glob.glob('*.uc') + glob.glob('*.uc!')
        self.id_mp = {}
        self.title = {}
        self.artist = {}
        self.album = {}
        self.cover = {}
        for i in self.files:
            self.id_mp[self.getId(i)] = i
        if not os.path.exists(DESDIR):
            os.mkdir(DESDIR)
        if not os.path.exists(LRCDIR):
            os.mkdir(LRCDIR)
        if not os.path.exists(MSCDIR):
            os.mkdir(MSCDIR)
        # import re
        # self.nameXpath ='//div[@class="tit"]/em[@class="f-ff2"]/text()'
        # self.lrcSentencePt=re.compile(r'\[\d+:\d+\.\d+\](.*?)\\n')         # wrong  (r'\[\d+,\d+\](\(\d+,\d+\)(\w))+\n')

    def getId(self, name):
        return name[:name.find('-')]

    def getInfoFromWeb(self, musicId):
        dic = {}
        url = API+'type=detail&id=' + musicId
        info = requests.get(url).json()['songs'][0]
        dic['artist'] = [info['ar'][0]['name']]
        dic['title'] = [info['name']]
        dic['cover'] = [info['al']['picUrl']]
        dic['album'] = [info['al']['name']]
        return dic

    def getInfoFromFile(self, path):
        if not os.path.exists(path):
            safeprint('Can not find file ' + path)
            return {}
        elif hasModu:
            return dict(MP3(path, ID3=EasyID3))
        else:
            print('[Error] You can use pip3 to install mutagen or connet to the Internet')
            raise Exception('Failed to get info of ' + path)

    def getPath(self, dic,musicId):
        title = dic['title'][0]
        artist = dic['artist'][0]
        album = dic['album'][0]
        cover = dic['cover'][0]
        if artist in title:
            title = title.replace(artist, '').strip()
        name = (artist + ' - ' + title)
        for i in '>?*/\:"|<':
            name = name.replace(i,'-') # form valid file name
        self.id_mp[musicId] = name
        self.title[musicId] = title
        self.artist[musicId] = artist
        self.album[musicId] = album
        self.cover[musicId] = cover
        #print('''{{title: "{title}",artist: "{artist}",mp3: "http://ounix1xcw.bkt.clouddn.com/{name}.mp3",cover: "{cover}",}},'''\
               #.format(title = title,name = name,artist=artist,cover=dic['cover'][0]))
        return os.path.join(MSCDIR, name + '.mp3')
    
    def decrypt(self, cachePath):
        musicId = self.getId(cachePath)
        idpath = os.path.join(MSCDIR, musicId + '.mp3')
        try:  # from web
            dic = self.getInfoFromWeb(musicId)
            path = self.getPath(dic,musicId)
            if os.path.exists(path): return 
            with open(path,'wb') as f:
                f.write(bytes(self._decrypt(cachePath)))
        except Exception as e:  # from file
            print(e)
            print ("from file")
            if not os.path.exists(idpath):
                with open(idpath,'wb') as f:
                    f.write(bytes(self._decrypt(cachePath)))
            dic = self.getInfoFromFile(idpath)
            path = getPath(dic,musicId)
            if os.path.exists(path):
                os.remove(idpath)
                return 
            os.rename(idpath, path)
    
    def _decrypt(self,cachePath):
        with open(cachePath, 'rb') as f:
            btay = bytearray(f.read())
        for i, j in enumerate(btay):
            btay[i] = j ^ 0xa3
        return btay
    
    def getLyric(self, musicId):
        name = self.id_mp[musicId]
        url = API + 'type=lyric&id=' + musicId
        url2 = 'https://music.163.com/api/song/lyric?id='+ musicId +'&lv=1&kv=1&tv=-1'
        try:
            lrc = requests.get(url).json()['lrc']['lyric']
            if lrc=='':
                lrc = requests.get(url2).json()['lrc']['lyric']
            if lrc=='':
                raise Exception('')
            file = os.path.join(LRCDIR, name + '.lrc')
            if not os.path.exists(file):
                with open(file, 'w', encoding='utf8') as f:
                    f.write(str(lrc))
        except Exception as e:
            print(e,end='')
            safeprint(': Failed to get lyric of music '+name)
    
    def getMusic(self):
        for ct, cachePath in enumerate(self.files):
            self.decrypt(cachePath)
            musicId = self.getId(cachePath)
            mfilename = self.id_mp[musicId] + '.mp3'
            mfilepath = os.path.join(MSCDIR, mfilename)
            try:
                tags = EasyID3(mfilepath)
                tags['title'] = self.title[musicId]
                tags['album'] = self.album[musicId]
                tags['artist'] = self.artist[musicId]
                tags.save()
            except MutagenError: 
                print ('Loading EasyID3 tags failed.')
            
            try:
                # print ('picurl: ' + self.cover[musicId])
                albumcover = urlopen(self.cover[musicId])
                try:
                audio = ID3(mfilepath)
                audio['APIC'] = APIC(
                      encoding=3,
                      mime='image/jpeg',
                      type=3, desc=u'Cover',
                      data=albumcover.read()
                    )
                albumcover.close()
                audio.save()
                except ID3NoHeaderError:
                print ('Loading ID3 tags failed.')
            except HTTPError as e:
                print('Error code: ', e.code)
            except URLError as e:
                print ('Error code: ', e.reason)
            
            print('[{}]'.format(ct+1).ljust(5) + mfilename + 'NMID' + musicId)
            self.getLyric(musicId)



if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = sys.argv[1].strip()
    else:
        path = os.path.join(os.getcwd(), 'Music1')
    handler = netease_music(path)
    handler.getMusic()
