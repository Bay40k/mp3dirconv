import os, os.path

EXT = ".m4a" #extension to convert
DIR = "." #directory to convert
OUT_DIR = "./output" #output directory
SAMPL_RATE = "44100" #sample rate (kHz)
BIT_RATE = "200" #birate (kbps)

songs = [name for name in os.listdir(DIR) if EXT in name]

def convertAllInFolder():
    for song in songs:
        song_name = str(song[:-int(len(EXT))]) #remove extension

        #convert
        data = {"in_name": song_name, "extendo": EXT, "sample_rate": SAMPL_RATE, "bit_rate": BIT_RATE, "outdir": OUT_DIR, "out_name": song_name}
        os.system("ffmpeg -i \"{in_name}{extendo}\" -vn -ar {sample_rate} -ac 2 -b:a {bit_rate}k -n -f mp3 \"{outdir}/{out_name}.mp3\"".format(**data))

convertAllInFolder()
