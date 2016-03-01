import logging
import random

#: ===========================  Loger initialization ===============:#


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='prepare_dummy_ISUG.log')
log = logging.getLogger('prepare_dummy_ISUG')
log.setLevel(logging.INFO)


#: Create console handler and set level to warning :#
#: All the loggings that are higher than this level here,shall be written to stdout. :#
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)

#: create formatter that will be passed to console handler :#
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#: Add formatter to ch :#
ch.setFormatter(formatter)


#: =============================  end of logger ===========================:#


def message_pool(branch, revision):

    #: Message pool :#

    message1 = """Hello,\n\nThe commits for dummy ISUG are done @ """ + revision + """

            \nWill start the ISO from this revision\n
            \nRgds

          """

    message2 = """Hi,\n\nI have commited against """ + branch + """ the ISUG commits.\n 

             Will trigger the ISO from """ + revision + """
             \nRgds"""

    message3 = """Hi,\n\nCommited revision """ + revision + """\nISO will start soon\n

            \nRgds 
            """

    body_mail = [message1, message2, message3]

    #: Choose randomly an outgoing message each time :#
    out = random.choice(body_mail)
    return out
