#!/usr/bin/python 

#: Utility that  can automate a trivial and usual procedure of preparing a build to accommodate as dummy ISUG target :#
#: script will take only two arguments .The source build revision and the branch we are performing the dummy ISUG :#
import traceback
import os
import re
import sys
from subprocess import Popen,STDOUT,PIPE
import urllib2
import smtplib
from email.mime.text import MIMEText
import ldap
from optparse import OptionParser
import fileinput
from collections import Counter
from itertools import *
import time
from loglib import log,ch,message_pool
from gitlib import *


#: ====================   Parser initialization   =================:#
parser = OptionParser()
parser.add_option("-b","--branch",\
dest="branch",\
action="store",\
help='The svn delivery that will be used for parsing')
    
parser.add_option("-q","--quiet",\
dest="verbose",\
action="store_true",\
help='When -q is present,only ERROR log level messages are prompted.')
    
parser.add_option("-r","--build_rev",\
dest="src_build_rev",\
type="int",\
action="store",\
help='Source build revision')

if len(sys.argv)==1:
    parser.print_help()
    sys.exit(1)
(options,args) = parser.parse_args()

options.src_build_rev = str(options.src_build_rev)

#: =======================    end of parser    ==================:#


#: ========================== constants here  ===================:#
cmd = Custom_Command()
git = Git()
retry = 1 #:variable that stores the num of retries in check_sanity :#
          #: and since it is used inside a function check_sanity    :#
          #: it needs to be declared as global at the top of this function :#
          #: so as to inform the intepreter that the variable we are referring to #:
          #: inside the function is actually the variable that is declared at the top of the module :#
          #: Do not do that and fail with UnboundLocalError as Python creates another variable inside the function :#
          #: with the same name as it is used in a operation ie retry += 1 (creates another new local var) 
ssh_winterfell  ='ssh django@10.85.40.177' #: user must have setup the keys between hyperion and winterfell :#
cat_regex       = re.compile(r'(\w+)(?=:(\d{5,6}))')
dir='isu_cgr'
if options.branch.startswith('cat'):
    dir='isu'
vevak_url = 'http://vevak.dev.cic.nsn-rdnet.net/'+dir+'/rev_db_cache_'+options.branch+'.txt'
homepath     = os.environ['HOME'] 
working_copy = '/scratch/'+os.environ['USER']+'/git_trunk' #:this can be customized according to the user's needs :#
ipc_file     = os.environ['TOOLS_ROOT']+'/troubleshoot/msgmon/conf/ipc_encoding_scheme.conf'
supported_file = os.environ['LIB_ROOT']+'/libisu_mc/manage_gen/supported_versions.conf'
buildbot_url ='http://fra.dev.cic.nsn-rdnet.net/'+options.branch+'/one_box_per_builder'
ipc_message_db = ['LIBSYNC_HA_UPDATE','PEM_CTRL_SC_PEER_DOWN_INDICATION','CDR_COLLECTOR_HA_CTRL_SWO_NOTIFY']
commitBanServer_url = 'http://10.85.40.174:8091/commitBanServer'
rpm_url = 'http://fra.dev.cic.nsn-rdnet.net/'+options.branch+'/rpms/'



#: ==========================  end of constants ====================:#


#: =========================== take care of console handler  ===============:#


# #: If -q option is present stdout will be supressed except for ERRORS & CRITICALS ,yet it will be written to the logger's log file (prepare_dummy_ISUG.log) :#
if options.verbose == True:
    
    ch.setLevel(logging.ERROR)
    log.addHandler(ch)
    
else:    
    #: Add console handler to logger :#
    log.addHandler(ch)




#:    *******************   main utilities start here   ****************** :#
def commit_ban(BanServerUrl):


    """ Function that checks if commit ban is ON/OFF"""

    try:
        resp = urllib2.urlopen(BanServerUrl).readlines()
    except urllib2.HTTPError as e:
        print 'Commit Ban Server is unavailable'
        print 'Will use magic_word_ISUG anyway to be sure'
        return True

    else:
        for line in resp:
            if 'ON' in line and options.branch in line:
                log.warning('COMMIT BAN is ON for %s' % options.branch)
                log.warning('Will use magic_word_ISUG in commit msg')
                print 'COMMIT BAN is ON for %s' % options.branch
                print 'Will use magic_word_ISUG in commit msg'
                return True
            else:
                pass

    return False

def check_sanity(commited=None):

    """ Function that checks the sanity status from buildbot 
        If sanity is red it calls itself recursively in order
        to wait until sanity is green.If it is red for 30 minutes
        it aborts.

        @rtype  tuple
        $rvalue flag that tells is sanity is green and the green revision

    """    



    global retry
    is_green = False

    
    print'Checking sanity status'



    #: the buildbot file shall be kept into a list in order to parse it later :#
    try:
        f = urllib2.urlopen(buildbot_url).readlines()
    except urllib2.HTTPError as e:
        print 'Unable to fetch buildbot url '
        print e
        sys.exit(3)
    

    #: it will be used to get the revision in the sanity box :#
    sanity_reg = re.compile(r'(?<=href=)"builders/SANITY/builds/\d+">(\d{6})</a><br />(\w+)<br')

    #: check the validity of the buildbot file that has now become a list ---check line 133:#
    
    
    if 'SANITY' in ' '.join(f):
        log.info('SANITY string is found in the buildbot file.Proceed with parsing')
    else:
        log.error('Failed to find SANITY in buildbot file.Check manually')
        sys.exit(3)


    if not commited:
    #: we are in the case where the script calls for the first time check_sanity in order to proceed with the commits :#
        for line in f:
        
            if 'SANITY' in line and 'failed' in line:

            #: enter an 3min loop periodically until sanity box is green.Break the loop then. :#

                while (retry < 10):

            #: give it some time until it tries again :#
            #: There are some cases about sanity that need to be handled accordingly :#
            #: 1)The sanity has left in red state and no-one is looking at this
            #: |
            #: |-----> the script will try for 30 minutes and abort.Before aborting it must restore 
            #:         the files that have been changed to their previous state 
            #: 2)The sanity is either red or green but it is expected by the responsible team to be fixed
            #:   in less than 1h
            
                    time_period = 180
                    log.info('Sleeping for 3 mins in order to wait for sanity to be green')
                    time.sleep(time_period)
                    log.info('Retrying sanity check:%s' % retry)    
                    retry += 1
                    return check_sanity()

                log.critical('Tried for 30minutes and sanity is still red.Aborting...num of retries:%s' % retry)
                sys.exit(8)

            elif 'SANITY' in line and 'successful' in line:
                green_rev = sanity_reg.search(line).group(1)
                is_green = True
                print'================================================='
                print 'Green revision currently on buildbot SANITY is ',green_rev
                print'================================================='
                print'Done\n'

                break

            else:
                pass

    #: we should get here when we call check_sanity with commited revision as parameter :#
    #: in order to verify if this revision ended with green sanity                      :#

    else:
    #: this is the case that we make sure our commits turned sanity into green :#
        for line in f:
            if 'SANITY/builds' in line:
                while sanity_reg.search(line).group(1) != commited:
                    print 'revision in buildot:',sanity_reg.search(line).group(1)
                    print 'revision that commited:',commited
                    sanity_reg.search(line).group(1) != commited
                    log.info('Currently building.Wait until our commited revision is in the sanity box and turns green')
                    time.sleep(120)
                    return check_sanity(commited)
                log.info('Commited revision %s is in sanity box' % commited)
                if 'successful' in line:
                    log.info('Commited revision %s turned green.SUCCESS!!!' % commited)
                    print'=========================================='
                    print'    We commited %s and is green ' % commited
                    print'=========================================='
                    green_rev = commited
                    is_green = True
                    break
                else:
                    log.error('We most probably broke sanity @ %s.Check manually' % commited)
                    error = 'Hi,\n\n Commited revision %s has resulted in red sanity.\n\nCould you please check?' % commited
                    sender = find_sender(username())
                    #send_mail(error,sender)
                    sys.exit(4)

    return (is_green,green_rev)




def ipc_message_gen(file_object):

    """
        Generator function that uses lazy evaluation for checking if
        a message from the message db that is defined in the top level
        of the module can be found in the ipc scheme

        On success/failure it yields to the caller (examine_ipc_scheme) the message.
        
        The handling is implemented in the caller level(just below)
   
    """

    
    for message in ipc_message_db:
        x=filter(lambda line:re.match('M='+message+' ',line),file_object.readlines())
        
        if x:
            yield (True,x[0].strip('\n'))
        else:
            file_object.seek(0)
            yield (False,message)
            continue


def examine_ipc_scheme(ipc_file):

    """
        Function that is used along with the above generator function 
        Scope is the same.
        On success from the generator it returns the message.
        On failure it returns a notification that the message is not found in the 
        scheme.
        If the number of failures is 3 it aborts.

        @rtype  file object
        @rvalue string


    """


    
    cnt = 0  
    try:
        with open(ipc_file) as f:
            for message_found in ipc_message_gen(f):
                if message_found[0] == True:
                    log.info('%s is found in ipc scheme.Try to modify this', ' '.join(message_found[1].split()))
                    break   
                else:
                    cnt += 1
                    log.warning('%s is not found in ipc scheme.Try next candidate',' '.join(message_found[1].split()))  

            if cnt == len(ipc_message_db):
                log.error('ipc message db is examined and no candidate found for editing')
                sys.exit(3)
            else:
                log.info('Will change now %s in ipc file' % message_found[1].split()[0])
                
                
    except IOError:
        #: if we get here then something is really messed up... :#
        log.error('ipc encoding scheme seems that does not exist')
        sys.exit(4)

    return message_found[1]



def edit_ipc_supported(message_to_modify,srclvn='',currentlvn='',supported=False):

    """
        Function that it is called twice in the code.
        a)For the initial commit in the ipc scheme
        b)For the revert of the ipc scheme and modification of supported_versions.
       
        $rtype function
       
    """


    if supported == False:

        edit_ipc(message_to_modify)

    else:

        edit_ipc(message_to_modify)
        edit_supported(srclvn,currentlvn)



def edit_supported(source_lvn,current_lvn):
    
    """
        Function that edits the supported_versions.conf.
        It opens the file and inserts a line of this form:

        Adaptation:  bfr_<src_lvn>  <===> bfr_<trg_lvn>

        It calculates the target lvn itself by examining what is the
        latest lvn in the vevak file,and adds 2.The latest lvn should
        normally be always the same as the src_lvn...

        @rtype  None

    """


    print 'Going to edit supported_versions.conf file\n'
    log.info('Going to edit supported_versions.conf file')
    print 'Calculating target LVN'
    log.info('Calculating target LVN')

    print '======================'
    if int(current_lvn) != int(source_lvn):
        log.critical('It seems that source lvn:%s differs from current lvn:%s in %s.Usually they need to be equal.' % (source_lvn,current_lvn,options.branch))    

    trg_lvn = str(int(current_lvn) + 2)
    print 'Target lvn will be :',trg_lvn
    log.info('Target lvn will be :%s' % trg_lvn)
    print'======================='

    S = open(supported_file,'r+')
    supported_list = S.readlines()
    for i,line in enumerate(supported_list):
        if re.search('End of file',line,re.I):
#            print 'Found End of file at line : ',i
            break
    

    if options.branch == 'trunk':
        bfr = '1'
    else:
        #: 1st way to retrieve BFR :#
        bfr_lvn = re.findall('\d+'+'_'+'\d+','\n'.join(supported_list))
        bfrs = [line.split('_')[0] for line in bfr_lvn]
        c = Counter(bfrs)
        bfr_1 = c.most_common()[0][0]
        #: 2nd backup way to retrieve BFR :#
        try:
            f = open('Makefile.inc')
        except IOError: 
            log.error('Unable to open Makefile.inc to retrieve the BFR')
            sys.exit(12)
        else:
            for line in f:
                if (re.search('BFR',line) and re.search('\d{6}',line)) and not re.search('9{4,}',line):
                    bfr_2 = re.search('(\d{6})',line).group(1)
        if int(bfr_1) == int(bfr_2):
            bfr = bfr_2
        else:
            print 'Collected BFRs that were retrieved with 2 methods are different'
            print '%s != %s' % (str(bfr_1),str(bfr_2))
            log.critical('Collected BFRs that were retrieved with 2 methods are different,but will proceed with %s' % str(bfr_2))
            log.critical('%s != %s', str(bfr_1),str(bfr_2))
            bfr = bfr_2
            #sys.exit(2)
    supported_list.insert(i,'Adaptation:  '+str(bfr)+'_'+source_lvn+' <===> '+str(bfr)+'_'+trg_lvn+'\n')    
    S.seek(0)
    S.write(''.join(supported_list)) 
    S.close()   
    git.diff()
    log.info('supported versions edited.This is the diff:  ================= \n\n\n %s ==============',git.stdOut)
    print 'Done\n'
    log.info('Done')


def edit_ipc(message_to_modify):

    """
        Function that edits the ipc encoding scheme.
        It is called twice via the edit_ipc_supported method as it is
        actually returned by this. 

    """

    for line in fileinput.input(ipc_file,inplace=True):
        if re.match(message_to_modify.split()[0]+' ',line):
            log.info('Match found in ipc scheme for %s.Change that' % message_to_modify.split()[0])
            new_flag = set_ISU_flag(line)
            print re.sub('ISU=\d','ISU='+new_flag,line).replace('\n','')
        else:
            print line.replace('\n','')
    
    git.diff()
    log.info('ipc scheme edited.This is the diff: =============== \n\n\n %s \n\n\n ============',git.stdOut)




def set_ISU_flag(line):

    """ 
        Function that sets the ISU flag of a message given to this.
        If original message has ISU=1 it sets it to ISU=0 and vice versa

    """


    
    old_value = re.search('ISU=(\d)',line).group(1)
    log.info('Old value for ISU flag of %s is %s' % (' '.join(line.split()),old_value))

    return str(1) if old_value == str(0) else str(0)



def commit_message(msg,commited_files=[]):
    
    """
        Function that adds the changes into the git changeset and commits locally
        
        @arg  string that is the description of the commited message (REF:    DESCR: )

    """

    magic_flag = ''

    if commit_ban(commitBanServer_url):
        magic_flag = 'magic_word_ISUG'


    
    msg = msg + magic_flag
    git.add(commited_files)
    git.commit(msg)
    
def find_ini_branch():


    """Function that finds in which branch we are 
       before to start the script operations
    """

    git.show_branches()
    for line in git.stdOut.splitlines():
        if '*' in line:
            return line.split()[1]


def check_branch_existence():


    """
        Function that will make a precheck to the user's environment.
        It looks for the branch in question,and if the user has already cloned it
        it passes.Error is logged on failure to find a cloned branch.

    """

#: Check if the branch(case insensitive) is cloned :#
    os.chdir(working_copy)
    #: utilize git object :#
    git.show_branches()
    available_branches = git.stdOut
    if re.search(options.branch,available_branches,re.I):   #: trunk is already cloned as master :#
        pass
    else:
        log.error('%s is not cloned.Exit',options.branch)
        sys.exit(3)


#: There are 2 categories of builds. :#
#: Lately,the trunk builds are named by real revisions rather than green tags. :#
#: And the other category comprises of the builds in the options.branches that are still named by green tag :#

def fetch_vevak_file(f):

    """ decorator/cosmetic """

    def wrap():
        print 'Retrieve source LVN'
        log.info('Retrieve source LVN')
        return f()
    return wrap


@fetch_vevak_file
def get_src_lvn():

    """ Function that retrieves the source lvn from vevak file 
        It also returns apart from the source lvn,the latest lvn in the
        vevak file.It is used for calculating the target lvn.

    """



    try:
        response = urllib2.urlopen(vevak_url).readlines()
    except urllib2.HTTPError:
        log.error('url %s from vevak not found' % vevak_url)
        sys.exit(5)
    else:
        if not options.branch.startswith('cat'):
            try:
                src_lvn = filter(lambda line:re.search('\\b'+options.src_build_rev+'\\b',line),response)[0].split('|')[7].strip()
                #src_lvn=re.search(r'(?<= )(\d{1,3})(?= )',filter(lambda line:re.search('\\b'+options.src_build_rev+'\\b',line),response)[0]).group(1)
                #latest_LVN = re.search(r'(?<= )(\d{1,3})(?= )',response[-1]).group(1)
                latest_LVN = response[-1].split('|')[7].strip()
            except IndexError:
                log.error('Requested wrong revision %s against %s',options.src_build_rev,options.branch)
                sys.exit(3)
        else:
            try:
                enter_winterfell()
                file_desc = open('/home/'+username()+'/'+options.src_build_rev+'.txt','r')
                green_tag = cat_regex.search(file_desc.readlines()[2]).group(2)
            except AttributeError:
                log.error('Requested wrong revision %s against %s',options.src_build_rev,options.branch)
                sys.exit(4)
            else:
                log.info('green tag is:%s ',green_tag)
                #: LVN in branches are most of the times 2-digit string :#
                src_lvn=filter(lambda line:re.search('\\b'+green_tag+'\\b',line),response)[0].split('|')[7].strip()
                #src_lvn=re.search(r'(?<= )(\d{1,2})(?= )',filter(lambda line:re.search('\\b'+green_tag+'\\b',line),response)[0]).group(1)
                #latest_LVN = re.search(r'(?<= )(\d{1,2})(?= )',response[-1]).group(1)
                latest_LVN=response[-1].split('|')[7].strip()
    print'================================'
    print 'You requested %s as source lvn' % src_lvn        
    log.info('You requested %s as source lvn' % src_lvn)
    print 'Latest LVN in %s is %s ' % (options.branch,latest_LVN)
    log.info('Latest LVN in %s is %s ' % (options.branch,latest_LVN))
    print'================================'
    print'Done\n'
    log.info('Done')
    return (src_lvn,latest_LVN)


           
def enter_winterfell():


    """
        Function that is used when we are doing ISUG in a branch and not in trunk.
        It fetches a revision file from winterfell machine and opens to examine the
        green tag that was built the ISO.
        If branches  use the real commited revisions in their ISOs in the future we can skip this call

    """

    log.info('SSH to winterfell for %s.txt' % options.src_build_rev)
    print 'SSH to winterfell for %s.txt' % options.src_build_rev
    django = pexpect.spawn(ssh_winterfell)
    django.expect_exact('$')
    c=pexpect.spawn('scp django@10.85.40.177:/home/django/lvnproject/Weblvn/my_media/svnhistory/'+options.src_build_rev+'.txt'' /home/'+username()+'/')
    c.expect(pexpect.EOF,timeout=None)
    c.terminate()
    django.terminate()
    if os.path.exists('/home/'+username()+'/'+options.src_build_rev+'.txt'):
        log.info('Fetched revision file %s.txt' % options.src_build_rev)
        print 'Fetched revision file %s.txt' % options.src_build_rev
        print 'Done\n'
    else:
        log.error('Did not succeed to fetch %s.txt from winterfell' % options.src_build_rev)
        
        sys.exit(14) 




def find_commited_revision():


    """
        Function that will be used to retrieve the revision in svn terms
        of the 2nd commit we made.
        This should be the revision from which the ISO will be built.

    """




    print'Find the commited revision'
    print'==========================='
    git.log(supported_file)
    if re.search(username(),git.stdOut):
        hashvalue = re.search(r'(?<=commit )(\w{10})',git.stdOut).group(1) 
        cmd.run('git svn find-rev '+hashvalue)
        com_revision = cmd.stdOut.strip('\n')
        print 'Commited revision is: ',com_revision
        log.info('Commited revision is %s: ' % com_revision)
        print '==========================='
        print'Done\n'
    else:
        log.error('Unable to find %s in %s.Check manually' % (username(),git.stdOut))
        sys.exit(3)
    return com_revision
 
def find_sender(user):


    """
        Utility to find the mail address of the sender

    """



    l = ldap.open("ed-p-gl.emea.nsn-net.net")
    l.protocol_version=ldap.VERSION3
    baseDN = "o=nsn"
    searchScope = ldap.SCOPE_SUBTREE
    retrieveAttributes=None
    searchFilter= "uid="+str(user.strip())
    x= l.search(baseDN,searchScope,searchFilter,retrieveAttributes)
    res = l.result(x,0)
    l.unbind_s()
    return res[1][0][1].get('mail')[0]


def send_mail(outgoing_message,Thesender):

   
    """
        Function that will send out a descriptive message
        to the build triggerers and not only,to notify about
        the revision we commited and if they should start an ISO
        or chech why sanity is red.


    """



    Topeople=['ioannis.kalyvas@nsn.com',
             'konstantinos.siatos@nsn.com',
             'georgios.georgiadis@nsn.com',
             'nikolaos.gkotsis@nsn.com',
             'cristina.montejo@nsn.com'
             ]

    if options.branch == 'cat_japan' or options.branch == 'ng30_13a':
        Topeople.append('mbb-paco-ng-team-abava-dg@internal.nsn.com')


    msg = MIMEText(outgoing_message)
    msg['Subject'] = 'New ISO for dummy ISUG' 
    msg['From'] = Thesender 
    msg['To'] = ','.join(Topeople)        
    s=smtplib.SMTP('localhost')
    s.sendmail(Thesender,[Thesender,','.join(Topeople)],msg.as_string())
    s.quit()
    log.info("Mail for iso trigger has been sent out!")

def restore_working_copy():

    """ If anything goes wrong during the running time
            this function will always be called to restore
            the modified files or actions in git

    """

    #: using hard reset it makes sure that 1)all the commited changes are undone
    #:and 2) that the changes are also discarded from the working copy
    print 'Hard resetting to HEAD~2 now'
    git.reset('hard',2)
    print'git svn rebase is recommended after that to restore latest HEAD'


def check_rpms(green_revision):

    """Checking the correct rpm production 
       after a successful sanity ensures us 
       that the iso that will follow will take
       the revision that resulted in green sanity

    """

    try:
        resp = urllib2.urlopen(rpm_url)
    except urllib2.HTTPError as e:
        print 'Cannot fetch rpms page from buildbot for parsing'
        print 'this should not prevent us from proceeding.Please check by yourself'
    else:
        rpms = re.findall('href=(.+?)tgz',' '.join(resp))   
    if green_revision in rpms[-1]:
        print 'Found the rpms for the sanity we just got green'
    else:
        print 'rpms are not the correct.the iso will most probably wont take the green revision %s ' % green_revision
             


if __name__ == '__main__':

    try:
        check_branch_existence()  
        original_branch = find_ini_branch()
        print 'Initially we are in:',original_branch
        log.info('Initially we are in:%s' % original_branch)
        
        git_stash_list(original_branch)
    

        git_rebase(options.branch)


        srcLVN,latestLVN = get_src_lvn()

        #: find a message from the db that will edit it's ISU flag:#
        message = examine_ipc_scheme(ipc_file)

        #: check if sanity is OK :#
        green_flag,green_rev = check_sanity()
    
        # : change the flag of the message in ipc scheme and show the diff :#
        print'First commit will happen now locally'
        print'======================================='
        print'Message to be committed in the ipc encoding scheme is:\n%s' % ' '.join(message.split()) 
        print'======================================='
        print'Done\n'
        edit_ipc_supported(message,supported=False) 
        log.info('FIRST COMMIT WILL HAPPEN NOW.Green revision currently on trunk is %s and message to modify:%s: ' % (green_rev,' '.join(message.split())))
        #: first local commit to git :#
        commit_message('REF:dummy commit to ipc scheme for dummy ISUG'+'\n'+'DESCR:\n',[ipc_file])
 
        #: change the flag back to its original state in IPC scheme and commit supported versions:# 
        #: Previous call of edit_ipc_supported uses the default parameters for source and latest LVN:#
        #: they are empty strings.For this call though,we need to set explicitly their values       :#
        print'Second commit will happen now locally'
        print'=========================================='
        print'Message to be committed in the ipc encoding scheme is:\n%s' % ' '.join(message.split()) 
        print'Will also commmit supported versions file'
        print'=========================================='
        print'Done\n'
        edit_ipc_supported(message,srcLVN,latestLVN,supported=True)
        log.info('SECOND COMMIT WILL HAPPEN NOW.Revert of ipc scheme and commit supported versions')
        #: second local commit to git :#
        commit_message('REF:revert of ipc scheme and commit supported versions'+'\n'+'DESCR:\n',[ipc_file,supported_file])

        raw_input('Press Enter to commit in SVN\n')
        #: send the 2 commits to svn as one :#
        git_dcommit()
    
        
        #: Find the commited revision from which ISO will be triggered :#
        rev = find_commited_revision()
        print'Wait 30 secs before sanity slave is awake '
        time.sleep(30) #: wait before sanity slave is awake :#

        #: Check if the commited revision turns sanity system into green :#
        print'Check now for %s to turn green and notify the ISO builders ' % rev
        check_sanity(rev)
        print'Done\n'

        check_rpms(rev)

        #raw_input('ABORT BEFORE SENDING MAIL')
        #: notify the team via email :#
        sender = find_sender(username())

        out = message_pool(options.branch,rev)

        #: Notify them and rest in peace :#
        answer = raw_input('Do you want to send an email(Y) or not(N)?')
        send_mail(out,sender) if answer in ['Y','y'] else None
 

    except BaseException:
        print '\nException Occurence!\nCheck the log file for further info\n\n'
        log.info('Exception Occurence happened.Traceback follows:\n\n\n'+traceback.format_exc())
        print 'Performing system restore'
        print '=========================='
        restore_working_copy()
        print '=========================='
        print 'Done\n'

    finally:
        
        print'Get the files back from stash if any'
        print'======================================'
        pat = re.compile('WIP on (\w+):')
        while True:
            git.stash('list')
            stashes = git.stdOut.splitlines()
            git.show_branches()
            all_branches = git.stdOut
            #: do git stash pop only if you are in the correct branch! :# 
            #: make use of mapping dict as master resolves into trunk... :#

            if stashes and options.branch in [pat.search(line).group(1) for line in stashes] and options.branch == [cur.split()[1] for cur in all_branches.splitlines() if '*' in cur][0] : 
                
                for line in stashes:
                    branch=pat.search(line).group(1)
                    if branch and branch == options.branch:
                        log.warning('Found stash %s for %s' % (line,options.branch))
                        stash_rev = re.match('stash@{(\d+)}',line).group(1)
                        git.stash('pop stash@{'+stash_rev+'}')
                        log.warning('Pop up this stash %s back to %s' % (line,options.branch))
                        break
                    else:
                        pass
            else:
                print 'No available stashes.Exit'
                break    
        #log.info('Get the files back from stash if any\n %s' % git.stdOut)
        print '========================================'
        print 'Done\n'
        sys.exit(2)
        
