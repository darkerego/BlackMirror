import time
from utils.colorprint import NewColorPrint
cp = NewColorPrint()

def start():
    time.sleep(0.25)
    cp.pulse('Loading...                                                                        ')
    time.sleep(0.3)
    cp.alert('- 1%')
    time.sleep(0.125)
    cp.alert('-- 2.5%')
    time.sleep(0.15)
    cp.alert('---- 5% ')
    time.sleep(0.2)
    cp.alert('-------- 10%')
    time.sleep(0.2)
    cp.alert('---------------- 12.5%')
    time.sleep(0.2)
    cp.alert('---------------------------- 25%')
    time.sleep(0.2)
    cp.alert('---------------------------------------- 50%')
    time.sleep(0.2)
    cp.alert('-------------------------------------------------------------- 75%')
    time.sleep(0.2)
    cp.alert('-------------------------------------------------------------------------- 99%')
    time.sleep(0.25)
    cp.alert('--------------------------------------------------------------------------- 100%')
    cp.pulse('root@rekt:~$                                                                    ')
    print('\n\n\n')


    cp.white_black("""                                                                                           """)
    cp.white_black("""  ██████╗ ██╗      █████╗  ██████╗██╗  ██╗███╗   ███╗██╗██████╗ ██████╗  ██████╗ ██████╗   """)
    cp.blue_black("""  ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝████╗ ████║██║██╔══██╗██╔══██╗██╔═══██╗██╔══██╗  """)
    cp.white_black("""  ██████╔╝██║     ███████║██║     █████╔╝ ██╔████╔██║██║██████╔╝██████╔╝██║   ██║██████╔╝  """)
    cp.alert("""  ██╔══██╗██║     ██╔══██║██║     ██╔═██╗ ██║╚██╔╝██║██║██╔══██╗██╔══██╗██║   ██║██╔══██╗  """)
    cp.white_black("""  ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗██║ ╚═╝ ██║██║██║  ██║██║  ██║╚██████╔╝██║  ██║  """)
    cp.white_black("""  ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝  """)
    cp.dark("""                   FTX Trade Mirroring Platform ~ Darkerego, 2020-2022 ~ version 0.1.1       """)
    time.sleep(0.75)
    print('\n\n\n')


def post():
    t = 0.00000000000001
    for i in range(1, 3):
        t += 0.01
        cp.random_pulse('Built by geniuses, for degenerates!')
        time.sleep(t)
